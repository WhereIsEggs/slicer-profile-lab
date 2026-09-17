# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
import zipfile

from profilelab.drafts import delete_draft
from profilelab.user_sharing import write_user_zip, repair_stock_export


class UserSharingTests(unittest.TestCase):
    def test_repair_keeps_all_profiles_and_removes_bundle_routing(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.orca_printer'
            profiles = [
                {'name': 'Printer', 'printer_settings_id': 'Printer', 'default_filament_profile': ['PLA'], 'default_print_profile': 'Process'},
                {'name': 'PLA', 'filament_settings_id': ['PLA'], 'compatible_printers': ['Printer']},
                {'name': 'Process', 'print_settings_id': 'Process', 'compatible_printers': ['Printer']},
            ]
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('bundle_structure.json', json.dumps(dict(zip(['printer_config', 'filament_config', 'process_config'], [['0.json'], ['1.json'], ['2.json']]))))
                for i, profile in enumerate(profiles):
                    archive.writestr(f'{i}.json', json.dumps(profile))
            original = source.read_bytes()
            output = repair_stock_export(source, root / 'fixed.zip')
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn('bundle_structure.json', archive.namelist())
                saved = [json.loads(archive.read(n)) for n in archive.namelist()]
                self.assertEqual(len(saved), 3)
                self.assertEqual(saved[1]['compatible_printers'], ['Printer'])
            self.assertEqual(original, source.read_bytes())
            with self.assertRaises(FileExistsError):
                repair_stock_export(source, output)

    def test_missing_links_and_external_parents_rejected(self):
        with TemporaryDirectory() as temporary:
            for fields in ({'inherits': 'Absent'}, {'compatible_printers': ['Absent']}):
                with self.assertRaises(ValueError):
                    write_user_zip([{'name': 'PLA', 'type': 'filament', **fields}], Path(temporary) / 'bad.zip')

    def test_delete_moves_only_selected_unchanged_draft(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = {'id': str(uuid4()), 'name': 'Test'}
            source = root / (draft['id'] + '.json')
            source.write_text(json.dumps(draft))
            other = root / 'other.json'
            other.write_text('{}')
            with self.assertRaises(ValueError):
                delete_draft(root, {**draft, 'name': 'Old'})
            backup = delete_draft(root, draft)
            self.assertFalse(source.exists())
            self.assertEqual(json.loads(backup.read_text()), draft)
            self.assertEqual(other.read_text(), '{}')
