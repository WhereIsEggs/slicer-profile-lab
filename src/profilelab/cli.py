import argparse
from pathlib import Path

from profilelab.validator import find_missing_parents

from profilelab.loader import InvalidProfileError


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

    try:
        errors = find_missing_parents(args.profile_folder)
    except InvalidProfileError as error:
        print(f"ERROR: {error.profile_path}: invalid JSON")
        return 1

    if not errors:
        print("No missing parent profiles found.")
        return 0

    for error in errors:
        print(
            f"ERROR: {error['path']}: {error['profile']} is missing parent "
            f"{error['missing_parent']}"
        )
        return 1


if __name__ == "__main__":
    main()
