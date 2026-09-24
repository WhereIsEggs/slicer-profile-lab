# SPDX-License-Identifier: AGPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QDialog
from profilelab.profile_sets import new_set, add_copy, save_set, load_sets
from profilelab.profile_sets_view import ProfileSetsView


class SetEditSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_save_keeps_profile_tab_and_setting_for_all_categories(self):
        cases = [('machine', 'nozzle_diameter', ['0.4'], ['0.8']),
                 ('filament', 'additional_cooling_fan_speed', ['70'], ['60']),
                 ('process', 'layer_height', '0.2', '0.3')]
        with TemporaryDirectory() as folder:
            root = Path(folder)
            data = new_set('Selection')
            for kind, key, value, _ in cases:
                add_copy(data, kind, kind, {key: value}, '2.4.2')
            save_set(root, data)
            view = ProfileSetsView(None, root=root)
            self.addCleanup(view.close)
            view.open_set(1)
            for step, (kind, key, _, changed) in enumerate(cases):
                view.steps.setCurrentIndex(step)
                view.members.setCurrentRow(0)
                page = view.setting_tabs.mapping.get(key, ('Other settings', ''))[0]
                tab = next(i for i in range(view.setting_tabs.count()) if view.setting_tabs.tabText(i) == page)
                view.setting_tabs.setCurrentIndex(tab)
                row = view.keys.index(key)
                view.values.setCurrentCell(row, 1)
                with patch('profilelab.profile_sets_view.SettingDialog') as dialog:
                    dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
                    dialog.return_value.value = changed
                    view.edit(row, 1)
                self.assertEqual(view.members.currentRow(), 0)
                self.assertEqual(view.setting_tabs.tabText(view.setting_tabs.currentIndex()), page)
                self.assertFalse(view.setting_tabs.isHidden())
                self.assertEqual(view.keys[view.values.currentRow()], key)
                saved = next(p for p in load_sets(root)[0]['profiles'] if p['type'] == kind)
                self.assertEqual(saved[key], changed)
