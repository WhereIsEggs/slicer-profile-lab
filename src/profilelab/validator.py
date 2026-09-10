from pathlib import Path
from profilelab.loader import load_profile


def find_missing_parents(profile_folder: Path) -> list[dict[str, str]]:
    """Return profiles that inherir from a parent not found in the folder."""
    profiles = []

    for profile_path in profile_folder.rglob("*.json"):
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

    for profile_path in sorted(profile_folder.rglob("*.json")):
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
