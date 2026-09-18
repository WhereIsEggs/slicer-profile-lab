# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import unittest
from profilelab.library_choices import selectable_library_records
from profilelab.resolver import ProfileResolver


class LibraryChoiceTests(unittest.TestCase):
    def test_keeps_legacy_entries_without_changing_inheritance(self):
        def record(name, template=False, parent=''):
            return dict(name=name, vendor='re3D', type='filament', template=template,
                        path=name + '.json', settings={'inherits': parent, 'filament_diameter': ['2.85']})
        root = record('fdm_filament_pc', True)
        base = record('re3D PC', parent=root['name'])
        variant = record('re3D PC @0.4 nozzle', parent=root['name'])
        records = [root, base, variant]
        before = deepcopy(records)
        self.assertEqual(selectable_library_records(records), [base, variant])
        self.assertEqual(ProfileResolver(records).chain(variant), [variant, root])
        self.assertEqual(records, before)

    def test_keeps_genuine_unsuffixed_profiles_and_missing_variant_fallback(self):
        records = [dict(name='Generic PLA', vendor='Other', type='filament'),
                   dict(name='Generic PLA @0.4 nozzle', vendor='Other', type='filament'),
                   dict(name='re3D PC', vendor='re3D', type='filament')]
        self.assertEqual(selectable_library_records(records), records)
