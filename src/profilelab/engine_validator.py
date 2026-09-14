"""Safe, optional use of OrcaSlicer's own profile validation engine."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


def engine_home() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return local_app_data / "SlicerProfileLab" / "engine" / "orca-nightly"


def validator_path() -> Path:
    override = os.environ.get("PROFILELAB_ORCA_VALIDATOR")
    if override:
        return Path(override)
    return engine_home() / "OrcaSlicer_profile_validator.exe"


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


def run_orca_engine(profile_folder: Path, timeout_seconds: int = 900) -> EngineValidationResult:
    """Validate a copied complete tree so Orca cannot alter the user's files."""
    executable = validator_path()
    if not executable.is_file():
        return EngineValidationResult(
            "unavailable",
            "The Orca engine check is not installed. Built-in checks still ran.",
        )
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
        command = [str(executable), "--path", str(copied_tree), "--log_level", "2",
                   "--check_filament_subtypes", "--slice"]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired:
            return EngineValidationResult(
                "failed", "The Orca engine check took too long and was stopped safely.",
            )
        except OSError as error:
            return EngineValidationResult(
                "failed", f"The Orca engine could not start: {error}",
            )

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if completed.returncode == 0:
        return EngineValidationResult("passed", "Orca's own engine check passed.")
    return EngineValidationResult(
        "failed", "Orca's own engine check found a problem.", friendly_engine_details(output),
    )
