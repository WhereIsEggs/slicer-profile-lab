import unittest
from pathlib import Path

from profilelab.validator import find_missing_parents

from unittest.mock import patch

from profilelab.cli import main

FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "missing_parent"
VALID_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "valid_parent"
ROOT_PROFILE_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "root_profile"
INVALID_JSON_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "invalid_json"


class MissingParentTests(unittest.TestCase):
    def test_reports_a_missing_parent(self):
        errors = find_missing_parents(FIXTURE_FOLDER)

        self.assertEqual(
            errors,
            [
                {
                    "profile": "0.24mm Draft @GB4 0.4 nozzle",
                    "missing_parent": "0.24mm Standard @GB4 0.4 nozzle",
                    "path": str(FIXTURE_FOLDER / "draft_process.json"),
                }
            ],
        )

    def test_accepts_a_profile_without_a_parent(self):
        errors = find_missing_parents(ROOT_PROFILE_FIXTURE_FOLDER)

        self.assertEqual(errors, [])

    def test_accepts_an_existing_parent(self):
        errors = find_missing_parents(VALID_FIXTURE_FOLDER)

        self.assertEqual(errors, [])

    def test_cli_returns_one_for_a_missing_parent(self):
        with (
            patch("sys.argv", ["profilelab", str(FIXTURE_FOLDER)]),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        mock_print.assert_called_once_with(
            "ERROR: "
            f"{FIXTURE_FOLDER / 'draft_process.json'}: "
            "0.24mm Draft @GB4 0.4 nozzle is missing parent "
            "0.24mm Standard @GB4 0.4 nozzle"
        )

    def test_cli_returns_zero_when_all_parents_exist(self):
        with patch("sys.argv", ["profilelab", str(VALID_FIXTURE_FOLDER)]):
            self.assertEqual(main(), 0)

    def test_cli_returns_one_for_invalid_json(self):
        with (
            patch("sys.argv", ["profilelab", str(INVALID_JSON_FIXTURE_FOLDER)]),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        mock_print.assert_called_once_with(
            f"ERROR: {INVALID_JSON_FIXTURE_FOLDER / 'broken_process.json'}: invalid JSON"
        )

        if __name__ == "__main__":
            unittest.main()
