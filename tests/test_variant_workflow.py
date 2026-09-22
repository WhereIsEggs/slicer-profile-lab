# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile
from profilelab.profile_sets import new_set, add_copy, prepare_set, save_set, load_sets, set_readiness, review_set
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_install import install_user_profiles
from profilelab.user_sharing import share_prepared_package
from profilelab.validation import validate_folder


def fixture():
    data = new_set('Two nozzle workshop')
    for nozzle, height in [('0.4', '0.2'), ('0.8', '0.4')]:
        add_copy(data, 'machine', 'Workshop ' + nozzle, dict(printer_model='Workshop', printer_variant=nozzle,
                 nozzle_diameter=[nozzle, nozzle]), '2.4.2')
        for material in ('PLA', 'PETG'):
            add_copy(data, 'filament', material + ' ' + nozzle,
                     dict(filament_diameter=['2.85'], filament_type=[material], filament_id='family-' + material), '2.4.2')
        add_copy(data, 'process', 'Standard ' + nozzle, dict(layer_height=height), '2.4.2')
    data['printer_assignments'] = {
        'Workshop ' + nozzle: dict(filaments=['PLA ' + nozzle, 'PETG ' + nozzle], processes=['Standard ' + nozzle],
                                  defaults=dict(filaments=['PLA ' + nozzle, 'PETG ' + nozzle], process='Standard ' + nozzle))
        for nozzle in ('0.4', '0.8')}
    return data


class VariantWorkflowTests(unittest.TestCase):
    def test_save_package_share_install_preserves_exact_variant_links(self):
        data = fixture()
        before = deepcopy(data)
        self.assertEqual(set_readiness(data), [])
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            save_set(root / 'sets', data)
            profiles = prepare_set(load_sets(root / 'sets')[0])
            package = root / 'workshop.orca_bundle'
            export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], package)
            with zipfile.ZipFile(share_prepared_package(package)) as archive:
                shared = {p['name']: p for p in [json.loads(archive.read(n)) for n in archive.namelist()]}
            with patch('profilelab.user_install.require_orca_closed'):
                installed_paths = install_user_profiles(package, root / 'isolated-user')
            installed = {p['name']: p for p in [json.loads(path.read_text()) for path in installed_paths]}
            self.assertEqual(shared, installed)
            self.assertEqual(len(shared), 8)
            self.assertTrue(validate_folder(root / 'isolated-user').is_valid)
            for nozzle in ('0.4', '0.8'):
                printer = shared['Workshop ' + nozzle]
                self.assertEqual(printer['printer_model'], 'Workshop')
                self.assertEqual(printer['printer_variant'], nozzle)
                self.assertEqual(printer['nozzle_diameter'], [nozzle, nozzle])
                self.assertEqual(printer['default_filament_profile'], ['PLA ' + nozzle, 'PETG ' + nozzle])
                self.assertEqual(printer['default_print_profile'], 'Standard ' + nozzle)
                for name in ['PLA ' + nozzle, 'PETG ' + nozzle, 'Standard ' + nozzle]:
                    self.assertEqual(shared[name]['compatible_printers'], ['Workshop ' + nozzle])
                    self.assertEqual(shared[name]['inherits'], '')
                self.assertEqual(shared['PLA ' + nozzle]['filament_id'], 'family-PLA')
            self.assertEqual(data, before)

    def test_readiness_lists_all_gaps_and_clears_after_repair(self):
        data = fixture()
        before = deepcopy(data)
        data['printer_assignments']['Workshop 0.8']['defaults'] = {}
        add_copy(data, 'process', 'Unassigned', {'layer_height': '0.2'}, '2.4.2')
        gaps = set_readiness(data)
        self.assertTrue(any('E0' in g for g in gaps))
        self.assertTrue(any('E1' in g for g in gaps))
        self.assertTrue(any('default process' in g for g in gaps))
        self.assertTrue(any('Unassigned' in g for g in gaps))
        self.assertEqual(set_readiness(before), [])

    def test_nozzle_variant_mismatch_is_warning_not_silent_rewrite(self):
        data = fixture()
        data['profiles'][0]['printer_variant'] = '0.8'
        before = deepcopy(data)
        self.assertTrue(any('does not match all nozzle' in w for w in review_set(data)))
        self.assertEqual(data, before)
