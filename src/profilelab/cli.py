import argparse
from pathlib import Path
from profilelab.validation import validate_folder


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

    report = validate_folder(args.profile_folder)

    if report.is_valid:
        print("No validation problems found.")
        return 0
        
    for issue in report.issues:
        print(f"ERROR: {issue.message}")
        
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
