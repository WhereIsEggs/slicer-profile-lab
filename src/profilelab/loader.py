import json
from pathlib import Path

def load_profile(profile_path) -> dict[str, object]:
    """load one JSON profile file and return its contents."""
    with profile_path.open("r", encoding="utf-8") as profile_file:
        return json.load(profile_file)