import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from profilelab.orca_bundle import export_orca_bundle
from profilelab.sharing import collect_profiles
from profilelab.bundle_contract import scope_profiles


class OrcaBundleTests(unittest.TestCase):
    def test_conflicting_type_identity_blocks_export(self):
        profiles = self.profiles()
        profiles[2]["printer_settings_id"] = "Process"
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "bad.orca_bundle"
            with self.assertRaisesRegex(ValueError, "another profile type"):
                export_orca_bundle(profiles, [("machine", "A Child")], destination)
            self.assertFalse(destination.exists())

    def profiles(self):
        return [
            {"type": "machine", "name": "A Child", "inherits": "Z Parent", "version": "2.4.2.0", "printer_settings_id": "A Child", "default_print_profile": "Process", "default_filament_profile": ["PLA"]},
            {"type": "machine", "name": "Z Parent", "version": "2.4.2.0", "printer_settings_id": "Z Parent", "nozzle_diameter": ["0.4"]},
            {"type": "process", "name": "Process", "version": "2.4.2.0", "print_settings_id": "Process", "compatible_printers": ["A Child"], "layer_height": "0.2"},
            {"type": "filament", "name": "PLA", "version": "2.4.2.0", "filament_settings_id": ["PLA"], "compatible_printers": ["A Child"], "filament_type": ["PLA"]},
        ]

    def test_reopen_archive_without_source_and_check_import_order(self):
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "fictional.orca_bundle"
            profiles = self.profiles()
            export_orca_bundle(profiles, [("machine", "A Child")], destination)
            profiles.clear()
            with zipfile.ZipFile(destination) as archive:
                manifest = json.loads(archive.read("bundle_structure.json"))
                names = [n for n in archive.namelist() if n != "bundle_structure.json"]
                self.assertEqual(set(names), set(sum((manifest[k] for k in ("printer_config", "filament_config", "process_config")), [])))
                loaded = [json.loads(archive.read(n)) for n in names]
            self.assertEqual(manifest["name"], "A Child")
            self.assertEqual(manifest["bundle_id"], "A Child")
            self.assertTrue(next(p for p in loaded if p["name"] == "A Child")["inherits"].startswith("_local/" + manifest["id"] + "/"))
            loaded = scope_profiles(loaded, manifest["id"], unqualify=True)
            seen = set()
            for profile in loaded:
                if profile.get("inherits"):
                    self.assertIn((profile["type"], profile["inherits"]), seen)
                seen.add((profile["type"], profile["name"]))
            self.assertEqual(len(collect_profiles(loaded, [("machine", "A Child")])), 4)
            self.assertEqual(next(p for p in loaded if p["name"] == "Process")["layer_height"], "0.2")
            with self.assertRaises(FileExistsError):
                export_orca_bundle(self.profiles(), [("machine", "A Child")], destination)

    def test_missing_import_identity_creates_no_archive(self):
        profiles = self.profiles()
        del profiles[0]["printer_settings_id"]
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "invalid.orca_bundle"
            with self.assertRaisesRegex(ValueError, "printer_settings_id"):
                export_orca_bundle(profiles, [("machine", "A Child")], destination)
            self.assertFalse(destination.exists())
