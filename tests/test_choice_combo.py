# SPDX-License-Identifier: AGPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QDialog
from profilelab.choice_combo import ChoiceComboBox, ChoiceDialog
from profilelab.desktop_theme import apply_theme


class ChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def test_long_combo_preserves_data_and_cancel(self):
        combo = ChoiceComboBox()
        for i in range(100):
            combo.addItem('Vendor ' + str(i), {'id': i})
        combo.setCurrentIndex(4)
        def select():
            dialog = QApplication.activeModalWidget()
            dialog.search.setText('Vendor 91')
            dialog.list.setCurrentRow(91)
            dialog.accept_selection()
        QTimer.singleShot(0, select)
        combo.showPopup()
        self.assertEqual(combo.currentData(), {'id': 91})
        QTimer.singleShot(0, lambda: QApplication.activeModalWidget().reject())
        combo.showPopup()
        self.assertEqual(combo.currentData(), {'id': 91})
        self.assertFalse(combo.isEditable())

    def test_large_dialog_is_bounded_and_search_never_changes_source(self):
        names = ['All vendors', 're3D PC', 're3D PLA'] + [f'Example vendor {i}' for i in range(100)]
        dialog = ChoiceDialog(names, 0)
        dialog.show()
        self.app.processEvents()
        dialog.search.setText('RE3d pc')
        self.assertEqual(dialog.count.text(), '1 choice')
        self.assertFalse(dialog.choose.isEnabled())
        dialog.accept_selection()
        self.assertIsNone(dialog.selected_index)
        dialog.list.setCurrentRow(1)
        self.assertTrue(dialog.choose.isEnabled())
        dialog.search.setText('not a valid vendor')
        self.assertFalse(dialog.choose.isEnabled())
        self.assertEqual(dialog.list.count(), len(names))
        dialog.search.clear()
        self.assertLessEqual(dialog.height(), dialog.screen().availableGeometry().height())
        self.assertEqual(dialog.list.item(1).text(), 're3D PC')
        if os.environ.get('PROFILELAB_CHOICE_SCREENSHOT'):
            self.assertTrue(dialog.grab().save(os.environ['PROFILELAB_CHOICE_SCREENSHOT']))
        dialog.close()

    def test_small_combo_stays_bounded(self):
        combo = ChoiceComboBox()
        combo.addItems(['Off', 'On'])
        self.assertEqual(combo.maxVisibleItems(), 10)
        with patch('profilelab.choice_combo.ChoiceDialog') as dialog:
            combo.showPopup()
            dialog.assert_not_called()
            combo.hidePopup()
