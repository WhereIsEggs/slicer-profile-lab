import unittest
from pathlib import Path

from profilelab.validator import find_missing_parents

FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "missing_parent"
VALID_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "valid_parent"
ROOT_PROFILE_FIXTURE_FOLDER = Path(__file__).parent / "fixtures" / "root_profile"


class MissingParentTests(unittest.TestCase):
    def test_reports_a_missing_parent(self):
        errors = find_missing_parents(FIXTURE_FOLDER)

        self.assertEqual(
            errors,
            [
                {
                    "profile": "0.24mm Draft @GB4 0.4 nozzle",
                    "missing_parent": "0.24mm Standard @GB4 0.4 nozzle",
                }
            ],
        )

    def test_accepts_a_profile_without_a_parent(self):
        errors = find_missing_parents(ROOT_PROFILE_FIXTURE_FOLDER)

        self.assertEqual(errors, [])

    def test_accepts_an_existing_parent(self):
        errors = find_missing_parents(VALID_FIXTURE_FOLDER)

        self.assertEqual(errors, [])

        if __name__ == "__main__":
            unittest.main()
