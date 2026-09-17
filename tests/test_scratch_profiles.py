# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import os
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from profilelab.scratch_profiles import scratch_values


def scratch_fixture():
    return {
        'machine': dict(firmware='klipper', width='200', depth='200', height='200', extruders='2', nozzle_0='0.4', nozzle_1='0.6', offset_x='25', offset_y='0', start_gcode='; fictional test only', end_gcode='; fictional test only'),
        'filament': dict(material='PLA', diameter='1.75', temperature='200', bed_temperature='55', flow_ratio='1'),
        'process': dict(layer_height='0.2', first_layer_height='0.2', walls='2', infill='15', outer_speed='30', inner_speed='40'),
    }


class ScratchTests(unittest.TestCase):
    def test_core_values_are_explicit_and_correctly_typed(self):
        values = scratch_fixture()
        printer = scratch_values('machine', values['machine'])
        self.assertEqual(printer['nozzle_diameter'], ['0.4', '0.6'])
        self.assertEqual(printer['extruder_offset'], ['0x0', '25x0'])
        self.assertEqual(printer['printable_area'], ['0x0', '200x0', '200x200', '0x200'])
        self.assertEqual(scratch_values('filament', values['filament'])['nozzle_temperature'], ['200'])
        self.assertEqual(scratch_values('process', values['process'])['sparse_infill_density'], '15%')

    def test_missing_and_nonfinite_values_rejected(self):
        for kind in scratch_fixture():
            with self.assertRaises(ValueError):
                scratch_values(kind, {})
        values = scratch_fixture()['machine']
        values['nozzle_0'] = 'NaN'
        with self.assertRaises(ValueError):
            scratch_values('machine', values)

    def test_single_extruder_does_not_require_right_hand_fields(self):
        values = scratch_fixture()['machine']
        values.update(extruders='1', nozzle_1='', offset_x='', offset_y='')
        self.assertEqual(scratch_values('machine', values)['nozzle_diameter'], ['0.4'])

    def test_missing_gcode_and_fractional_wall_count_rejected(self):
        values = scratch_fixture()
        values['machine']['start_gcode'] = ''
        values['process']['walls'] = '1.5'
        for kind in ('machine', 'process'):
            with self.assertRaises(ValueError):
                scratch_values(kind, values[kind])

    def test_dialog_rejects_empty_then_accepts_explicit_process(self):
        from PySide6.QtWidgets import QApplication, QDialog
        from profilelab.scratch_dialog import ScratchDialog
        app = QApplication.instance() or QApplication([])
        dialog = ScratchDialog('process')
        with patch('profilelab.scratch_dialog.QMessageBox.warning') as warning:
            dialog.submit()
            warning.assert_called_once()
        dialog.fields['name'].setText('Fictional process')
        for key, value in scratch_fixture()['process'].items():
            dialog.fields[key].setText(value)
        dialog.submit()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        dialog.close()
        app.processEvents()
