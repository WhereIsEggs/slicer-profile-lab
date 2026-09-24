# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from profilelab.printer_templates import generic_printer, sync_nozzle_variant
from profilelab.profile_sets import new_set, add_copy, prepare_set
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_install import exportable_profiles


class PrinterTemplateTests(unittest.TestCase):
    def snapshot(self):
        return {'metadata': {'version': '2.4.2', 'revision': 'test'}, 'profiles': [
            dict(name='Base', type='machine', vendor='Custom', path='base.json', template=True,
                 settings={'retraction_length': ['0.8'], 'machine_start_gcode': 'TEMPLATE'}),
            dict(name='MyKlipper 0.4 nozzle', type='machine', vendor='Custom', path='leaf.json', template=False,
                 settings={'inherits': 'Base', 'printer_model': 'Generic Klipper Printer', 'printer_variant': '0.4',
                           'default_print_profile': 'Donor process', 'nozzle_diameter': ['0.4']})]}

    def test_template_values_and_shared_variant_identity_survive_export(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        entered = {'gcode_flavor': 'klipper', 'nozzle_diameter': ['0.4', '0.4'],
                   'machine_start_gcode': 'USER', 'extruder_offset': ['0x0', '10x0']}
        values, source = generic_printer('Gigabot 4 175', entered, snapshot)
        self.assertEqual(values['machine_start_gcode'], 'USER')
        self.assertEqual(values['retraction_length'], ['0.8'])
        self.assertNotIn('default_print_profile', values)
        self.assertEqual(source['chain'], ['Base', 'MyKlipper 0.4 nozzle'])
        self.assertEqual(snapshot, before)
        data = new_set('Variants')
        add_copy(data, 'machine', 'Gigabot 0.4', values, '2.4.2')
        add_copy(data, 'machine', 'Gigabot 0.8', values, '2.4.2')
        data['profiles'][1]['nozzle_diameter'] = ['0.8', '0.8']
        add_copy(data, 'filament', 'PLA', {}, '2.4.2')
        add_copy(data, 'process', 'Normal', {}, '2.4.2')
        data['printer_assignments'] = {name: {'filaments': ['PLA'], 'processes': ['Normal'],
            'defaults': {'filaments': ['PLA', 'PLA'], 'process': 'Normal'}} for name in ('Gigabot 0.4', 'Gigabot 0.8')}
        profiles = prepare_set(data)
        with TemporaryDirectory() as folder:
            package = Path(folder) / 'set.orca_bundle'
            export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], package)
            printers = [p for p in exportable_profiles(package) if p['type'] == 'machine']
        self.assertEqual({p['printer_model'] for p in printers}, {'Gigabot 4 175'})
        self.assertEqual({p['printer_variant'] for p in printers}, {'0.4', '0.8'})
        self.assertTrue(all(p['inherits'] == '' for p in printers))

    def test_missing_template_does_not_guess(self):
        with self.assertRaises(ValueError):
            generic_printer('Printer', {'gcode_flavor': 'klipper'}, None)

    def test_mixed_nozzles_not_mislabeled(self):
        profile = {'nozzle_diameter': ['0.4', '0.8']}
        sync_nozzle_variant(profile)
        self.assertNotIn('printer_variant', profile)

    @unittest.skipUnless(os.environ.get('PROFILELAB_PUBLIC_LIBRARY_TESTS') == '1', 'Cached library integration')
    def test_all_supported_firmware_templates(self):
        from profilelab.library import library_home, read_snapshot
        snapshot = read_snapshot(library_home())
        for flavor in ('klipper', 'marlin', 'marlin2', 'reprapfirmware'):
            values, source = generic_printer('Independent printer', {'gcode_flavor': flavor, 'nozzle_diameter': ['0.8']}, snapshot)
            self.assertEqual(values['gcode_flavor'], flavor)
            self.assertEqual(values['printer_model'], 'Independent printer')
            self.assertEqual(values['printer_variant'], '0.8')
            self.assertGreater(len(values), 8)
