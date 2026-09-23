# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from profilelab.setting_labels import setting_label, setting_help
from profilelab.orca_setting_labels import SETTINGS, SOURCE_REVISION


class SettingLabelTests(unittest.TestCase):
    def test_upstream_catalog_and_context(self):
        self.assertGreater(len(SETTINGS), 800)
        self.assertEqual(len(SOURCE_REVISION), 40)
        label = setting_label('additional_cooling_fan_speed')
        self.assertIn('Auxiliary', label)
        self.assertIn('%', label)
        self.assertIn('additional_cooling_fan_speed', setting_help('additional_cooling_fan_speed'))
        self.assertIn('auxiliary', setting_help('additional_cooling_fan_speed'))

    def test_unknown_key_is_not_lost(self):
        self.assertEqual(setting_label('new_future_option'), 'New future option')
        self.assertIn('new_future_option', setting_help('new_future_option'))

    def test_display_metadata_never_renames_saved_key(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from profilelab.setting_editor import SettingDialog
        app = QApplication.instance() or QApplication([])
        original = ['70']
        dialog = SettingDialog('Old label', 'additional_cooling_fan_speed', original)
        self.assertEqual(dialog.key, 'additional_cooling_fan_speed')
        self.assertEqual(dialog.windowTitle(), setting_label(dialog.key))
        dialog.editors[0].setText('60')
        dialog.accept_values()
        self.assertEqual(dialog.value, ['60'])
        self.assertEqual(original, ['70'])
        dialog.close()
