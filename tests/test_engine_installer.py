# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from profilelab.engine_installer import install_engine


class EngineInstallerTests(unittest.TestCase):
    def test_ready_engine_never_downloads(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / 'validator.exe'
            executable.touch()
            (root / 'profiles' / 'Vendor').mkdir(parents=True)
            (root / 'profiles' / 'Vendor.json').write_text('{}')
            with patch('profilelab.engine_installer.validator_path', return_value=executable), \
                 patch('profilelab.engine_installer.validation_engine_resources', return_value=root), \
                 patch('urllib.request.urlopen') as network:
                self.assertEqual(install_engine(), executable)
                network.assert_not_called()

    def test_missing_engine_requires_app_repair_not_nightly(self):
        with TemporaryDirectory() as temporary:
            with patch('profilelab.engine_installer.validator_path', return_value=Path(temporary) / 'missing.exe'), \
                 patch('urllib.request.urlopen') as network:
                with self.assertRaisesRegex(ValueError, 'Reinstall Profile Lab'):
                    install_engine()
                network.assert_not_called()
