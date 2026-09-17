# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from unittest.mock import patch

from profilelab import __version__, DISPLAY_VERSION
from profilelab.engine_validator import _run_with_console_python
from profilelab.external_runtime import external_environment


class PackagingTests(unittest.TestCase):
    def test_version_matches_project_and_is_alpha(self):
        root = Path(__file__).resolve().parents[1]
        project = tomllib.loads((root / 'pyproject.toml').read_text())
        self.assertEqual(project['project']['version'], __version__)
        self.assertIn('Alpha', DISPLAY_VERSION)

    def test_frozen_app_never_tries_to_run_itself_as_python(self):
        with patch.object(sys, 'frozen', True, create=True), patch('subprocess.run') as run:
            result, detail = _run_with_console_python([], Path('engine.exe'), 1)
        self.assertIsNone(result)
        self.assertIn('packaged app', detail)
        run.assert_not_called()

    def test_child_environment_excludes_bundled_qt_without_mutating_parent(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'bundle'
            original = str(bundle / 'PySide6') + os.pathsep + str(root / 'system')
            with patch.object(sys, 'frozen', True, create=True), \
                 patch.object(sys, '_MEIPASS', str(bundle), create=True), \
                 patch.dict(os.environ, {'PATH': original, 'QT_PLUGIN_PATH': 'test'}):
                result = external_environment(root / 'engine' / 'validator.exe')
                self.assertNotIn(str(bundle), result['PATH'])
                self.assertIn(str(root / 'system'), result['PATH'])
                self.assertNotIn('QT_PLUGIN_PATH', result)
                self.assertEqual(os.environ['PATH'], original)

    def test_isolated_packaged_entry_smoke_from_source(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.json'
            environment = os.environ.copy()
            environment['QT_QPA_PLATFORM'] = 'offscreen'
            environment['PYTHONPATH'] = str(root / 'src')
            result = subprocess.run([sys.executable, str(root / 'packaging/launch.py'), '--smoke-test', str(report)],
                                    env=environment, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            data = json.loads(report.read_text())
            self.assertTrue(data['passed'])
            self.assertEqual(data['tabs'], 4)
            self.assertEqual(data['shared_profiles'], 3)
