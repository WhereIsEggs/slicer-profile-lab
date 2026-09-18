# SPDX-License-Identifier: AGPL-3.0-only
import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from profilelab.library_choices import filament_families, matching_variants
from profilelab.profile_picker import ProfilePicker


class FamilyTests(unittest.TestCase):
    def setUp(self):
        self.records = [dict(name=name, type='filament', vendor='re3D', settings={'filament_id': 'PC'},
                             values={'compatible_printers': links}) for name, links in [
            ('re3D PC', ['Printer 0.4', 'Printer 0.8']),
            ('re3D PC @0.4 nozzle', ['Printer 0.4']),
            ('re3D PC @0.8 nozzle', ['Printer 0.8'])]]
        self.data = {'profiles': [{'name': 'Printer 0.4', 'type': 'machine'}]}

    def test_metadata_grouping_and_narrow_variant_selection(self):
        self.assertEqual(len(filament_families(self.records)), 1)
        self.assertEqual(matching_variants(self.records, self.data), {id(self.records[1])})
        self.data['profiles'].append({'name': 'Printer 0.8', 'type': 'machine'})
        self.assertEqual(matching_variants(self.records, self.data), {id(self.records[1]), id(self.records[2])})
        self.assertEqual(matching_variants(self.records, {'profiles': []}), set())

    def test_no_grouping_by_name_or_across_vendors(self):
        self.records[2]['vendor'] = 'Other'
        self.records[1]['settings'] = {}
        self.assertEqual(len(filament_families(self.records)), 3)

    def test_family_checkbox_preserves_exact_identity_and_base_is_accessible(self):
        app = QApplication.instance() or QApplication([])
        picker = ProfilePicker(self.records, multi=True, set_data=self.data)
        picker.category.setCurrentIndex(picker.category.findData('filament'))
        parent = picker.family_tree.topLevelItem(0)
        self.assertEqual(parent.childCount(), 3)
        parent.setCheckState(0, Qt.CheckState.Checked)
        self.assertEqual(picker.checked, {id(self.records[1])})
        picker.search.setText('PC')
        self.assertEqual(picker.checked, {id(self.records[1])})
        picker.accept_selected()
        self.assertIs(picker.selected_records[0], self.records[1])
        if os.environ.get('PROFILELAB_FAMILY_SCREENSHOT'):
            picker.show()
            picker.family_tree.expandAll()
            app.processEvents()
            picker.grab().save(os.environ['PROFILELAB_FAMILY_SCREENSHOT'])
        picker.close()
