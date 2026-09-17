# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import json
from pathlib import Path


class InvalidProfileError(Exception):
    """Raised when a profile contains invalid JSON or an invalid structure."""
    
    def __init__(self, profile_path: Path, reason: str = "invalid JSON"):
        self.profile_path = profile_path
        self.reason = reason
        super().__init__(f"{profile_path}: {reason}")


class DuplicateJsonKeyError(ValueError):
    pass


def _no_duplicate_keys(pairs):
    profile = {}
    for key, value in pairs:
        if key in profile:
            raise DuplicateJsonKeyError(f"duplicate JSON key '{key}'")
        profile[key] = value
    return profile
        
def load_profile(profile_path: Path) -> dict[str, object]:
    """Load a JSON profile and check that it is an object."""
    try:
        with profile_path.open("r", encoding="utf-8") as profile_file:
                profile = json.load(profile_file, object_pairs_hook=_no_duplicate_keys)
    except json.JSONDecodeError as error:
        raise InvalidProfileError(profile_path) from error
    except DuplicateJsonKeyError as error:
        raise InvalidProfileError(profile_path, str(error)) from error
                
    if not isinstance(profile, dict):
        raise InvalidProfileError(
            profile_path,
            "profile must be a JSON object",
        )
        
    profile_name = profile.get("name")
    
    if not isinstance(profile_name, str) or not profile_name.strip():
        raise InvalidProfileError(
            profile_path,
            "profile must have a nonempty string name",
        )
                
    return profile
