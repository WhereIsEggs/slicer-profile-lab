# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from profilelab.validation import validate_folder


FIXTURES = Path(__file__).parent / "fixtures"


class ValidationReportTests(unittest.TestCase):
    def test_valid_folder_returns_a_report_without_printing(self):
        with patch("builtins.print") as output:
            report = validate_folder(FIXTURES / "valid_parent")

        self.assertTrue(report.is_valid)
        self.assertEqual(report.issues, [])
        output.assert_not_called()

    def test_missing_parent_returns_structured_issue_without_printing(self):
        with patch("builtins.print") as output:
            report = validate_folder(FIXTURES / "missing_parent")

        self.assertFalse(report.is_valid)
        self.assertEqual(len(report.issues), 1)
        issue = report.issues[0]
        self.assertEqual(issue.kind, "missing_parent")
        self.assertEqual(
            issue.paths, [FIXTURES / "missing_parent" / "draft_process.json"]
        )
        self.assertIn("is missing parent", issue.message)
        output.assert_not_called()

    def test_invalid_json_returns_a_report_instead_of_raising(self):
        report = validate_folder(FIXTURES / "invalid_json")

        self.assertFalse(report.is_valid)
        self.assertEqual(report.issues[0].kind, "invalid_profile")
        self.assertEqual(
            report.issues[0].paths,
            [FIXTURES / "invalid_json" / "broken_process.json"],
        )

    def test_system_tree_checks_setting_ids_but_user_folder_does_not(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            vendor = root / "Example"
            process = vendor / "process"
            process.mkdir(parents=True)
            (root / "Example.json").write_text("{}", encoding="utf-8")
            (process / "profile.json").write_text(
                '{"name":"Print","instantiation":"true","setting_id":"wrong"}',
                encoding="utf-8",
            )
            report = validate_folder(root)
        self.assertEqual(report.issues[0].kind, "setting_id")
        self.assertIn("stale", report.issues[0].message)

    def test_system_tree_checks_orca_compatibility_references(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            vendor = root / "Example"
            (vendor / "filament").mkdir(parents=True)
            (vendor / "machine").mkdir()
            (root / "Example.json").write_text("{}", encoding="utf-8")
            (vendor / "filament" / "pla.json").write_text(
                '{"name":"PLA","instantiation":"true","setting_id":"wrong",'
                '"compatible_printers":["Missing"],"filament_type":"PLA"}', encoding="utf-8"
            )
            (vendor / "machine" / "printer.json").write_text(
                '{"name":"Printer","default_filament_profile":["Missing material"],'
                '"extruder_clearance_radius":"1","extruder_clearance_max_radius":"1"}',
                encoding="utf-8",
            )
            report = validate_folder(root)
        messages = "\n".join(issue.message for issue in report.issues)
        self.assertIn("unknown compatible_printers", messages)
        self.assertIn("missing default filament", messages)
        self.assertIn("filament_type", messages)
        self.assertIn("conflicting settings", messages)
