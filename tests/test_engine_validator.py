import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from profilelab.engine_validator import (
    EngineValidationResult, friendly_engine_details, is_complete_profile_tree,
    run_orca_engine,
)


class EngineValidatorTests(unittest.TestCase):
    def test_complete_tree_requires_catalog_and_vendor_folder(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "Example.json").write_text("{}", encoding="utf-8")
            self.assertFalse(is_complete_profile_tree(folder))
            (folder / "Example").mkdir()
            self.assertTrue(is_complete_profile_tree(folder))

    def test_individual_profile_folder_is_not_sent_to_orca(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "profile.json").write_text('{"name": "Example"}', encoding="utf-8")
            result = run_orca_engine(folder)
        self.assertEqual(result.status, "not_applicable")

    def test_engine_uses_a_temporary_copy_and_full_modes(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary) / "profiles"
            vendor = folder / "Example"
            vendor.mkdir(parents=True)
            (folder / "Example.json").write_text("{}", encoding="utf-8")
            (vendor / "preset.json").write_text('{"name": "Example"}', encoding="utf-8")
            executable = Path(temporary) / "validator.exe"
            executable.touch()
            completed = subprocess.CompletedProcess([], 0, "Validation completed successfully", "")
            with patch("profilelab.engine_validator.validator_path", return_value=executable), \
                 patch("profilelab.engine_validator.subprocess.run", return_value=completed) as run:
                result = run_orca_engine(folder)
            command = run.call_args.args[0]
            self.assertEqual(result.status, "passed")
            self.assertIn("--slice", command)
            self.assertIn("--check_filament_subtypes", command)
            self.assertNotIn(str(folder), command)
            copied_folder = Path(command[command.index("--path") + 1])
            self.assertTrue(str(copied_folder).endswith("resources\\profiles"))

    def test_engine_errors_keep_only_relevant_lines(self):
        self.assertEqual(
            friendly_engine_details("progress\n[error] broken parent\nfinished"),
            "[error] broken parent",
        )

    def test_missing_engine_is_explained(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with patch("profilelab.engine_validator.validator_path", return_value=folder / "missing.exe"):
                result = run_orca_engine(folder)
        self.assertEqual(result.status, "unavailable")
