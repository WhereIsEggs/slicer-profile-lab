# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QComboBox, QLabel
    from profilelab.setting_editor import SettingDialog, display_value
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from profilelab.profile_choices import compatible_filaments


@unittest.skipUnless(AVAILABLE, "Requires desktop extra")
class SettingControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_boolean_strings_round_trip(self):
        dialog = SettingDialog("Fan", "enable_overhang_bridge_fan", ["1", "0"])
        self.assertEqual(display_value(["1", "0"], "enable_overhang_bridge_fan"), "On · Off")
        dialog.editors[0].setCurrentIndex(0)
        dialog.editors[1].setCurrentIndex(1)
        dialog.accept_values()
        self.assertEqual(dialog.value, ["0", "1"])

    def test_numeric_one_is_not_a_switch(self):
        self.assertEqual(display_value("1", "filament_flow_ratio"), "1")
        dialog = SettingDialog("Flow", "filament_flow_ratio", ["1"])
        self.assertNotIsInstance(dialog.editors[0], QComboBox)

    def test_two_extruder_dropdowns(self):
        dialog = SettingDialog("Filament", "default_filament_profile", ["PLA", "PETG"],
                               choices=["PLA", "PETG"], extruder_slots=True)
        labels = [label.text() for label in dialog.findChildren(QLabel)]
        self.assertIn("E0 / Left", labels)
        self.assertIn("E1 / Right", labels)
        self.assertTrue(all(not e.isEditable() for e in dialog.editors))
        dialog.editors[0].setCurrentIndex(dialog.editors[0].findData("PETG"))
        dialog.accept_values()
        self.assertEqual(dialog.value, ["PETG", "PETG"])

    def test_missing_choices_cannot_save(self):
        dialog = SettingDialog("Filament", "default_filament_profile", ["Unknown"])
        dialog.accept_values()
        self.assertEqual(dialog.result(), 0)
        self.assertTrue(dialog.error.text())


class CompatibilityChoiceTests(unittest.TestCase):
    def test_only_verified_unique_concrete_matches(self):
        draft = {"type": "machine", "library": {"revision": "test"}, "base": {"name": "Printer"}}
        def profile(name, printers, **extra):
            return {"name": name, "type": "filament", "vendor": "Example", "path": name,
                    "template": False, "settings": {"compatible_printers": printers, **extra}}
        snapshot = {"metadata": {"revision": "test"}, "profiles": [
            profile("PLA", ["Printer"]), profile("Wrong", ["Other"]),
            profile("Expression", [], compatible_printers_condition="unknown"),
            profile("Duplicate", ["Printer"]), profile("Duplicate", ["Printer"]),
        ]}
        self.assertEqual(compatible_filaments(draft, snapshot), ["PLA"])
        snapshot["metadata"]["revision"] = "different"
        self.assertEqual(compatible_filaments(draft, snapshot), [])
