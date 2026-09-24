# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Export-friendly ordinary user presets for stock OrcaSlicer 2.4.2."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4


class ProfileConflicts(ValueError):
    def __init__(self, files):
        self.files = files
        super().__init__('These installed profiles differ: ' + ', '.join(p.stem for p in files))

from profilelab.profile_install import _read_bundle, _safe_name, IDENTITIES
from profilelab.orca_status import require_orca_closed


def exportable_profiles(package):
    metadata, profiles = _read_bundle(package)
    if metadata.get("profilelab_demo"):
        raise ValueError("Fictional demo packages cannot be installed.")
    index = {(p["type"], p["name"]): p for p in profiles}
    result = []
    for leaf in profiles:
        if leaf.get("instantiation") == "false":
            continue
        chain, current = [], leaf
        while True:
            chain.append(current)
            if not current.get("inherits"):
                break
            current = index[(current["type"], current["inherits"])]
        resolved = {}
        for ancestor in reversed(chain):
            resolved.update(deepcopy(ancestor))
        # Freeze explicitly saved values, not external or hidden parent identities.
        for key in ("setting_id", "settings_id", "alias", "renamed_from", *IDENTITIES.values()):
            resolved.pop(key, None)
        resolved.update(name=leaf["name"], type=leaf["type"], inherits="", instantiation="true")
        resolved["from"] = "User"
        resolved[IDENTITIES[leaf["type"]]] = [leaf["name"]] if leaf["type"] == "filament" else leaf["name"]
        _safe_name(leaf["name"])
        result.append(resolved)
    if not result:
        raise ValueError("The package contains no selectable profiles.")
    if len({(p["type"], p["name"].casefold()) for p in result}) != len(result):
        raise ValueError("Package names conflict on Windows.")
    return result


def install_user_profiles(package: Path, user_folder: Path, *, approved_updates=None):
    profiles = exportable_profiles(package)
    root = Path(user_folder).absolute()
    if root.resolve() != root:
        raise ValueError("Linked user folders are not supported.")
    payloads = {}
    conflicts = {}
    for profile in profiles:
        folder = root / profile["type"]
        if folder.resolve() != folder:
            raise ValueError("Linked profile folders are not supported.")
        # Include nested base files in collision checks, without reading contents.
        target = folder / (profile["name"] + ".json")
        matches = [p for p in folder.rglob('*.json') if p.stem.casefold() == profile['name'].casefold()] if folder.exists() else []
        if matches:
            if len(matches) != 1 or matches[0] != target or target.resolve() != target:
                raise ValueError(f"'{profile['name']}' already exists in a different location or casing. Rename this profile before installing.")
            original = target.read_bytes()
            try:
                identical = json.loads(original) == profile
            except (ValueError, UnicodeError):
                identical = False
            if identical:
                continue
            conflicts[target] = original
        payloads[target] = json.dumps(profile, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
    if conflicts and (approved_updates is None or any(approved_updates.get(p) != content for p, content in conflicts.items())):
        raise ProfileConflicts(conflicts)
    require_orca_closed()
    created = []
    try:
        root.mkdir(parents=True, exist_ok=True)
        if conflicts:
            backup_root = root / 'profilelab-backups'
            if backup_root.resolve() != backup_root:
                raise ValueError('Linked backup folders are not supported.')
            backup = backup_root / uuid4().hex
            for target, original in conflicts.items():
                dest = backup / target.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(original)
        with TemporaryDirectory(prefix="profilelab-user-stage-", dir=root) as temporary:
            # Publish complete files, never partially written profiles. Hard-link
            # creation refuses an existing target; staging is on the same volume.
            for number, target in enumerate(sorted(payloads, key=lambda p: p.parent.name == "machine")):
                staged = Path(temporary) / str(number)
                staged.write_bytes(payloads[target])
                require_orca_closed()
                target.parent.mkdir(parents=True, exist_ok=True)
                if target in conflicts:
                    if target.read_bytes() != conflicts[target]:
                        raise ValueError('An installed profile changed during installation. Try again.')
                    os.replace(staged, target)
                else:
                    os.link(staged, target)
                created.append(target)
            require_orca_closed()
    except Exception:
        for target in reversed(created):
            # Never remove a file another process has subsequently changed.
            if target.exists() and target.read_bytes() == payloads[target]:
                if target in conflicts:
                    target.write_bytes(conflicts[target])
                else:
                    target.unlink()
        raise
    return created
