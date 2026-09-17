# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from profilelab.app_updates import REPOSITORY, choose_update, download_update, version_key


def release(tag='v0.1.0-alpha.3'):
    filename = 'SlicerProfileLab-0.1.0a3-windows-x64-setup.exe'
    return dict(tag_name=tag, prerelease=True, assets=[dict(name=name, browser_download_url=
                REPOSITORY + '/releases/download/' + tag + '/' + name)
                for name in (filename, 'SHA256SUMS.txt')])


class UpdateTests(unittest.TestCase):
    def test_versions_and_channels(self):
        self.assertEqual(version_key('v0.1.0-alpha.2'), version_key('0.1.0a2'))
        self.assertGreater(version_key('0.1.0a10'), version_key('0.1.0a2'))
        self.assertIsNotNone(choose_update([release()], '0.1.0a2'))
        self.assertIsNone(choose_update([release()], '0.1.0a3'))
        self.assertIsNone(choose_update([release('v0.2.0-beta.1')], '0.1.0'))

    def test_incomplete_draft_and_foreign_downloads(self):
        item = release()
        item['draft'] = True
        self.assertIsNone(choose_update([item], '0.1.0a2'))
        item = release()
        item['assets'].pop()
        self.assertIsNone(choose_update([item], '0.1.0a2'))
        item = release()
        item['assets'][0]['browser_download_url'] = 'https://example.com/untrusted.exe'
        with self.assertRaises(ValueError):
            choose_update([item], '0.1.0a2')

    def test_download_verification_and_partial_cleanup(self):
        update = choose_update([release()], '0.1.0a2')
        data = b'fictional installer'
        checksum = (hashlib.sha256(data).hexdigest() + '  ' + update.filename).encode()
        with TemporaryDirectory() as folder:
            with patch('profilelab.app_updates.read_url', return_value=checksum), patch(
                    'urllib.request.urlopen', return_value=io.BytesIO(data)):
                target = download_update(update, folder)
                self.assertEqual(target.read_bytes(), data)
            with patch('profilelab.app_updates.read_url', return_value=checksum), patch(
                    'urllib.request.urlopen', return_value=io.BytesIO(b'corrupt')):
                with self.assertRaises(ValueError):
                    download_update(update, folder)
            self.assertEqual(list(Path(folder).rglob('*.exe')), [target])
            self.assertEqual(list(Path(folder).rglob('*.part')), [])

    def test_dialog_does_not_check_when_opened(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from profilelab.update_dialog import UpdateDialog
        app = QApplication.instance() or QApplication([])
        with patch('profilelab.update_dialog.check_update') as check:
            dialog = UpdateDialog()
            app.processEvents()
            check.assert_not_called()
            self.assertIsNone(dialog.worker)
            dialog.close()
