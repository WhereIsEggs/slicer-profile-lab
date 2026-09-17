# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Safe, optional use of OrcaSlicer's own profile validation engine."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from profilelab.external_runtime import external_dll_search, external_environment


def engine_home() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return local_app_data / "SlicerProfileLab" / "engine" / "orca-nightly"


def validator_path() -> Path:
    override = os.environ.get("PROFILELAB_ORCA_VALIDATOR")
    if override:
        return Path(override)
    return engine_home() / "OrcaSlicer_profile_validator.exe"


def validation_engine_resources() -> Path:
    """Use the resources shipped with the installed engine, never the editor cache."""
    return validator_path().parent / "resources"


@dataclass(frozen=True)
class EngineValidationResult:
    status: str
    message: str
    details: str = ""


def is_complete_profile_tree(folder: Path) -> bool:
    """A tree has vendor catalog files beside matching vendor directories."""
    if not folder.is_dir():
        return False
    return any(
        item.is_file() and item.suffix == ".json" and (folder / item.stem).is_dir()
        for item in folder.iterdir()
    )


def friendly_engine_details(output: str) -> str:
    """Keep useful Orca errors while dropping normal progress chatter."""
    lines = [line.strip() for line in output.splitlines() if "error" in line.casefold()]
    return "\n".join(lines[:30]) or output.strip()[:6000]


def is_runtime_profile_tree(folder: Path) -> bool:
    """Nightly runtimes may ship compiled vendor caches rather than source JSON."""
    return is_complete_profile_tree(folder) or (
        folder.is_dir() and any(p.is_file() and p.stat().st_size > 0 for p in folder.glob("*.opc"))
    )


def run_orca_engine(profile_folder: Path, timeout_seconds: int = 900) -> EngineValidationResult:
    """Validate a copied complete tree so Orca cannot alter the user's files."""
    executable = validator_path()
    if not is_complete_profile_tree(profile_folder):
        return EngineValidationResult(
            "not_applicable",
            "The Orca engine check needs a complete system profile library. Built-in checks still ran.",
        )

    with TemporaryDirectory(prefix="profilelab-orca-check-") as temporary:
        copied_resources = Path(temporary) / "resources"
        copied_tree = copied_resources / "profiles"
        shutil.copytree(profile_folder, copied_tree)
        source_info = profile_folder.parent / "info"
        if source_info.is_dir():
            shutil.copytree(source_info, copied_resources / "info")
        return _run_copied_tree(executable, copied_tree, timeout_seconds)


def run_orca_engine_for_user_profiles(resources: Path, user_profiles: Path,
                                      timeout_seconds: int = 900) -> EngineValidationResult:
    """Overlay a user folder onto trusted system profiles in a disposable workspace."""
    executable = validator_path()
    system_profiles = resources / "profiles"
    if not is_runtime_profile_tree(system_profiles) or not user_profiles.is_dir():
        return EngineValidationResult("not_applicable", "A matching system library is not ready for this user-profile check.")
    if not is_complete_profile_tree(system_profiles):
        return EngineValidationResult(
            "not_applicable",
            "Orca's validator needs matching source profiles. This runtime contains compiled profiles only; full validation has not run.",
            "The portable runtime's .opc files cannot replace the source JSON library in validator mode. Do not substitute an unrelated library version.",
        )
    with TemporaryDirectory(prefix="profilelab-orca-user-check-") as temporary:
        copied_resources = Path(temporary) / "resources"
        copied_tree = copied_resources / "profiles"
        shutil.copytree(system_profiles, copied_tree)
        # Orca may have downloaded newer or additional vendor bundles locally.
        local_system = user_profiles.parent.parent / "system"
        if local_system.is_dir():
            shutil.copytree(local_system, copied_tree, dirs_exist_ok=True)
        source_info = resources / "info"
        if source_info.is_dir():
            shutil.copytree(source_info, copied_resources / "info")
        shutil.copytree(user_profiles, copied_tree / "user" / "default", dirs_exist_ok=True)
        result = _run_copied_tree(executable, copied_tree, timeout_seconds, slice_profiles=False)
        if result.status == "passed":
            return EngineValidationResult("passed", "Profile loading and inheritance checks passed. Print quality and slicing were not tested.")
        if result.details:
            user_errors, library_errors = [], []
            for line in result.details.splitlines():
                clean = line.replace(str(copied_tree), "Validation library").replace("\\", "/")
                (user_errors if "/user/default/" in clean else library_errors).append(clean)
            sections = []
            if user_errors:
                sections.append("Your profiles — review these findings:\n" + "\n".join(user_errors))
            if library_errors:
                sections.append("System library or engine findings — these may affect the check:\n" + "\n".join(library_errors))
            sections.append("A missing parent means it was unavailable in this validation library; confirm its source before editing your profile.")
            return EngineValidationResult(result.status, "Profile check needs attention.", "\n\n".join(sections))
        return result


@external_dll_search()
def _run_copied_tree(executable: Path, copied_tree: Path, timeout_seconds: int, slice_profiles: bool = True) -> EngineValidationResult:
    command = [str(executable), "--path", str(copied_tree), "--log_level", "2",
               "--check_filament_subtypes", "--slice"]
    if not slice_profiles:
        command = command[:5]
    environment = external_environment(executable)
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_seconds, check=False,
            cwd=executable.parent, env=environment,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except subprocess.TimeoutExpired:
        return EngineValidationResult("failed", "The Orca engine check took too long and was stopped safely.")
    except FileNotFoundError as error:
        fallback, fallback_detail = _run_with_qt_process(command, executable, timeout_seconds)
        if fallback is not None:
            return fallback
        console_fallback, console_detail = _run_with_console_python(command, executable, timeout_seconds)
        if console_fallback is not None:
            return console_fallback
        return EngineValidationResult(
            "failed",
            "The Orca engine could not start.",
            "Windows could not start the installed Orca engine: " + str(error)
            + "\nFallback diagnostic: " + fallback_detail + "; " + console_detail,
        )
    except OSError as error:
        return EngineValidationResult("failed", f"The Orca engine could not start: {error}")

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if completed.returncode == 0:
        return EngineValidationResult("passed", "Orca's own engine check passed.")
    return EngineValidationResult(
        "failed", "Orca's own engine check found a problem.", friendly_engine_details(output),
    )


def _run_with_qt_process(command: list[str], executable: Path,
                         timeout_seconds: int) -> tuple[EngineValidationResult | None, str]:
    """Use Qt's Windows process API as a desktop-only fallback."""
    try:
        from PySide6.QtCore import QProcess, QProcessEnvironment
        process = QProcess()
        environment = QProcessEnvironment()
        for key, value in external_environment(executable).items():
            environment.insert(key, value)
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(executable.parent))
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process.start()
        if not process.waitForStarted(30_000):
            return None, "Qt process: " + process.errorString()
        if not process.waitForFinished(timeout_seconds * 1000):
            process.kill()
            return EngineValidationResult(
                "failed", "The Orca engine check took too long and was stopped safely."
            ), ""
        output = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        output += "\n" + bytes(process.readAllStandardError()).decode("utf-8", "replace")
        if process.exitCode() == 0:
            return EngineValidationResult("passed", "Orca's own engine check passed."), ""
        return EngineValidationResult(
            "failed", "Orca's own engine check found a problem.", friendly_engine_details(output),
        ), ""
    except Exception as error:
        return None, f"Qt process: {type(error).__name__}: {error}"


def _run_with_console_python(command: list[str], executable: Path,
                             timeout_seconds: int) -> tuple[EngineValidationResult | None, str]:
    """Retry from python.exe when a Windows GUI host cannot create the Orca process."""
    if getattr(sys, 'frozen', False):
        return None, 'Console-Python fallback is unavailable in the packaged app; check the engine installation.'
    console_python = Path(sys.executable).with_name("python.exe")
    if not console_python.is_file():
        return None, f"console Python was not found beside {sys.executable}"
    helper = (
        "import json, os, subprocess, sys; "
        "command = json.loads(sys.argv[1]); "
        "environment = os.environ.copy(); "
        "environment['PATH'] = sys.argv[2] + os.pathsep + environment.get('PATH', ''); "
        "result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', "
        "errors='replace', cwd=sys.argv[2], env=environment, check=False); "
        "print(json.dumps({'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}))"
    )
    try:
        completed = subprocess.run(
            [str(console_python), "-c", helper, json.dumps(command), str(executable.parent)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds + 30, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return None, f"{type(error).__name__}: {error}; console Python: {console_python}"
    output = "\n".join(part for part in (payload.get("stdout", ""), payload.get("stderr", "")) if part)
    if payload.get("returncode") == 0:
        return EngineValidationResult("passed", "Orca's own engine check passed."), ""
    return EngineValidationResult(
        "failed", "Orca's own engine check found a problem.", friendly_engine_details(output),
    ), ""
