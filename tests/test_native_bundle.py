# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Opt-in native smoke test. Uses only fictional profiles in temporary folders."""

import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_orca_bundle
from profilelab.engine_validator import validator_path
from profilelab.orca_bundle import export_orca_bundle
from profilelab.profile_install import install_bundle


@unittest.skipUnless(os.environ.get("PROFILELAB_NATIVE_TESTS") == "1", "Opt-in installed Orca engine test")
class NativeBundleTests(unittest.TestCase):
    def test_comparison_family_loads_all_eight_profiles(self):
        from prepare_variant_comparison import comparison_set
        from profilelab.profile_sets import prepare_set
        self.assert_profiles_load(prepare_set(comparison_set()), ('machine', 'Lab Standard 0.4'), ordinary=True, select_all=True)

    def test_multi_printer_set_loads_every_member(self):
        from test_multi_printer_sets import multi_fixture
        from profilelab.profile_sets import prepare_set
        profiles = prepare_set(multi_fixture())
        self.assert_profiles_load(profiles, ('machine', 'Small 0.4'), ordinary=True, select_all=True)
    def test_scratch_set_loads_in_native_orca(self):
        from test_scratch_profiles import scratch_fixture
        from profilelab.scratch_profiles import scratch_values
        from profilelab.profile_sets import new_set, add_copy, prepare_set
        data = new_set('Scratch native test')
        for kind, values in scratch_fixture().items():
            add_copy(data, kind, 'Fictional ' + kind, scratch_values(kind, values), '2.4.2')
        data['defaults'] = dict(filaments=['Fictional filament', 'Fictional filament'], process='Fictional process')
        self.assert_profiles_load(prepare_set(data), ('machine', 'Fictional machine'), ordinary=True)

    @unittest.skipUnless(os.environ.get("PROFILELAB_PUBLIC_LIBRARY_TESTS") == "1", "Opt-in cached public library test")
    def test_real_prusa_draft_package_loads_in_orca(self):
        from profilelab.library import read_snapshot, library_home
        from profilelab.drafts import create_draft
        from profilelab.draft_package import prepare_draft_profiles
        from profilelab.resolver import ProfileResolver
        snapshot = read_snapshot(library_home())
        self.assertIsNotNone(snapshot, "Download the public system library first")
        printer = next(p for p in snapshot["profiles"] if p["vendor"] == "Prusa" and p["name"] == "Prusa MK3S 0.4 nozzle")
        with TemporaryDirectory() as temporary:
            draft = create_draft(Path(temporary), "Profile Lab Workshop MK3S", printer, snapshot["metadata"], ProfileResolver(snapshot["profiles"]))
            profiles, selected = prepare_draft_profiles(draft["id"], [draft], snapshot)
        leaves = [p for p in profiles if p.get("instantiation") != "false"]
        self.assertEqual({p["type"] for p in leaves}, {"machine", "filament", "process"})
        self.assert_profiles_load(profiles, selected)
        self.assert_profiles_load(profiles, selected, ordinary=True)

    def test_native_engine_loads_every_profile_with_two_parent_levels(self):
        fixture = test_orca_bundle.OrcaBundleTests().profiles()
        fixture[1]["inherits"] = "ZZ Root"
        fixture.append({"type": "machine", "name": "ZZ Root", "version": "2.4.2.0", "printer_settings_id": "ZZ Root", "nozzle_diameter": ["0.4"]})
        self.assert_profiles_load(fixture, ("machine", "A Child"))

    def test_demo_package_loads_all_ten_profiles_in_native_orca(self):
        from profilelab.demo import demo_snapshot
        from profilelab.drafts import create_draft, save_override
        from profilelab.draft_package import prepare_draft_profiles
        from profilelab.resolver import ProfileResolver
        snapshot = demo_snapshot()
        printer = next(p for p in snapshot["profiles"] if p["name"] == "Demo Dual Printer 0.4 nozzle")
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = create_draft(root, "Workshop Printer", printer, snapshot["metadata"], ProfileResolver(snapshot["profiles"]))
            draft = save_override(root, draft, "retraction_length", ["1.2", "1.0"])
            profiles, selected = prepare_draft_profiles(draft["id"], [draft], snapshot)
        self.assertEqual(len(profiles), 10)
        self.assert_profiles_load(profiles, selected)

    def assert_profiles_load(self, fixture, selected, ordinary=False, select_all=False):
        with TemporaryDirectory(prefix="profilelab-native-regression-") as temporary:
            root = Path(temporary)
            tree = root / "resources" / "profiles"
            (tree / "OrcaFilamentLibrary").mkdir(parents=True)
            # An empty vendor prevents unrelated public-library findings from
            # concealing whether the user's bundle was actually loaded.
            (tree / "OrcaFilamentLibrary.json").write_text(json.dumps({
                "name": "OrcaFilamentLibrary", "version": "2.4.2.0",
                "filament_list": [], "process_list": [], "machine_list": [], "machine_model_list": [],
            }))
            package = root / "fictional.orca_bundle"
            metadata = export_orca_bundle(fixture, [(p['type'], p['name']) for p in fixture] if select_all else [selected], package)
            # Suppress the real process guard only for this isolated test target.
            if ordinary:
                from profilelab.user_install import install_user_profiles, exportable_profiles
                fixture = exportable_profiles(package)
                with patch("profilelab.user_install.require_orca_closed"):
                    installed = install_user_profiles(package, tree / "user" / "default")
            else:
                with patch("profilelab.profile_install.require_orca_closed"):
                    installed = install_bundle(package, tree / "user" / "default")
            self.assertEqual(len(installed), len(fixture))
            executable = Path(os.environ.get('PROFILELAB_NATIVE_VALIDATOR') or validator_path())
            checked = subprocess.run([str(executable), "--path", str(tree), "--log_level", "3"],
                                     cwd=executable.parent, capture_output=True, text=True,
                                     encoding="utf-8", errors="replace", timeout=60, check=False)
            output = checked.stdout + checked.stderr
            self.assertEqual(checked.returncode, 0, output)
            for profile in fixture:
                expected = "preset name is:" + ("" if ordinary else "_local/" + metadata["id"] + "/") + profile["name"]
                self.assertIn(expected, output, "Orca skipped a profile: " + profile["name"])
