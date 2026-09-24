# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from profilelab.user_install import exportable_profiles, install_user_profiles
from profilelab.orca_bundle import export_orca_bundle


class UserInstallTests(unittest.TestCase):
    def package(self, root):
        profiles = [
            {"type": "machine", "name": "Base", "version": "2.4.2.0", "instantiation": "false", "printer_settings_id": "Base", "nozzle_diameter": ["0.4"], "setting_id": "system"},
            {"type": "machine", "name": "Workshop", "version": "2.4.2.0", "inherits": "Base", "printer_settings_id": "Workshop", "default_filament_profile": ["PLA"]},
            {"type": "filament", "name": "PLA", "version": "2.4.2.0", "filament_settings_id": ["PLA"], "filament_id": "OFexample", "compatible_printers": ["Workshop"]},
        ]
        path = root / "test.orca_bundle"
        export_orca_bundle(profiles, [("machine", "Workshop")], path)
        return path

    def test_flattened_copies_keep_values_and_bare_links(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.package(root)
            original = package.read_bytes()
            profiles = exportable_profiles(package)
            self.assertEqual(len(profiles), 2)
            printer = next(p for p in profiles if p["type"] == "machine")
            self.assertEqual(printer["inherits"], "")
            self.assertEqual(printer["nozzle_diameter"], ["0.4"])
            self.assertEqual(printer["default_filament_profile"], ["PLA"])
            self.assertNotIn("setting_id", printer)
            self.assertEqual(package.read_bytes(), original)

    def test_no_bundle_prefix_and_no_overwrite(self):
        with TemporaryDirectory() as temporary, patch("profilelab.user_install.require_orca_closed"):
            root = Path(temporary)
            package = self.package(root)
            installed = install_user_profiles(package, root / "user")
            self.assertEqual(installed[-1].parent.name, "machine")
            self.assertFalse((root / "user" / "_local").exists())
            self.assertEqual(install_user_profiles(package, root / "user"), [])

    def test_updates_need_approval_and_keep_backup(self):
        import json
        from profilelab.user_install import ProfileConflicts
        with TemporaryDirectory() as temporary, patch('profilelab.user_install.require_orca_closed'):
            root = Path(temporary)
            package = self.package(root)
            installed = install_user_profiles(package, root / 'user')
            target = installed[-1]
            content = json.loads(target.read_text())
            content['printer_notes'] = 'Existing edits'
            original = json.dumps(content).encode()
            target.write_bytes(original)
            with self.assertRaises(ProfileConflicts) as caught:
                install_user_profiles(package, root / 'user')
            self.assertEqual(target.read_bytes(), original)
            approval = caught.exception.files
            target.write_bytes(original + b' ')
            with self.assertRaises(ProfileConflicts):
                install_user_profiles(package, root / 'user', approved_updates=approval)
            target.write_bytes(original)
            self.assertEqual(install_user_profiles(package, root / 'user', approved_updates=approval), [target])
            backups = list((root / 'user/profilelab-backups').rglob('*.json'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)

    def test_expanded_package_adds_variant_and_skips_original(self):
        from copy import deepcopy
        with TemporaryDirectory() as temporary, patch('profilelab.user_install.require_orca_closed'):
            root = Path(temporary)
            package = self.package(root)
            installed = install_user_profiles(package, root / 'user')
            originals = {p: p.read_bytes() for p in installed}
            profiles = exportable_profiles(package)
            variant = deepcopy(next(p for p in profiles if p['type'] == 'machine'))
            variant.update(name='Printer 0.8', nozzle_diameter=['0.8'])
            with patch('profilelab.user_install.exportable_profiles', return_value=profiles + [variant]):
                added = install_user_profiles(package, root / 'user')
            self.assertEqual([p.name for p in added], ['Printer 0.8.json'])
            self.assertTrue(all(p.read_bytes() == content for p, content in originals.items()))

    def test_closed_guard_rolls_back_new_files(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.package(root)
            with patch("profilelab.user_install.require_orca_closed", side_effect=[None, None, RuntimeError("running")]):
                with self.assertRaises(RuntimeError):
                    install_user_profiles(package, root / "user")
            self.assertEqual(list((root / "user").rglob("*.json")), [])
