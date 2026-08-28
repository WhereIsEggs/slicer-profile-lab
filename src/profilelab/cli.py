import argparse
from pathlib import Path

from profilelab.validator import find_missing_parents


def main():
    parser = argparse.ArgumentParser(
        description="Validate an OrcaSlicer profile folder."
    )
    parser.add_argument(
        "profile_folder",
        type=Path,
        help="Folder containing profile JSON files.",
    )
    args = parser.parse_args()
    
    errors = find_missing_parents(args.profile_folder)
    
    if not errors:
        print("No missing parent profiles found.")
        return
    
    for error in errors:
        print(
            f"ERROR: {error['profile']} is missing parent "
            f"{error['missing_parent']}"
        )
        
        
        if __name__ == "__main__":
            main()