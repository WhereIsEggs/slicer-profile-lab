import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from profilelab.validator import (
    find_duplicate_profile_names,
    find_missing_parents,
)
from unittest.mock import patch
from profilelab.cli import main
import json
from profilelab.loader import InvalidProfileError, load_profile
from shutil import copyfile
from profilelab.validator import (
    find_duplicate_profile_names,
    find_inheritance_cycles,
    find_missing_parents,
)

FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "missing_parent"
VALID_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "valid_parent"
ROOT_PROFILE_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "root_profile"
INVALID_JSON_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "invalid_json"
DUPLICATE_NAMES_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "duplicate_names"
INVALID_STRUCTURE_FIXTURE_FOLDER = (
    Path(__file__).parent / "fixtures" / "invalid_structure"
)
MISSING_NAME_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "missing_name"
MULTIPLE_MISSING_PARENTS_FIXTURE_FOLDER = (
    Path(__file__).parent / "fixtures" / "multiple_missing_parents"
)
SELF_INHERITANCE_FIXTURE_FOLDER = (
    Path(__file__).parent / "fixtures" / "self_inheritance"
)
TWO_PROFILE_CYCLE_FIXTURE_FOLDER = (
    Path(__file__).parent / "fixtures" / "two_profile_cycles"
)

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

    def test_cli_returns_one_for_a_missing_folder(self):
        missing_folder = Path(__file__).parent / "fixtures" / "does_not_exist"

        with (
            patch("sys.argv", ["profilelab", str(missing_folder)]),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        mock_print.assert_called_once_with(
            f"ERROR: {missing_folder}: folder does not exist"
        )

    def test_reports_duplicate_profile_names(self):
        errors = find_duplicate_profile_names(DUPLICATE_NAMES_FIXTURE_FOLDER)

        self.assertEqual(
            errors,
            [
                {
                    "profile": "0.24mm Standard @GB4 0.4 nozzle",
                    "paths": [
                        str(DUPLICATE_NAMES_FIXTURE_FOLDER / "base_process.json"),
                        str(DUPLICATE_NAMES_FIXTURE_FOLDER / "copied_process.json"),
                    ],
                }
            ],
        )

    def test_cli_returns_one_for_duplicate_profile_names(self):
        with (
            patch("sys.argv", ["profilelab", str(DUPLICATE_NAMES_FIXTURE_FOLDER)]),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        mock_print.assert_called_once_with(
            "ERROR: duplicate profile name "
            "'0.24mm Standard @GB4 0.4 nozzle' appears in: "
            f"{DUPLICATE_NAMES_FIXTURE_FOLDER / 'base_process.json'}, "
            f"{DUPLICATE_NAMES_FIXTURE_FOLDER / 'copied_process.json'}"
        )

    def test_accepts_unique_profile_names(self):
        errors = find_duplicate_profile_names(VALID_FIXTURE_FOLDER)

        self.assertEqual(errors, [])

    def test_cli_returns_one_for_an_empty_folder(self):
        with TemporaryDirectory() as empty_folder:
            with (
                patch("sys.argv", ["profilelab", empty_folder]),
                patch("builtins.print") as mock_print,
            ):
                self.assertEqual(main(), 1)

            mock_print.assert_called_once_with(
                f"ERROR: {empty_folder}: no JSON profile files found"
            )

    def test_cli_returns_one_for_a_non_object_profile(self):
        with (
            patch(
                "sys.argv",
                ["profilelab", str(INVALID_STRUCTURE_FIXTURE_FOLDER)],
            ),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        mock_print.assert_called_once_with(
            f"ERROR: {INVALID_STRUCTURE_FIXTURE_FOLDER / 'list_profile.json'}: "
            "profile must be a JSON object"
        )

    def test_cli_returns_one_for_a_profile_without_a_name(self):
        with (
            patch("sys.argv", ["profilelab", str(MISSING_NAME_FIXTURE_FOLDER)]),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        mock_print.assert_called_once_with(
            f"ERROR: {MISSING_NAME_FIXTURE_FOLDER / 'unnamed_process.json'}: "
            "profile must have a nonempty string name"
        )

    def test_rejects_invalid_profile_names(self):
        for name in ("", "   ", 123):
            with self.subTest(name=name):
                with TemporaryDirectory() as folder:
                    profile_path = Path(folder) / "invalid_name.json"
                    profile_path.write_text(
                        json.dumps({"name": name, "type": "process"}),
                        encoding="utf-8",
                    )

                    with self.assertRaises(InvalidProfileError) as caught:
                        load_profile(profile_path)

                    self.assertEqual(
                        caught.exception.reason,
                        "profile must have a nonempty string name",
                    )
                    self.assertEqual(
                        caught.exception.profile_path,
                        profile_path,
                    )

    def test_cli_reports_all_missing_parents(self):
        folder = MULTIPLE_MISSING_PARENTS_FIXTURE_FOLDER

        with (
            patch("sys.argv", ["profilelab", str(folder)]),
            patch("builtins.print") as mock_print,
        ):
            self.assertEqual(main(), 1)

        messages = [call.args[0] for call in mock_print.call_args_list]

        self.assertCountEqual(
            messages,
            [
                f"ERROR: {folder / 'first_process.json'}: "
                "First Process is missing parent Missing Base A",
                f"ERROR: {folder / 'second_process.json'}: "
                "Second Process is missing parent Missing Base B",
            ],
        )

    def test_cli_reports_missing_parents_and_duplicates_together(self):
        with TemporaryDirectory() as folder:
            folder_path = Path(folder)

            copyfile(
                MULTIPLE_MISSING_PARENTS_FIXTURE_FOLDER / "first_process.json",
                folder_path / "first_process.json",
            )
            copyfile(
                DUPLICATE_NAMES_FIXTURE_FOLDER / "base_process.json",
                folder_path / "base_process.json",
            )
            copyfile(
                DUPLICATE_NAMES_FIXTURE_FOLDER / "copied_process.json",
                folder_path / "copied_process.json",
            )

            with (
                patch("sys.argv", ["profilelab", folder]),
                patch("builtins.print") as mock_print,
            ):
                self.assertEqual(main(), 1)

        messages = [call.args[0] for call in mock_print.call_args_list]

        self.assertCountEqual(
            messages,
            [
                f"ERROR: {folder_path / 'first_process.json'}: "
                "First Process is missing parent Missing Base A",
                "ERROR: duplicate profile name "
                "'0.24mm Standard @GB4 0.4 nozzle' appears in: "
                f"{folder_path / 'base_process.json'}, "
                f"{folder_path / 'copied_process.json'}",
            ],
        )
        
    def test_accepts_a_parent_in_another_subfolder(self):
        with TemporaryDirectory() as folder:
            folder_path = Path(folder)
            parent_folder = folder_path / "parents"
            child_folder = folder_path / "children"
            
            parent_folder.mkdir()
            child_folder.mkdir()
            
            copyfile(
                VALID_FIXTURE_FOLDER / "base_process.json",
                parent_folder / "base_process.json",
            )
            copyfile(
                VALID_FIXTURE_FOLDER / "draft_process.json",
                child_folder / "draft_process.json",
            )
            
            errors = find_missing_parents(folder_path)
            
            self.assertEqual(errors, [])
            
    def test_reports_self_inheritance(self):
        cycles = find_inheritance_cycles(SELF_INHERITANCE_FIXTURE_FOLDER)
        
        self.assertEqual(
            cycles,
            [["Self Process", "Self Process"]],
        )
        
    def test_reports_a_two_profile_cycle_once(self):
        cycles = find_inheritance_cycles(TWO_PROFILE_CYCLE_FIXTURE_FOLDER)
        
        self.assertEqual(
            cycles,
            [["Process A", "Process B", "Process A"]],
        )

        if __name__ == "__main__":
            unittest.main()
