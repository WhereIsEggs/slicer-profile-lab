# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from profilelab.profile_picker import ProfilePicker


class ProfilePickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.records = [dict(name='Printer 0.4', type='machine', vendor='Alpha'),
                        dict(name='Printer 0.4', type='machine', vendor='Beta'),
                        dict(name='PLA', type='filament', vendor='Alpha')]
        self.picker = ProfilePicker(self.records)

    def tearDown(self):
        self.picker.close()

    def test_starts_empty_until_category_chosen(self):
        self.assertEqual(self.picker.table.rowCount(), 0)
        self.assertFalse(self.picker.choose.isEnabled())

    def test_library_location_is_independent_of_brand_and_compatibility(self):
        from copy import deepcopy
        records = [dict(name='Shared tuned', type='filament', vendor='OrcaFilamentLibrary',
                        values={'filament_vendor': ['Polymaker'], 'compatible_printers': ['Printer']}),
                   dict(name='Vendor unrestricted', type='filament', vendor='BBL',
                        values={'filament_vendor': ['Polymaker'], 'compatible_printers': []})]
        before = deepcopy(records)
        picker = ProfilePicker(records, multi=True)
        self.addCleanup(picker.close)
        picker.category.setCurrentIndex(2)
        picker.brand.setCurrentIndex(picker.brand.findData('Polymaker'))
        picker.location.setCurrentIndex(picker.location.findData('shared'))
        self.assertEqual(picker.matches, [records[0]])
        self.assertIn('Linked to specific printers', picker.table.item(0, 2).text())
        child = picker.family_tree.topLevelItem(0).child(0)
        self.assertIn('Linked to specific printers', child.text(2))
        picker.checked.add(id(records[0]))
        picker.location.setCurrentIndex(picker.location.findData('printer'))
        self.assertEqual(picker.matches, [records[1]])
        self.assertIn('No explicit printer restriction', picker.table.item(0, 2).text())
        self.assertIn(id(records[0]), picker.checked)
        picker.vendor.setCurrentIndex(picker.vendor.findData('OrcaFilamentLibrary'))
        self.assertEqual(picker.matches, [])
        picker.category.setCurrentIndex(1)
        self.assertTrue(picker.location.isHidden())
        self.assertEqual(picker.location.currentData(), '')
        self.assertEqual(records, before)

    def test_printer_scope_respects_conditions_and_unresolved_sources(self):
        from profilelab.profile_picker import printer_scope
        self.assertEqual(printer_scope({'values': {'compatible_printers_condition': 'nozzle_diameter[0] == 0.4'}}),
                         'Conditional printer restriction')
        self.assertEqual(printer_scope({'source_error': 'Missing parent'}), 'Printer restrictions unresolved')
        self.assertEqual(printer_scope({'values': {'compatible_printers': 'bad'}}), 'Printer restrictions need review')

    def test_filament_brand_search_uses_inherited_values_across_sources(self):
        from copy import deepcopy
        from profilelab.resolver import ProfileResolver
        base = dict(name='Product base', type='filament', vendor='OrcaFilamentLibrary',
                    path='base.json', settings={'filament_vendor': ['Polymaker']})
        leaf = dict(name='PolyTerra PLA', type='filament', vendor='BBL', path='leaf.json',
                    settings={'inherits': 'Product base'})
        leaf['values'] = {k: v.value for k, v in ProfileResolver([base, leaf]).resolve(leaf).items()}
        other = dict(name='PolyLite PLA', type='filament', vendor='Qidi',
                     values={'filament_vendor': ['Polymaker']})
        unknown = dict(name='Unknown PLA', type='filament', vendor='BBL')
        records = [leaf, other, unknown]
        before = deepcopy(records)
        picker = ProfilePicker(records, multi=True)
        self.addCleanup(picker.close)
        picker.category.setCurrentIndex(2)
        self.assertGreater(picker.brand.findData('Polymaker'), 0)
        self.assertEqual(picker.brand.findData('BBL'), -1)
        picker.search.setText('polymaker')
        self.assertEqual({id(r) for r in picker.matches}, {id(leaf), id(other)})
        picker.search.clear()
        picker.brand.setCurrentIndex(picker.brand.findData('Polymaker'))
        self.assertEqual(len(picker.matches), 2)
        picker.checked.add(id(other))
        picker.vendor.setCurrentIndex(picker.vendor.findData('BBL'))
        self.assertEqual(picker.matches, [leaf])
        self.assertIn(id(other), picker.checked)
        picker.category.setCurrentIndex(1)
        self.assertTrue(picker.brand.isHidden())
        self.assertEqual(records, before)

    def test_filters_and_selects_exact_record(self):
        self.picker.category.setCurrentIndex(1)
        self.picker.vendor.setCurrentIndex(self.picker.vendor.findData('Beta'))
        self.picker.search.setText('PRINTER 0.4')
        self.assertEqual(len(self.picker.matches), 1)
        self.picker.table.selectRow(0)
        self.picker.accept_selected()
        self.assertIs(self.picker.selected_record, self.records[1])

    def test_filter_clears_stale_selection(self):
        self.picker.category.setCurrentIndex(1)
        self.picker.table.selectRow(0)
        self.picker.search.setText('No such profile')
        self.assertFalse(self.picker.choose.isEnabled())
        self.picker.accept_selected()
        self.assertIsNone(self.picker.selected_record)

    def test_category_rebuilds_vendor_choices(self):
        self.picker.category.setCurrentIndex(2)
        self.assertEqual(self.picker.vendor.findData('Beta'), -1)
        self.assertEqual(self.picker.matches, [self.records[2]])

    def test_model_and_variant_filters_keep_exact_identity(self):
        self.records[0].update(model='Small', variant='0.4', source_chain=['Root', 'Printer 0.4'])
        self.records[1].update(model='Large', variant='0.8')
        self.picker.category.setCurrentIndex(1)
        self.picker.model.setCurrentIndex(self.picker.model.findData('Small'))
        self.assertEqual(self.picker.matches, [self.records[0]])
        self.assertEqual(self.picker.nozzle.findData('0.8'), -1)
        self.picker.table.selectRow(0)
        self.assertIn('Root → Printer 0.4', self.picker.details.text())
        self.picker.accept_selected()
        self.assertIs(self.picker.selected_record, self.records[0])

    def test_no_name_based_parent_or_variant_inference(self):
        self.picker.category.setCurrentIndex(1)
        self.assertEqual(self.picker.model.count(), 1)
        self.assertEqual(self.picker.nozzle.count(), 1)
        self.assertEqual(len(self.picker.matches), 2)

    def test_broken_source_cannot_be_accepted(self):
        self.records[0]['source_error'] = 'Missing parent'
        self.picker.category.setCurrentIndex(1)
        self.picker.table.selectRow(0)
        self.assertFalse(self.picker.choose.isEnabled())
        self.picker.accept_selected()
        self.assertIsNone(self.picker.selected_record)
