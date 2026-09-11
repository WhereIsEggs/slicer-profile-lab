import argparse
from pathlib import Path
from profilelab.validator import (
    find_duplicate_profile_names,
    find_missing_parents,
)
from profilelab.loader import InvalidProfileError
from profilelab.validator import (
    find_duplicate_profile_names,
    find_inheritance_cycles,
    find_missing_parents,
)


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

    if not args.profile_folder.is_dir():
        print(f"ERROR: {args.profile_folder}: folder does not exist")
        return 1
        
    if not any(args.profile_folder.rglob("*.json")):
        print(f"ERROR: {args.profile_folder}: no JSON profile files found")
        return 1

    try:
        errors = find_missing_parents(args.profile_folder)
        duplicates = find_duplicate_profile_names(args.profile_folder)
        cycles = find_inheritance_cycles(args.profile_folder)
        
    except InvalidProfileError as error:
        print(f"ERROR: {error.profile_path}: {error.reason}")
        return 1
        
    if not errors and not duplicates and not cycles:
        print("No validation problems found.")
        return 0
        
    for error in errors:
        print(
            f"ERROR: {error['path']}: {error['profile']} is missing parent "
            f"{error['missing_parent']}"
        )
        
    for duplicate in duplicates:
        paths = ", ".join(duplicate["paths"])
        print(
            f"ERROR: duplicate profile name "
            f"'{duplicate['profile']}' appears in: {paths}"
        )
        
    for cycle in cycles:
        chain = " -> ".join(cycle)
        print(f"ERROR: inheritance cycle: {chain}")
        
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
