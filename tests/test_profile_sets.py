from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from profilelab.profile_sets import new_set, add_copy, prepare_set, save_set, load_sets, review_set
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_install import exportable_profiles


class ProfileSetTests(unittest.TestCase):
    def test_source_chain_is_frozen_project_metadata_not_exported_settings(self):
        data = self.fixture()
        source = dict(chain=['Root', 'Parent', 'Leaf'], revision='pinned')
        add_copy(data, 'process', 'Source copy', {}, '2.4.2', source=source)
        source['chain'].clear()
        self.assertEqual(data['sources']['process/Source copy']['chain'], ['Root', 'Parent', 'Leaf'])
        self.assertNotIn('source', data['profiles'][-1])
        self.assertNotIn('sources', data['profiles'][-1])
        self.assertEqual(data['profiles'][-1]['inherits'], '')

    def fixture(self):
        data = new_set('Workshop')
        add_copy(data, 'filament', 'PLA', {'filament_diameter': ['1.75']}, '2.4.2')
        add_copy(data, 'machine', 'Printer', {'nozzle_diameter': ['0.4', '0.4']}, '2.4.2')
        add_copy(data, 'filament', 'PETG', {}, '2.4.2')
        add_copy(data, 'process', 'Fast', {}, '2.4.2')
        add_copy(data, 'process', 'Fine', {}, '2.4.2')
        data['defaults'] = dict(filaments=['PLA', 'PETG'], process='Fine')
        return data

    def test_links_and_independent_copies(self):
        data = self.fixture()
        before = deepcopy(data)
        profiles = prepare_set(data)
        self.assertEqual(data, before)
        self.assertEqual(len(profiles), 5)
        self.assertEqual(profiles[1]['default_filament_profile'], ['PLA', 'PETG'])
        for p in profiles:
            if p['type'] != 'machine':
                self.assertEqual(p['compatible_printers'], ['Printer'])
            if p['type'] == 'process':
                self.assertNotIn('compatible_prints', p)

    def test_incomplete_and_stale_defaults_block_packaging(self):
        with self.assertRaises(ValueError):
            prepare_set(new_set('Empty'))
        data = self.fixture()
        data['defaults']['filaments'] = ['Missing', 'PLA']
        with self.assertRaises(ValueError):
            prepare_set(data)

    def test_save_reopen_and_package_all_members(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = self.fixture()
            save_set(root, data)
            self.assertEqual(load_sets(root), [data])
            profiles = prepare_set(data)
            destination = root / 'set.orca_bundle'
            export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], destination)
            self.assertEqual(len(exportable_profiles(destination)), 5)

    def test_second_printer_preserves_legacy_assignments(self):
        data = self.fixture()
        add_copy(data, 'machine', 'Second', {'nozzle_diameter': ['0.8']}, '2.4.2')
        self.assertEqual(data['printer_assignments']['Printer']['defaults']['process'], 'Fine')
        with self.assertRaisesRegex(ValueError, 'Second'):
            prepare_set(data)

    def test_review_warns_without_changing_mixed_set(self):
        data = self.fixture()
        data['profiles'][2]['filament_diameter'] = ['2.85']
        data['profiles'][3]['layer_height'] = '0.8'
        before = deepcopy(data)
        warnings = review_set(data)
        self.assertTrue(any('mixes filament diameters' in w for w in warnings))
        self.assertTrue(any('layer height exceeds' in w for w in warnings))
        self.assertEqual(data, before)
        self.assertEqual(len(prepare_set(data)), 5)

    def test_review_handles_invalid_numbers(self):
        data = self.fixture()
        data['profiles'][1]['nozzle_diameter'] = ['NaN']
        self.assertTrue(any('nozzle diameters are missing or invalid' in w for w in review_set(data)))
