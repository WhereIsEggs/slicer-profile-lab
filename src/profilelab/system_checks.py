"""Publishing checks used by OrcaSlicer for complete system profile trees."""

import json
from pathlib import Path
import uuid


_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_SETTING_ID_NAMESPACE = uuid.UUID("c1f4d9e2-7a3b-5c8d-9e0f-1a2b3c4d5e6f")
_PROFILE_TYPES = ("filament", "machine", "process")
_CONFLICTING_KEYS = ("extruder_clearance_radius", "extruder_clearance_max_radius")


def expected_setting_id(vendor: str, profile_type: str, name: str) -> str:
    """Match OrcaSlicer's current deterministic 16-character setting ID."""
    value = int.from_bytes(
        uuid.uuid5(_SETTING_ID_NAMESPACE, f"{vendor}/{profile_type}/{name}").bytes,
        "big",
    )
    digits = []
    for _ in range(16):
        digits.append(_ALPHABET[value % 62])
        value //= 62
    return "".join(reversed(digits))


def find_setting_id_issues(profile_root: Path) -> list[dict]:
    """Check current upstream setting_id rules for a complete system tree only."""
    issues = []
    owners: dict[str, list[Path]] = {}
    for vendor_folder in sorted(path for path in profile_root.iterdir() if path.is_dir()):
        vendor = vendor_folder.name
        for profile_type in _PROFILE_TYPES:
            type_folder = vendor_folder / profile_type
            if not type_folder.is_dir():
                continue
            for path in sorted(type_folder.rglob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(data, dict):
                    continue
                if "settings_id" in data:
                    issues.append({"path": path, "message": 'uses "settings_id"; use "setting_id" instead'})
                setting_id = data.get("setting_id")
                instantiated = data.get("instantiation") == "true"
                if not instantiated:
                    if setting_id:
                        issues.append({"path": path, "message": "a base profile must not have a setting_id"})
                    continue
                if not setting_id:
                    issues.append({"path": path, "message": "an instantiated profile is missing a setting_id"})
                    continue
                if not isinstance(setting_id, str):
                    issues.append({"path": path, "message": "setting_id must be text"})
                    continue
                owners.setdefault(setting_id, []).append(path)
                if vendor != "BBL":
                    expected = expected_setting_id(vendor, profile_type, data.get("name", ""))
                    if setting_id != expected:
                        issues.append({"path": path, "message": f'setting_id is stale; expected "{expected}"'})
    for setting_id, paths in owners.items():
        if len(paths) > 1:
            joined = ", ".join(str(path) for path in paths)
            issues.append({"path": paths[0], "message": f'setting_id "{setting_id}" is shared by: {joined}'})
    return issues


def find_profile_reference_issues(profile_root: Path) -> list[dict]:
    """Checks mirrored from Orca's extra profile checker where safe for a tree."""
    records = []
    for vendor_folder in sorted(path for path in profile_root.iterdir() if path.is_dir()):
        for profile_type in _PROFILE_TYPES:
            for path in sorted((vendor_folder / profile_type).rglob("*.json")) if (vendor_folder / profile_type).is_dir() else []:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(data, dict) and isinstance(data.get("name"), str):
                    records.append((vendor_folder.name, profile_type, path, data))
    names = {(vendor, profile_type): set() for vendor, profile_type, _, _ in records}
    for vendor, profile_type, _, data in records:
        names.setdefault((vendor, profile_type), set()).add(data["name"])
    all_filaments = {data["name"] for _, kind, _, data in records if kind == "filament"}
    issues = []
    for vendor, kind, path, data in records:
        def exists(target_kind, name):
            if name in names.get((vendor, target_kind), set()):
                return True
            return target_kind == "filament" and name in names.get(("OrcaFilamentLibrary", "filament"), set())

        parent = data.get("inherits")
        if isinstance(parent, str) and parent and not exists(kind, parent):
            # Generic parent validation has already named this problem; avoid duplication.
            pass
        for key, target_kind in (("compatible_printers", "machine"), ("compatible_prints", "process")):
            values = data.get(key)
            if values is not None and not isinstance(values, list):
                issues.append({"path": path, "message": f'"{key}" must be an array'})
            elif isinstance(values, list):
                for name in values:
                    if not isinstance(name, str) or not exists(target_kind, name):
                        issues.append({"path": path, "message": f'references unknown {key} entry "{name}"'})
        if kind == "filament" and vendor != "OrcaFilamentLibrary" and data.get("instantiation") == "true":
            if not data.get("compatible_printers"):
                issues.append({"path": path, "message": "an instantiated filament needs compatible_printers"})
        if kind == "machine":
            defaults = data.get("default_materials", data.get("default_filament_profile"))
            if isinstance(defaults, str):
                defaults = [part.strip() for part in defaults.split(";") if part.strip()]
            if isinstance(defaults, list):
                for name in defaults:
                    if name not in all_filaments:
                        issues.append({"path": path, "message": f'references missing default filament "{name}"'})
        if "filament_type" in data and not isinstance(data["filament_type"], list):
            issues.append({"path": path, "message": '"filament_type" must be an array'})
        present = [key for key in _CONFLICTING_KEYS if key in data]
        if len(present) > 1:
            issues.append({"path": path, "message": f"conflicting settings: {', '.join(present)}"})
    return issues
