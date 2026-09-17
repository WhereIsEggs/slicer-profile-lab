# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from unittest.mock import patch
import zipfile

from profilelab.legal import legal_root, LEGAL_SUMMARY

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_sources', ROOT / 'packaging/source_archive.py')
release_sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_sources)


class LicensingTests(unittest.TestCase):
    def test_metadata_and_offline_notices(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
        self.assertEqual(project['license'], 'AGPL-3.0-only')
        self.assertIn('LICENSE.txt', project['license-files'])
        self.assertEqual(legal_root(), ROOT)
        self.assertIn('WITHOUT ANY WARRANTY', LEGAL_SUMMARY)
        license_text = (ROOT / 'LICENSE.txt').read_text()
        self.assertIn('GNU AFFERO GENERAL PUBLIC LICENSE', license_text)
        self.assertIn('END OF TERMS AND CONDITIONS', license_text)
        self.assertIn('OrcaSlicer attribution', (ROOT / 'NOTICE.md').read_text())

    def test_frozen_legal_files_are_resolved_offline(self):
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, '_MEIPASS', str(ROOT), create=True):
            self.assertEqual(legal_root(), ROOT)

    def test_source_archive_contains_rebuild_inputs_and_hashes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project.zip'
            release_sources.write_project_source(ROOT, project, {'version': 'test'})
            with zipfile.ZipFile(project) as archive:
                names = set(archive.namelist())
                for required in ('LICENSE.txt', 'NOTICE.md', 'pyproject.toml',
                                 'packaging/build_windows.py', 'packaging/source_archive.py',
                                 'packaging/installer.iss', 'tests/test_licensing.py',
                                 'tests/fixtures/root_profile/base_process.json'):
                    self.assertIn(required, names)
                self.assertFalse(any(name.startswith(('artifacts/', '.venv/', '.git/')) for name in names))
                manifest = json.loads(archive.read('source-manifest.json'))
                for name, digest in manifest.items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            dependencies = root / 'dependencies'
            dependencies.mkdir()
            (dependencies / 'example.tar.xz').write_bytes(b'fixture')
            full = root / 'full.zip'
            release_sources.write_complete_source(project, dependencies, full)
            with zipfile.ZipFile(full) as archive:
                self.assertIn('LICENSE.txt', archive.namelist())
                self.assertEqual(archive.read('dependency-sources/example.tar.xz'), b'fixture')
