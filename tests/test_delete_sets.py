# SPDX-License-Identifier: AGPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QMessageBox
from profilelab.profile_sets import new_set, save_set, load_sets, delete_set
from profilelab.profile_sets_view import ProfileSetsView


class DeleteSetTests(unittest.TestCase):
    def test_backup_and_scope(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            selected, other = new_set('Test'), new_set('Keep')
            save_set(root, selected)
            save_set(root, other)
            source = root / (selected['id'] + '.json')
            original = source.read_bytes()
            package = root / 'keep.orca_bundle'
            package.write_bytes(b'unchanged')
            backup = delete_set(root, selected)
            self.assertEqual(backup.read_bytes(), original)
            self.assertFalse(source.exists())
            self.assertEqual(load_sets(root), [other])
            self.assertEqual(package.read_bytes(), b'unchanged')
            with self.assertRaises(FileNotFoundError):
                delete_set(root, selected)

    def test_stale_and_invalid_targets_are_not_deleted(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            selected = new_set('Original')
            save_set(root, selected)
            stale = deepcopy(selected)
            selected['name'] = 'Updated'
            save_set(root, selected)
            with self.assertRaisesRegex(ValueError, 'changed'):
                delete_set(root, stale)
            stale['id'] = '../outside'
            with self.assertRaises(ValueError):
                delete_set(root, stale)
            self.assertEqual(load_sets(root), [selected])
            self.assertFalse((root / 'deleted').exists())

    def test_button_cancel_confirm_and_placeholder(self):
        app = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as folder:
            root = Path(folder)
            selected = new_set('Delete me')
            save_set(root, selected)
            view = ProfileSetsView(None, root=root)
            self.assertFalse(view.delete_button.isEnabled())
            view.open_set(1)
            self.assertTrue(view.delete_button.isEnabled())
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
                view.delete_button.click()
            self.assertEqual(load_sets(root), [selected])
            view.open_set(0)
            self.assertIsNone(view.data)
            self.assertFalse(view.delete_button.isEnabled())
            view.open_set(1)
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                view.delete_button.click()
            self.assertEqual(load_sets(root), [])
            self.assertIsNone(view.data)
            self.assertFalse(view.delete_button.isEnabled())
            self.assertEqual(view.members.count(), 0)
            self.assertEqual(view.values.rowCount(), 0)
            self.assertEqual(view.saved.currentIndex(), 0)
            self.assertIn('Recoverable backup', view.status.text())
            view.close()
