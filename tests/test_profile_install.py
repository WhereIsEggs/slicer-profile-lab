# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import hashlib
import unittest
import zipfile

from profilelab.orca_bundle import export_orca_bundle
from profilelab.profile_install import install_bundle


class InstallationTests(unittest.TestCase):
    def test_existing_loose_user_profile_is_never_migrated(self):
        with TemporaryDirectory() as temporary, patch("profilelab.profile_install.require_orca_closed"):
            root = Path(temporary)
            existing = root / "user" / "machine" / "Fictional Printer.json"
            existing.parent.mkdir(parents=True)
            existing.write_text('{"name":"Fictional Printer","user_owned":true}')
            original = existing.read_bytes()
            installed = install_bundle(self.package(root), root / "user")
            self.assertEqual(existing.read_bytes(), original)
            self.assertTrue(all("_local" in p.parts for p in installed))

    def test_archive_ambiguity_blocks_installation_before_any_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.package(root)
            with zipfile.ZipFile(package) as archive:
                original = {n: archive.read(n) for n in archive.namelist()}
            first = next(n for n in original if n != "bundle_structure.json")
            mutations = [
                {first: b'{"name":"A","name":"B"}'},
                {"../escape.json": b'{}'},
                {"unlisted.json": b'{}'},
                {"bundle_structure.json": b'{"bundle_type":"printer config bundle"}'},
            ]
            for number, mutation in enumerate(mutations):
                modified = root / f"bad{number}.orca_bundle"
                with zipfile.ZipFile(modified, "w") as archive:
                    for name, payload in (original | mutation).items():
                        archive.writestr(name, payload)
                with self.subTest(number=number), self.assertRaises(ValueError):
                    install_bundle(modified, root / "user")
                self.assertFalse((root / "user").exists())

    def package(self, root):
        profiles = [{"type": kind, "name": name, "version": "2.4.2.0", identity: value} for kind, name, identity, value in [
            ("machine", "Fictional Printer", "printer_settings_id", "Fictional Printer"),
            ("process", "Fictional Process", "print_settings_id", "Fictional Process"),
            ("filament", "Fictional PLA", "filament_settings_id", ["Fictional PLA"])]]
        destination = root / "example.orca_bundle"
        export_orca_bundle(profiles, [(p["type"], p["name"]) for p in profiles], destination)
        return destination

    def test_installs_all_three_folders_and_refuses_replacement(self):
        with TemporaryDirectory() as temporary, patch("profilelab.profile_install.require_orca_closed"):
            root = Path(temporary)
            package = self.package(root)
            installed = install_bundle(package, root / "user")
            metadata = json.loads((installed[0].parent.parent / "bundle_metadata.json").read_text())
            self.assertEqual(metadata["name"], "Fictional Printer")
            self.assertEqual(installed[0].parent.parent.parent.name, "_local")
            for path in installed:
                self.assertEqual(path.stem, json.loads(path.read_text())["name"])
            self.assertEqual({p.parent.name for p in installed}, {"machine", "process", "filament"})
            before = {p: p.read_bytes() for p in installed}
            self.assertEqual(install_bundle(package, root / "user"), [])
            self.assertEqual(before, {p: p.read_bytes() for p in installed})
            changed = json.loads(installed[0].read_text())
            changed["description"] = "User edit"
            installed[0].write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "already exists"):
                install_bundle(package, root / "user")

    def test_does_not_repair_or_replace_changed_bundle_files(self):
        with TemporaryDirectory() as temporary, patch("profilelab.profile_install.require_orca_closed"):
            root = Path(temporary)
            package = self.package(root)
            paths = install_bundle(package, root / "user")
            old_paths = []
            for path in paths:
                profile = json.loads(path.read_text())
                digest = hashlib.sha256((profile["type"] + "\0" + profile["name"]).encode()).hexdigest()[:24]
                old = path.with_name(f"profilelab_{digest}.json")
                path.rename(old)
                old_paths.append(old)
            with self.assertRaisesRegex(ValueError, "already exists"):
                install_bundle(package, root / "user")
            self.assertTrue(all(not p.exists() for p in paths))
            self.assertTrue(all(p.exists() for p in old_paths))

    def test_running_orca_prevents_writes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.package(root)
            with patch("profilelab.profile_install.require_orca_closed", side_effect=RuntimeError("Close Orca")):
                with self.assertRaises(RuntimeError):
                    install_bundle(package, root / "user")
            self.assertFalse((root / "user").exists())

    def test_failure_mid_install_rolls_back_created_profiles(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = self.package(root)
            with patch("profilelab.profile_install.require_orca_closed", side_effect=[None, None, RuntimeError("Orca opened")]):
                with self.assertRaises(RuntimeError):
                    install_bundle(package, root / "user")
            self.assertEqual(list((root / "user").rglob("*.json")), [])
