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
