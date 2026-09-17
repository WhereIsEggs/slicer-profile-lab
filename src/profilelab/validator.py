# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
from pathlib import Path
from profilelab.loader import load_profile


def profile_paths(profile_folder: Path):
    """JSON presets, excluding root vendor catalog files in a full Orca tree."""
    return sorted(
        path for path in profile_folder.rglob("*.json")
        if not (path.parent == profile_folder and (profile_folder / path.stem).is_dir())
    )


def find_missing_parents(profile_folder: Path) -> list[dict[str, str]]:
    """Return profiles that inherit from a named parent not found in the folder."""
    profiles = []

    for profile_path in profile_paths(profile_folder):
        profiles.append((profile_path, load_profile(profile_path)))

    known_profile_names = {
        profile["name"]
        for _, profile in profiles
        if isinstance(profile.get("name"), str)
    }

    missing_parents = []

    for profile_path, profile in profiles:
        profile_name = profile.get("name")
        parent_name = profile.get("inherits")

        if (
            isinstance(profile_name, str)
            and isinstance(parent_name, str)
            and parent_name != ""
            and parent_name not in known_profile_names
        ):
            missing_parents.append(
                {
                    "profile": profile_name,
                    "missing_parent": parent_name,
                    "path": str(profile_path),
                }
            )

    return missing_parents


def find_duplicate_profile_names(profile_folder: Path) -> list[dict[str, object]]:
    """Return profile names that appear in more than one JSON file."""
    profile_paths_by_name: dict[str, list[str]] = {}

    for profile_path in profile_paths(profile_folder):
        profile = load_profile(profile_path)
        profile_name = profile.get("name")

        if isinstance(profile_name, str):
            if profile_name not in profile_paths_by_name:
                profile_paths_by_name[profile_name] = []

            profile_paths_by_name[profile_name].append(str(profile_path))

    duplicates = []

    for profile_name, paths in profile_paths_by_name.items():
        if len(paths) > 1:
            duplicates.append(
                {
                    "profile": profile_name,
                    "paths": paths,
                }
            )

    return duplicates


def find_inheritance_cycles(profile_folder: Path) -> list[list[str]]:
    """Return self-inheritance cycles, reporting each cycle once."""
    parents = {}
    
    for profile_path in profile_paths(profile_folder):
        profile = load_profile(profile_path)
        parent_name = profile.get("inherits")
        
        if isinstance(parent_name, str):
            parents[profile["name"]] = parent_name
            
    cycles = []
    checked = set()
    
    for start_name in sorted(parents):
        chain = []
        positions = {}
        current = start_name
        
        while current in parents and current not in checked:
            if current in positions:
                cycle_start = positions[current]
                cycle = chain[cycle_start:] + [current]
                cycles.append(cycle)
                break
            
            positions[current] = len(chain)
            chain.append(current)
            current = parents[current]
            
        checked.update(chain)
        
    return cycles
