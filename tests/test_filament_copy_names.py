# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import unittest
from profilelab.library_choices import copy_name
from profilelab.profile_sets import new_set, add_copy


class FilamentCopyNameTests(unittest.TestCase):
    def test_process_and_printer_names_do_not_include_set_name(self):
        data = new_set('Variant Test')
        process = {'name': '0.26 Standard @Old Printer', 'type': 'process'}
        printer = {'name': 'Gigabot 0.8 nozzle', 'type': 'machine'}
        self.assertEqual(copy_name(process, {}, data), '0.26 Standard')
        self.assertEqual(copy_name(printer, {}, data), 'Gigabot 0.8 nozzle')
        add_copy(data, 'process', '0.26 Standard', {}, '2.4.2')
        self.assertEqual(copy_name(process, {}, data), '0.26 Standard (2)')
    def test_clean_name_preserves_resolved_vendor(self):
        data = new_set('Variant Test')
        record = {'name': 'Polymaker Panchroma PLA @System', 'type': 'filament', 'vendor': 'BBL'}
        values = {'filament_vendor': ['Polymaker'], 'filament_diameter': ['1.75']}
        before = deepcopy(values)
        name = copy_name(record, values, data)
        self.assertEqual(name, 'Panchroma PLA')
        add_copy(data, 'filament', name, values, '2.4.2')
        self.assertEqual(data['profiles'][0]['filament_vendor'], ['Polymaker'])
        self.assertEqual(values, before)
        self.assertEqual(copy_name(record, values, data), 'Panchroma PLA (2)')

    def test_alias_and_unknown_brand(self):
        data = new_set('Test')
        record = {'name': 'Long name @Printer', 'type': 'filament', 'settings': {'alias': 'PolyLite PETG'}}
        self.assertEqual(copy_name(record, {}, data), 'PolyLite PETG')
        record = {'name': 'Generic PLA @System', 'type': 'filament'}
        self.assertEqual(copy_name(record, {'filament_vendor': ['Generic']}, data), 'Generic PLA')
        record = {'name': 'Polymaker PLA @System', 'type': 'filament', 'vendor': 'Polymaker'}
        self.assertEqual(copy_name(record, {}, data), 'Polymaker PLA')
