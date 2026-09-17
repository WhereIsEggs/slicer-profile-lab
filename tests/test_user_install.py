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
            with self.assertRaisesRegex(ValueError, "already exists"):
                install_user_profiles(package, root / "user")

    def test_closed_guard_rolls_back_new_files(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.package(root)
            with patch("profilelab.user_install.require_orca_closed", side_effect=[None, None, RuntimeError("running")]):
                with self.assertRaises(RuntimeError):
                    install_user_profiles(package, root / "user")
            self.assertEqual(list((root / "user").rglob("*.json")), [])
