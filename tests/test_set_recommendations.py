# SPDX-License-Identifier: AGPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog
from profilelab.profile_picker import ProfilePicker
from profilelab.recommendations import recommendation


class RecommendationsTests(unittest.TestCase):
    def setUp(self):
        self.printer = dict(type='machine', name='My printer', nozzle_diameter=['0.4'], default_filament_profile=['Original PLA'])
        self.data = dict(profiles=[self.printer], sources={'machine/My printer': {'name': 'Original printer', 'vendor': 'Vendor'}})
        self.records = [dict(type='filament', name='Original PLA', vendor='Vendor', values={'filament_diameter': ['2.85']}),
                        dict(type='filament', name='Other PLA', vendor='Other', values={'filament_diameter': ['2.85']}),
                        dict(type='filament', name='Wrong PLA', vendor='Vendor', values={'filament_diameter': ['1.75'], 'compatible_printers': ['Original printer']})]

    def test_default_and_other_diameter_match_but_not_conflict(self):
        self.assertTrue(any('Original default' in reason for reason in recommendation(self.records[0], self.data, self.records)))
        self.assertTrue(any('Diameter match' in reason for reason in recommendation(self.records[1], self.data, self.records)))
        self.assertEqual(recommendation(self.records[2], self.data, self.records), [])

    def test_no_nozzle_based_diameter_guess(self):
        self.printer.pop('default_filament_profile')
        self.assertEqual(recommendation(self.records[1], self.data, self.records), [])

    def test_reverse_printer_and_process_links(self):
        data = dict(profiles=[dict(type='filament', name='PLA', compatible_printers=['Printer'], compatible_prints=['Fine'])])
        self.assertTrue(recommendation(dict(type='machine', name='Printer', values={}), data, []))
        self.assertTrue(recommendation(dict(type='process', name='Fine', values={}), data, []))
        self.assertEqual(recommendation(dict(type='process', name='Other', values={}), data, []), [])

    def test_checked_items_survive_search_and_printers_stay_single(self):
        app = QApplication.instance() or QApplication([])
        picker = ProfilePicker(self.records + [dict(type='machine', name='Printer')], multi=True, set_data=self.data)
        picker.category.setCurrentIndex(picker.category.findData('filament'))
        if os.environ.get('PROFILELAB_WIZARD_SCREENSHOT'):
            picker.show()
            app.processEvents()
            picker.grab().save(os.environ['PROFILELAB_WIZARD_SCREENSHOT'])
        picker.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        first = picker.matches[0]
        picker.search.setText('Wrong')
        picker.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        picker.accept_selected()
        self.assertEqual(len(picker.selected_records), 2)
        self.assertIn(first, picker.selected_records)
        picker.category.setCurrentIndex(picker.category.findData('machine'))
        picker.search.clear()
        self.assertFalse(picker.checked)
        self.assertFalse(picker.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable)
        picker.close()

    def test_bulk_add_is_atomic_and_names_are_unique(self):
        from profilelab.profile_sets_view import ProfileSetsView
        from profilelab.profile_sets import new_set, load_sets
        app = QApplication.instance() or QApplication([])
        records = [dict(type='filament', name='PLA', vendor='Vendor', path=str(i),
                        resolve=lambda: ({'filament_diameter': ['2.85']}, '2.4.2')) for i in range(2)]
        with TemporaryDirectory() as root:
            view = ProfileSetsView(Mock(), root=root)
            view.data = new_set('Test')
            view.steps.setCurrentIndex(1)
            selected = Mock(selected_records=records)
            selected.exec.return_value = QDialog.DialogCode.Accepted
            with patch('profilelab.profile_sets_view.ProfilePicker', return_value=selected), patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                view.add(records, library=True)
                self.assertEqual([p['name'] for p in view.data['profiles']], ['PLA - Test', 'PLA - Test (2)'])
                before = deepcopy(view.data)
                records[1]['resolve'] = Mock(side_effect=ValueError('Broken parent'))
                with self.assertRaises(ValueError):
                    view.add(records, library=True)
                self.assertEqual(view.data, before)
                self.assertEqual(load_sets(root)[0], before)
            view.close()
