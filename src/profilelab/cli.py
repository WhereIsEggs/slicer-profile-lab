import argparse
from pathlib import Path

from profilelab.loader import load_profile

def main():
    parser = argparse.ArgumentParser(
        description="Inspect and OrcaSlicer profile JSON file."
    )
    parser.add_argument(
        "profile_path",
        type=Path,
        help="Path to the profile JSON file to inspect.",
    )
    args = parser.parse_args()
    
    profile = load_profile(args.profile_path)
    
    print(f"Profile: {profile.get('name', '(unnamed)')}")
    print(f"Inherits: {profile.get('inherits', '(no parent)')}")
    
    
if __name__ == "__main__":
    main()