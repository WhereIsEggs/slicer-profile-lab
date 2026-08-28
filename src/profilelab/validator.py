from pathlib import Path
from profilelab.loader import load_profile


def find_missing_parents(profile_folder: Path) -> list[dict[str,str]]:
    """Return profiles that inherir from a parent not found in the folder."""
    profiles = []
    
    for profile_path in profile_folder.rglob("*.json"):
        profiles.append(load_profile(profile_path))
        
    known_profile_names = {
        profile["name"]
        for profile in profiles
        if isinstance(profile.get("name"), str)
    }
    
    missing_parents = []
    
    for profile in profiles:
        profile_name = profile.get("name")
        parent_name = profile.get("inherits")
        
        if (isinstance(profile_name, str)
            and isinstance(parent_name, str)
            and parent_name not in known_profile_names
        ):
            missing_parents.append(
                {
                    "profile": profile_name,
                    "missing_parent": parent_name,
                }
            )
            
    return missing_parents