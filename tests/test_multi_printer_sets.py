import os
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from profilelab.profile_sets import new_set, add_copy, prepare_set, assignment_map, save_set, load_sets
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_install import exportable_profiles
from profilelab.user_sharing import share_prepared_package
import zipfile
import json


def multi_fixture():
    data = new_set('Family')
    for name, nozzle in [('Small 0.4', '0.4'), ('XL 0.8', '0.8')]:
        add_copy(data, 'machine', name, {'nozzle_diameter': [nozzle]}, '2.4.2')
    for name in ('PLA', 'PETG'):
        add_copy(data, 'filament', name, {'filament_diameter': ['1.75']}, '2.4.2')
    for name, layer in [('Fine 0.4', '0.2'), ('Coarse 0.8', '0.4')]:
        add_copy(data, 'process', name, {'layer_height': layer}, '2.4.2')
    data['printer_assignments'] = {
        'Small 0.4': dict(filaments=['PLA'], processes=['Fine 0.4'], defaults=dict(filaments=['PLA'], process='Fine 0.4')),
        'XL 0.8': dict(filaments=['PLA', 'PETG'], processes=['Coarse 0.8'], defaults=dict(filaments=['PETG'], process='Coarse 0.8')),
    }
    return data


class MultiPrinterTests(unittest.TestCase):
    def test_explicit_links_do_not_leak_across_nozzles(self):
        data = multi_fixture()
        before = deepcopy(data)
        output = {p['name']: p for p in prepare_set(data)}
        self.assertEqual(output['PLA']['compatible_printers'], ['Small 0.4', 'XL 0.8'])
        self.assertEqual(output['Fine 0.4']['compatible_printers'], ['Small 0.4'])
        self.assertEqual(output['Coarse 0.8']['compatible_printers'], ['XL 0.8'])
        self.assertEqual(data, before)

    def test_missing_and_wrong_default_assignments_block(self):
        for change in ('missing', 'wrong_default', 'orphan'):
            data = multi_fixture()
            if change == 'missing':
                del data['printer_assignments']['XL 0.8']
            elif change == 'wrong_default':
                data['printer_assignments']['Small 0.4']['defaults']['process'] = 'Coarse 0.8'
            else:
                add_copy(data, 'filament', 'Unassigned', {}, '2.4.2')
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_set(data)

    def test_all_profiles_survive_save_and_share(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = multi_fixture()
            save_set(root, data)
            self.assertEqual(load_sets(root), [data])
            profiles = prepare_set(data)
            package = root / 'family.orca_bundle'
            export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], package)
            self.assertEqual(len(exportable_profiles(package)), 6)
            with zipfile.ZipFile(share_prepared_package(package)) as archive:
                saved = [json.loads(archive.read(n)) for n in archive.namelist()]
                self.assertEqual(len(saved), 6)
                self.assertEqual(next(p for p in saved if p['name'] == 'Fine 0.4')['compatible_printers'], ['Small 0.4'])

    def test_wizard_filters_and_duplicates_selected_category(self):
        from PySide6.QtWidgets import QApplication
        from profilelab.profile_sets_view import ProfileSetsView
        app = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as temporary:
            view = ProfileSetsView(None, root=Path(temporary))
            view.data = multi_fixture()
            view.render()
            self.assertEqual(view.members.count(), 2)
            view.steps.setCurrentIndex(2)
            self.assertEqual(view.data['profiles'][view.member_indices[0]]['type'], 'process')
            view.members.setCurrentRow(0)
            original = view.data['profiles'][view.member_indices[0]]
            source = dict(chain=['Root', 'Original'], revision='pinned')
            view.data['sources'] = {'process/' + original['name']: source}
            with patch('profilelab.profile_sets_view.QInputDialog.getText', return_value=('New process', True)):
                view.duplicate()
            self.assertEqual(view.data['profiles'][-1]['type'], 'process')
            self.assertEqual(view.data['sources']['process/New process'], source)
            self.assertIsNot(view.data['sources']['process/New process'], source)
            self.assertEqual(view.members.count(), 3)
            view.close()
            app.processEvents()

    def test_assignment_dialog_limits_defaults_to_checked_choices(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from profilelab.set_assignments import AssignmentsDialog
        app = QApplication.instance() or QApplication([])
        dialog = AssignmentsDialog(multi_fixture())
        page = dialog.pages[0]
        self.assertEqual(page['process'].findData('Coarse 0.8'), -1)
        page['lists']['filaments'].item(0).setCheckState(Qt.CheckState.Unchecked)
        self.assertEqual(page['slots'][0].currentData(), '')
        dialog.save()
        self.assertEqual(dialog.assignments['Small 0.4']['filaments'], [])
        dialog.close()
        app.processEvents()
