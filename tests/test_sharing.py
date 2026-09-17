from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from profilelab.sharing import collect_profiles, prepare_package, verify_package


def fictional_set():
    return [
        {"type": "machine", "name": "Lab Printer", "inherits": "Lab Base",
         "default_print_profile": "Lab Process", "default_filament_profile": ["Lab PLA"]},
        {"type": "machine", "name": "Lab Base", "nozzle_diameter": ["0.4"]},
        {"type": "process", "name": "Lab Process", "compatible_printers": ["Lab Printer"]},
        {"type": "filament", "name": "Lab PLA", "compatible_printers": ["Lab Printer"]},
        {"type": "filament", "name": "Unrelated material"},
    ]


class SharingTests(unittest.TestCase):
    def test_package_is_complete_without_original_library(self):
        profiles = fictional_set()
        original = deepcopy(profiles)
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "example.profilelab.zip"
            result = prepare_package(profiles, [("machine", "Lab Printer")], destination)
            self.assertEqual(len(result), 4)
            self.assertEqual(profiles, original)
            profiles.clear()
            self.assertEqual(verify_package(destination), result)
            with self.assertRaises(FileExistsError):
                prepare_package(original, [("machine", "Lab Printer")], destination)

    def test_missing_parent_prevents_creating_package(self):
        profiles = fictional_set()
        profiles.pop(1)
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "broken.zip"
            with self.assertRaisesRegex(ValueError, "Lab Base.*missing"):
                prepare_package(profiles, [("machine", "Lab Printer")], destination)
            self.assertFalse(destination.exists())

    def test_ambiguous_dependency_is_not_guessed(self):
        profiles = fictional_set()
        profiles.append(deepcopy(profiles[1]))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            collect_profiles(profiles, [("machine", "Lab Printer")])

    def test_inheritance_cycle_is_rejected_but_compatibility_cycles_are_valid(self):
        profiles = fictional_set()
        profiles[1]["inherits"] = "Lab Printer"
        with self.assertRaisesRegex(ValueError, "Inheritance cycle"):
            collect_profiles(profiles, [("machine", "Lab Printer")])

    def test_conditions_are_preserved_not_treated_as_dependencies(self):
        profiles = fictional_set()
        profiles[2]["compatible_printers_condition"] = 'printer_model=="Example"'
        result = collect_profiles(profiles, [("machine", "Lab Printer")])
        self.assertEqual(next(p for p in result if p["type"] == "process")["compatible_printers_condition"], 'printer_model=="Example"')

    def test_compatibility_is_not_dependency_ownership(self):
        profiles = fictional_set()
        profiles[3]["compatible_printers"] = ["Other Printer", "Lab Printer"]
        result = collect_profiles(profiles, [("filament", "Lab PLA")])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["compatible_printers"], ["Other Printer", "Lab Printer"])
