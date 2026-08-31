import json
from pathlib import Path


class InvalidProfileError(Exception):
    """Raised when a profile file contains invalid JSON."""

    def __init__(self, profile_path: Path):
        self.profile_path = profile_path
        super().__init__(f"Invalid JSON in {profile_path}")


def load_profile(profile_path) -> dict[str, object]:
    """load one JSON profile file and return its contents."""
    try:
        with profile_path.open("r", encoding="utf-8") as profile_file:
            return json.load(profile_file)
    except json.JSONDecodeError as error:
        raise InvalidProfileError(profile_path) from error
