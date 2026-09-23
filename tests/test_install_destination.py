# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from profilelab.install_destination import install_destination


class InstallDestinationTests(unittest.TestCase):
    def test_packaged_app_ignores_local_override(self):
        with patch('profilelab.install_destination.sys.frozen', True, create=True), patch.dict('os.environ', {'APPDATA': 'C:/normal'}):
            target, label = install_destination()
            self.assertEqual(target, Path('C:/normal/OrcaSlicer/user/default'))
            self.assertIn('Normal', label)

    def test_local_override_and_missing_folder_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            module = root / 'src/profilelab/install_destination.py'
            (root / 'local-orca-test.json').write_text('{"data_dir":"test-data"}')
            with patch('profilelab.install_destination.__file__', str(module)):
                with self.assertRaisesRegex(ValueError, 'missing'):
                    install_destination()
                (root / 'test-data').mkdir()
                target, label = install_destination()
                self.assertEqual(target, root / 'test-data/user/default')
                self.assertIn('2.5', label)

    def test_no_local_override_uses_normal_profiles(self):
        with TemporaryDirectory() as temp, patch.dict('os.environ', {'APPDATA': 'C:/normal'}):
            with patch('profilelab.install_destination.__file__', str(Path(temp) / 'src/profilelab/install_destination.py')):
                self.assertEqual(install_destination()[0], Path('C:/normal/OrcaSlicer/user/default'))
