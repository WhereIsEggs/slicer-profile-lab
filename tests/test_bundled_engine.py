# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from profilelab.engine_validator import validator_path, bundled_engine_problem, run_orca_engine_for_user_profiles
from profilelab.validation import validate_user_folder


class BundledEngineTests(unittest.TestCase):
    def test_frozen_path_does_not_use_old_nightly_cache(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', 'bundle', create=True), patch.dict(os.environ, {'PROFILELAB_ORCA_VALIDATOR': ''}):
            self.assertEqual(validator_path(), Path('bundle/orca-engine/OrcaSlicer_profile_validator.exe'))

    def test_missing_or_corrupt_bundled_resources_fail_closed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine = root / 'orca-engine'
            (engine / 'resources/profiles/Vendor').mkdir(parents=True)
            files = {'OrcaSlicer_profile_validator.exe': b'fake', 'resources/profiles/Vendor/root.json': b'{}'}
            for name, content in files.items():
                (engine / name).write_bytes(content)
            manifest = {'revision': 'pin', 'resources_revision': 'pin', 'files': {n: hashlib.sha256(c).hexdigest() for n, c in files.items()}}
            (engine / 'engine-manifest.json').write_text(json.dumps(manifest))
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(root), create=True), patch.dict(os.environ, {'PROFILELAB_ORCA_VALIDATOR': ''}):
                self.assertIsNone(bundled_engine_problem())
                (engine / 'resources/profiles/Vendor/root.json').write_text('changed')
                self.assertIn('Reinstall Profile Lab', bundled_engine_problem())
                with patch('profilelab.engine_validator._run_copied_tree') as run:
                    result = run_orca_engine_for_user_profiles(engine / 'resources', root)
                    self.assertEqual(result.status, 'failed')
                    run.assert_not_called()

    def test_unresolved_parent_is_not_hidden_by_successful_native_exit(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / 'resources'
            (resources / 'profiles/Vendor').mkdir(parents=True)
            (resources / 'profiles/Vendor.json').write_text('{}')
            user = root / 'user/default'
            user.mkdir(parents=True)
            (user / 'broken.json').write_text(json.dumps({'name': 'Broken', 'type': 'machine', 'inherits': 'Missing'}))
            with patch('profilelab.engine_validator._run_copied_tree') as run:
                result = run_orca_engine_for_user_profiles(resources, user)
                self.assertEqual(result.status, 'failed')
                self.assertIn('Missing', result.details)
                run.assert_not_called()

    def test_only_real_matching_category_parent_resolves_missing_parent(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            user = root / 'user/default'
            user.mkdir(parents=True)
            resources = root / 'resources'
            (resources / 'profiles/Vendor').mkdir(parents=True)
            parent = resources / 'profiles/Vendor/base.json'
            (user / 'custom.json').write_text(json.dumps({'name': 'Custom', 'type': 'machine', 'inherits': 'Base'}))
            parent.write_text(json.dumps({'name': 'Base', 'type': 'filament'}))
            self.assertFalse(validate_user_folder(user, resources).is_valid)
            parent.write_text(json.dumps({'name': 'Base', 'type': 'machine'}))
            self.assertTrue(validate_user_folder(user, resources).is_valid)
