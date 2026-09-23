# SPDX-License-Identifier: AGPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from profilelab.setting_tabs import SettingTabs, ordered_keys
from profilelab.orca_setting_layout import LAYOUT


class SettingTabsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_filament_order(self):
        pages = list(dict.fromkeys(p for _, p, _ in LAYOUT['filament']))
        self.assertEqual(pages, ['Filament', 'Cooling', 'Setting Overrides', 'Advanced', 'Multimaterial', 'Dependencies', 'Notes'])
        keys = ['additional_cooling_fan_speed', 'filament_diameter', 'filament_vendor', 'filament_type', 'filament_retraction_length']
        self.assertEqual(ordered_keys('filament', keys), ['filament_type', 'filament_vendor', 'filament_diameter', 'additional_cooling_fan_speed', 'filament_retraction_length'])

    def test_set_notes_saved_immediately_and_survive_switching(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from profilelab.profile_sets import new_set, add_copy, save_set, load_sets
        from profilelab.profile_sets_view import ProfileSetsView
        with TemporaryDirectory() as folder:
            root = Path(folder)
            data = new_set('Notes test')
            add_copy(data, 'machine', 'First', {'nozzle_diameter': ['0.4']}, '2.4.2')
            add_copy(data, 'machine', 'Second', {'nozzle_diameter': ['0.8']}, '2.4.2')
            save_set(root, data)
            view = ProfileSetsView(None, root=root)
            view.open_set(1)
            view.members.setCurrentRow(0)
            view.setting_tabs.notes.insertPlainText('Hello')
            view.setting_tabs.notes.insertPlainText('\nWorld')
            self.assertEqual(load_sets(root)[0]['profiles'][0]['printer_notes'], 'Hello\nWorld')
            self.assertEqual(view.setting_tabs.notes.textCursor().position(), 11)
            view.members.setCurrentRow(1)
            self.assertEqual(view.setting_tabs.notes.toPlainText(), '')
            view.setting_tabs.notes.insertPlainText('Second notes')
            view.open_set(1)
            self.assertEqual(view.data['profiles'][0]['printer_notes'], 'Hello\nWorld')
            self.assertEqual(view.data['profiles'][1]['printer_notes'], 'Second notes')
            view.close()

    def test_failed_autosave_is_visible_and_keeps_text(self):
        table = QTableWidget()
        tabs = SettingTabs(table)
        def fail(text):
            raise OSError('Disk unavailable')
        tabs.configure_notes('', fail)
        tabs.notes.insertPlainText('Keep this')
        self.assertIn('could not be saved', tabs.notes_status.text())
        self.assertEqual(tabs.notes.toPlainText(), 'Keep this')
        tabs.notes_panel.close()
        table.close()
        tabs.close()

    def test_dependencies_hidden_and_notes_editable_for_each_kind(self):
        for kind, key in [('machine', 'printer_notes'), ('filament', 'filament_notes'), ('process', 'notes')]:
            table = QTableWidget(1, 2)
            table.setItem(0, 0, QTableWidgetItem(key))
            tabs = SettingTabs(table)
            saved = []
            tabs.configure(kind, [key])
            tabs.configure_notes('Original', saved.append)
            pages = [tabs.tabText(i) for i in range(tabs.count())]
            self.assertNotIn('Dependencies', pages)
            tabs.setCurrentIndex(pages.index('Notes'))
            self.assertTrue(table.isHidden())
            self.assertFalse(tabs.notes_panel.isHidden())
            tabs.notes.setPlainText('New notes\nSecond line')
            self.assertEqual(saved, ['New notes\nSecond line'])
            tabs.configure_notes('Another profile', saved.append)
            self.assertEqual(saved, ['New notes\nSecond line'])
            table.close()
            tabs.notes_panel.close()
            tabs.close()

    def test_tabs_search_unknown_and_preserved_selection(self):
        keys = ordered_keys('filament', ['filament_type', 'additional_cooling_fan_speed', 'future_option'])
        table = QTableWidget(len(keys), 2)
        tabs = SettingTabs(table)
        for row, key in enumerate(keys):
            table.setItem(row, 0, QTableWidgetItem(key))
        tabs.configure('filament', keys)
        self.assertFalse(table.isRowHidden(0))
        self.assertTrue(table.isRowHidden(1))
        tabs.setCurrentIndex(1)
        self.assertFalse(table.isRowHidden(1))
        tabs.configure('', [])
        tabs.configure('filament', keys)
        self.assertEqual(tabs.tabText(tabs.currentIndex()), 'Cooling')
        tabs.apply(query='future_option')
        self.assertFalse(table.isRowHidden(2))
        tabs.setCurrentIndex(0)
        self.assertFalse(table.isRowHidden(2))
        tabs.apply(query='')
        tabs.setCurrentIndex(tabs.count() - 1)
        self.assertFalse(table.isRowHidden(2))
        self.assertEqual([table.item(i, 0).text() for i in range(3)], keys)
        table.close()
        tabs.close()
