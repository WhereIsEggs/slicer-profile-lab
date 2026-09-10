import json
from pathlib import Path


class InvalidProfileError(Exception):
    """Raised when a profile contains invalid JSON or an invalid structure."""
    
    def __init__(self, profile_path: Path, reason: str = "invalid JSON"):
        self.profile_path = profile_path
        self.reason = reason
        super().__init__(f"{profile_path}: {reason}")
        
def load_profile(profile_path: Path) -> dict[str, object]:
    """Load a JSON profile and check that it is an object."""
    try:
        with profile_path.open("r", encoding="utf-8") as profile_file:
            profile = json.load(profile_file)
    except json.JSONDecodeError as error:
        raise InvalidProfileError(profile_path) from error
                
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
