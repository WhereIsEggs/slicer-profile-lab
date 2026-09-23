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
