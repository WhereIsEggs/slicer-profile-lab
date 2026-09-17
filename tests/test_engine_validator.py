# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
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
    def test_compiled_runtime_is_valid_for_loading_not_source_audit(self):
        from profilelab.engine_validator import is_runtime_profile_tree
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Example.opc").write_bytes(b"fictional cache")
            self.assertTrue(is_runtime_profile_tree(root))
            self.assertFalse(is_complete_profile_tree(root))

    def test_compiled_only_runtime_never_claims_full_validation(self):
        from profilelab.engine_validator import run_orca_engine_for_user_profiles
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "profiles").mkdir()
            (root / "profiles" / "Example.opc").write_bytes(b"fictional cache")
            user = root / "user"
            user.mkdir()
            with patch("profilelab.engine_validator.subprocess.run") as run:
                result = run_orca_engine_for_user_profiles(root, user)
            self.assertEqual(result.status, "not_applicable")
            self.assertIn("compiled profiles only", result.message)
            run.assert_not_called()

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

    def test_user_profiles_overlay_only_a_temporary_system_copy(self):
        from profilelab.engine_validator import run_orca_engine_for_user_profiles
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "system"
            profiles = resources / "profiles"
            (profiles / "Example").mkdir(parents=True)
            (profiles / "Example.json").write_text("{}", encoding="utf-8")
            user = root / "user"
            user.mkdir()
            (user / "custom.json").write_text('{"name":"Custom"}', encoding="utf-8")
            executable = root / "validator.exe"
            executable.touch()
            with patch("profilelab.engine_validator.validator_path", return_value=executable), \
                 patch("profilelab.engine_validator.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as run:
                result = run_orca_engine_for_user_profiles(resources, user)
            copied_tree = Path(run.call_args.args[0][run.call_args.args[0].index("--path") + 1])
            self.assertEqual(result.status, "passed")
            self.assertNotIn(str(user), run.call_args.args[0])
            self.assertNotIn("--slice", run.call_args.args[0])
            self.assertNotIn("--check_filament_subtypes", run.call_args.args[0])
            self.assertTrue(str(copied_tree).endswith("resources\\profiles"))

    def test_local_system_parents_and_findings_stay_in_temporary_workspace(self):
        from profilelab.engine_validator import run_orca_engine_for_user_profiles
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "runtime" / "resources"
            (resources / "profiles" / "Example").mkdir(parents=True)
            (resources / "profiles" / "Example.json").write_text("{}")
            user = root / "Orca" / "user" / "default"
            user.mkdir(parents=True)
            system = root / "Orca" / "system"
            system.mkdir()
            (system / "Local.json").write_text("{}")
            def check(exe, tree, timeout, slice_profiles=True):
                self.assertFalse(slice_profiles)
                self.assertEqual((tree / "Local.json").read_text(), "{}")
                return EngineValidationResult("failed", "Failed", "[error] " + str(tree / "user" / "default" / "custom.json") + " missing parent\n[error] system issue")
            with patch("profilelab.engine_validator._run_copied_tree", side_effect=check):
                result = run_orca_engine_for_user_profiles(resources, user)
            self.assertIn("Your profiles", result.details)
            self.assertIn("System library or engine findings", result.details)
            self.assertNotIn(temporary, result.details)
            self.assertEqual((system / "Local.json").read_text(), "{}")

    def test_resources_come_from_engine_installation(self):
        from profilelab.engine_validator import validation_engine_resources
        with patch("profilelab.engine_validator.validator_path", return_value=Path("runtime") / "validator.exe"):
            self.assertEqual(validation_engine_resources(), Path("runtime") / "resources")

    def test_missing_engine_is_reported_as_a_start_failure(self):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "Example").mkdir()
            (folder / "Example.json").write_text("{}", encoding="utf-8")
            with patch("profilelab.engine_validator.validator_path", return_value=folder / "missing.exe"):
                result = run_orca_engine(folder)
        self.assertEqual(result.status, "failed")
