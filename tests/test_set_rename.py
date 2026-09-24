# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from profilelab.profile_sets import new_set, add_copy, rename_profile, prepare_set


class SetRenameTests(unittest.TestCase):
    def test_rename_updates_links_and_defaults(self):
        data = new_set('Test')
        add_copy(data, 'machine', 'Printer', {'nozzle_diameter': ['0.4']}, '2.4.2')
        add_copy(data, 'filament', 'PLA', {}, '2.4.2')
        add_copy(data, 'process', 'Fine', {}, '2.4.2')
        data['defaults'] = {'filaments': ['PLA'], 'process': 'Fine'}
        rename_profile(data, 0, 'Printer 0.4')
        rename_profile(data, 1, 'New PLA')
        rename_profile(data, 2, 'New Fine')
        profiles = prepare_set(data)
        printer = profiles[0]
        self.assertEqual(printer['default_filament_profile'], ['New PLA'])
        self.assertEqual(printer['default_print_profile'], 'New Fine')
        self.assertEqual(profiles[1]['compatible_printers'], ['Printer 0.4'])
