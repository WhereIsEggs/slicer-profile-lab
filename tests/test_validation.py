import unittest
from pathlib import Path
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
