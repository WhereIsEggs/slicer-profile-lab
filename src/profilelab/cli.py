# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import argparse
from pathlib import Path
from profilelab.validation import validate_folder
from profilelab.legal import LEGAL_SUMMARY


def main():
    parser = argparse.ArgumentParser(
        description="Validate an OrcaSlicer profile folder.",
        epilog=LEGAL_SUMMARY + ' See LICENSE.txt and NOTICE.md in the distribution.'
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
