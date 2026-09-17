# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Dependency-complete Profile Lab packages; not yet Orca import bundles."""

from copy import deepcopy
import json
from pathlib import Path
import zipfile

KINDS = {"machine", "filament", "process"}
REFERENCES = {
    "compatible_printers": "machine",
    "compatible_prints": "process",
    "default_print_profile": "process",
    "default_filament_profile": "filament",
}
DEPENDENCIES = {key: REFERENCES[key] for key in ("default_print_profile", "default_filament_profile")}


def collect_profiles(profiles: list[dict], selected: list[tuple[str, str]]) -> list[dict]:
    """Resolve named dependencies conservatively; never guess ambiguous identities."""
    index = {}
    for profile in profiles:
        kind, name = profile.get("type"), profile.get("name")
        if kind not in KINDS or not isinstance(name, str) or not name.strip():
            raise ValueError("Every profile needs a supported type and name.")
        index.setdefault((kind, name), []).append(profile)
    included, active, checked_parents = {}, set(), set()

    def lookup(key):
        matches = index.get(key, [])
        if len(matches) != 1:
            reason = "missing" if not matches else "ambiguous"
            raise ValueError(f"{key[0]} profile '{key[1]}' is {reason}.")
        return matches[0]

    def check_parent(key):
        if key in active:
            raise ValueError(f"Inheritance cycle at '{key[1]}'.")
        if key in checked_parents:
            return
        profile = lookup(key)
        active.add(key)
        parent = profile.get("inherits", "")
        if not isinstance(parent, str):
            raise ValueError(f"Invalid parent for '{key[1]}'.")
        if parent:
            check_parent((key[0], parent))
        active.remove(key)
        checked_parents.add(key)

    def visit(key):
        if key in included:
            return
        profile = lookup(key)
        check_parent(key)
        # Conditions are expressions, not filenames. Orca evaluates them; an
        # explicit compatibility list takes precedence over its condition.
        for field in ("compatible_printers_condition", "compatible_prints_condition"):
            if field in profile and not isinstance(profile[field], str):
                raise ValueError(f"Invalid {field} in '{key[1]}'.")
        included[key] = deepcopy(profile)
        if profile.get("inherits"):
            visit((key[0], profile["inherits"]))
        for field, kind in REFERENCES.items():
            values = profile.get(field, [])
            if field.startswith("compatible_") and not isinstance(values, list):
                raise ValueError(f"Invalid {field} in '{key[1]}': expected a list.")
            if isinstance(values, str):
                values = [values] if values else []
            if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
                raise ValueError(f"Invalid {field} in '{key[1]}'.")
            if field in DEPENDENCIES:
                for name in values:
                    visit((kind, name))

    if not selected:
        raise ValueError("Select at least one profile to share.")
    for key in selected:
        visit(tuple(key))
    return [included[key] for key in sorted(included)]


def verify_package(path: Path) -> list[dict]:
    """Reopen and verify using only package contents, with no local library lookup."""
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "profilelab-sharing-v1":
            raise ValueError("Unsupported sharing package.")
        profiles = [json.loads(archive.read(name)) for name in manifest["files"]]
    collected = collect_profiles(profiles, manifest["selected"])
    if len(collected) != len(profiles):
        raise ValueError("Package contains unreferenced profiles.")
    return collected


def prepare_package(profiles: list[dict], selected: list[tuple[str, str]], destination: Path) -> list[dict]:
    """Write a new package without overwriting files or changing source profiles."""
    collected = collect_profiles(profiles, selected)
    files = [f"profiles/{number:04d}.json" for number in range(len(collected))]
    manifest = {"format": "profilelab-sharing-v1", "selected": selected, "files": files,
                "orca_import_verified": False}
    # Encode before opening the destination so invalid settings create no file.
    payloads = [json.dumps(profile, ensure_ascii=False, allow_nan=False, indent=2) for profile in collected]
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, payload in zip(files, payloads):
            archive.writestr(name, payload)
    return verify_package(destination)
