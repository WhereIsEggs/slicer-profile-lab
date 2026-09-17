# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Install a complete, isolated local bundle; never overwrite user presets."""

import json
import re
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import zipfile

from profilelab.bundle_contract import bundle_prefix, scope_profiles, strict_json
from profilelab.orca_status import require_orca_closed
from profilelab.orca_rules import RULES_REVISION
from profilelab.sharing import collect_profiles

FOLDERS = {"machine": "machine", "process": "process", "filament": "filament"}
IDENTITIES = {"machine": "printer_settings_id", "process": "print_settings_id", "filament": "filament_settings_id"}
MANIFEST_FIELDS = {"printer_config": "machine", "process_config": "process", "filament_config": "filament"}


def _read_bundle(package):
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(e.file_size for e in entries) > 64 * 1024 * 1024:
            raise ValueError("Package exceeds the supported size.")
        names = [e.filename for e in entries]
        if len({n.casefold() for n in names}) != len(names):
            raise ValueError("Package contains duplicate filenames.")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
                raise ValueError("Unsafe package filename.")
        metadata = strict_json(archive.read("bundle_structure.json"))
        if not isinstance(metadata, dict) or metadata.get("bundle_type") != "printer config bundle":
            raise ValueError("Choose a prepared printer profile bundle.")
        if metadata.get("profilelab_rules_revision") != RULES_REVISION:
            raise ValueError("Re-prepare this package with the current Profile Lab before installing it.")
        bundle_prefix(metadata.get("id"))
        if not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
            raise ValueError("The bundle needs a display name.")
        profiles, referenced = [], ["bundle_structure.json"]
        for field, expected_kind in MANIFEST_FIELDS.items():
            paths = metadata.get(field)
            if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
                raise ValueError("Invalid bundle file list.")
            referenced.extend(paths)
            for name in paths:
                profile = strict_json(archive.read(name))
                if not isinstance(profile, dict) or profile.get("type") != expected_kind:
                    raise ValueError("Profile type does not match its bundle section.")
                _safe_name(profile.get("name"))
                if any(identity in profile for kind, identity in IDENTITIES.items() if kind != expected_kind):
                    raise ValueError("Profile contains conflicting type identity keys.")
                if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", str(profile.get("version", ""))):
                    raise ValueError("Profile is missing a numeric Orca version.")
                expected = [profile.get("name")] if expected_kind == "filament" else profile.get("name")
                if profile.get(IDENTITIES[expected_kind]) != expected:
                    raise ValueError("Profile identity does not match its name.")
                profiles.append(profile)
        if len(referenced) != len(set(referenced)) or set(referenced) != set(names):
            raise ValueError("Package file list is duplicated or incomplete.")
    profiles = scope_profiles(profiles, metadata["id"], unqualify=True)
    return metadata, collect_profiles(profiles, [(p["type"], p["name"]) for p in profiles])


def read_install_bundle(package: Path) -> list[dict]:
    return _read_bundle(package)[1]


def _safe_name(name):
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if (not isinstance(name, str) or not name.strip() or
            any(c in '<>:"/\\|?*' or ord(c) < 32 for c in name) or
            name.endswith((".", " ")) or len(name) > 180 or name.split(".")[0].upper() in reserved):
        raise ValueError(f"Rename '{name}' before installation: Orca requires a Windows-safe profile filename.")


def install_bundle(package: Path, user_folder: Path) -> list[Path]:
    metadata, profiles = _read_bundle(package)
    if metadata.get("profilelab_demo"):
        raise ValueError("This is a fictional demo package. Profile Lab will not install it into OrcaSlicer. Create a draft from the real library for actual use.")
    for profile in profiles:
        _safe_name(profile["name"])
    identities = {(p["type"], p["name"].casefold()) for p in profiles}
    if len(identities) != len(profiles):
        raise ValueError("Package contains conflicting profile names.")
    root = user_folder.resolve()
    local = root / "_local"
    destination = local / metadata["id"]
    if local.resolve() != local or destination.resolve() != destination:
        raise ValueError("Linked bundle folders are not supported.")
    scoped = scope_profiles(profiles, metadata["id"])
    payloads = {}
    # Orca reads each `base` subdirectory before the files in its parent.
    # Filesystem/filename order alone does not load ancestors reliably.
    index = {(p["type"], p["name"]): p for p in profiles}
    levels = {key: 0 for key in index}
    for key in index:
        current, level = key, 0
        while index[current].get("inherits"):
            current = (current[0], index[current]["inherits"])
            level += 1
            levels[current] = max(levels[current], level)
    for profile in scoped:
        profile["from"] = "Bundle"
        folder = Path(profile["type"]).joinpath(*(["base"] * levels[(profile["type"], profile["name"])]))
        payloads[folder / f"{profile['name']}.json"] = profile
    saved_metadata = {key: metadata.get(key, "") for key in ("id", "name", "version")}
    saved_metadata.update(description="Prepared by Slicer Profile Lab", author="", imported_time=0, updated_time=0)
    for kind, field in (("machine", "printer_presets"), ("process", "print_presets"), ("filament", "filament_presets")):
        saved_metadata[field] = [p["name"] for p in profiles if p["type"] == kind]
    payloads[Path("bundle_metadata.json")] = saved_metadata
    if destination.exists():
        existing = {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()}
        if existing == set(payloads) and all(strict_json((destination / p).read_bytes()) == data for p, data in payloads.items()):
            return []
        raise ValueError("This bundle already exists and differs. Nothing was installed.")
    require_orca_closed()
    local.mkdir(parents=True, exist_ok=True)
    # Stage outside local: Orca must never discover a half-written local bundle.
    with TemporaryDirectory(prefix="profilelab-stage-", dir=root) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        for path, data in payloads.items():
            require_orca_closed()
            target = staging / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as output:
                json.dump(data, output, ensure_ascii=False, allow_nan=False, indent=2)
        require_orca_closed()
        if destination.exists():
            raise ValueError("This bundle already exists. Nothing was installed.")
        staging.rename(destination)
    return [destination / p for p in payloads if p.name != "bundle_metadata.json"]
