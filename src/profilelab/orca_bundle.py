# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Experimental Orca bundle writer based on Orca's ZIP import contract.

Archive verification is not a substitute for testing the Orca GUI importer.
"""

import json
from pathlib import Path
import re
from uuid import uuid4
import zipfile

from profilelab.sharing import collect_profiles
from profilelab.bundle_contract import scope_profiles
from profilelab.orca_rules import RULES_REVISION

FIELDS = {"machine": ("printer", "printer_config", "printer_settings_id"),
          "filament": ("filament", "filament_config", "filament_settings_id"),
          "process": ("process", "process_config", "print_settings_id")}


def export_orca_bundle(profiles: list[dict], selected: list[tuple[str, str]], destination: Path, *, demo=False):
    """Export explicit profiles and dependencies, with parents before children."""
    if destination.suffix != ".orca_bundle":
        raise ValueError("Use the .orca_bundle extension.")
    collected = collect_profiles(profiles, selected)
    index = {(p["type"], p["name"]): p for p in collected}
    ordered, visited = [], set()

    def append(key):
        if key in visited:
            return
        profile = index[key]
        if profile.get("inherits"):
            append((key[0], profile["inherits"]))
        visited.add(key)
        ordered.append(profile)

    for key in sorted(index):
        append(key)
    bundle_id = "profilelab_" + uuid4().hex
    title = selected[0][1]
    manifest = {"version": ordered[0].get("version", ""), "id": bundle_id,
                "name": title, "bundle_id": title,
                "profilelab_rules_revision": RULES_REVISION,
                "profilelab_demo": bool(demo),
                "bundle_type": "printer config bundle", "printer_preset_name": title,
                "printer_config": [], "filament_config": [], "process_config": []}
    entries = []
    for number, profile in enumerate(scope_profiles(ordered, bundle_id)):
        folder, field, identity = FIELDS[profile["type"]]
        if any(other in profile for _, _, other in FIELDS.values() if other != identity):
            raise ValueError(f"'{profile['name']}' has identity keys belonging to another profile type.")
        version = profile.get("version", "")
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", version):
            raise ValueError(f"'{profile['name']}' needs an explicit numeric Orca version.")
        value = profile.get(identity)
        if profile["type"] == "filament":
            valid = isinstance(value, list) and len(value) == 1 and value[0] == profile["name"]
        else:
            valid = value == profile["name"]
        if not valid:
            raise ValueError(f"'{profile['name']}' needs its matching {identity}.")
        # Basenames are unique because Orca extracts all entries into one folder.
        name = f"{folder}/profile_{number:04d}.json"
        manifest[field].append(name)
        entries.append((name, json.dumps(profile, indent=2, ensure_ascii=False, allow_nan=False)))
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bundle_structure.json", json.dumps(manifest, indent=2))
        for name, payload in entries:
            archive.writestr(name, payload)
    return manifest
