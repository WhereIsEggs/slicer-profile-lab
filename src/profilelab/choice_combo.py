# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, searchable choices without accepting arbitrary profile names."""
from PySide6.QtCore import Qt, QEvent, QSize
from PySide6.QtWidgets import (QComboBox, QDialog, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QDialogButtonBox)


class ChoiceDialog(QDialog):
    def __init__(self, choices, current=-1, parent=None, title='Choose an option'):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selected_index = None
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Type to filter choices…')
        self.search.setClearButtonEnabled(True)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)
        for index, text in enumerate(choices):
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setToolTip(text)
            item.setSizeHint(QSize(0, max(28, self.fontMetrics().height() + 10)))
            self.list.addItem(item)
        self.list.setCurrentRow(current)
        self.count = QLabel()
        layout.addWidget(self.count)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.choose = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.choose.setText('Use selection')
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept_selection())
        self.list.currentItemChanged.connect(self.selection_changed)
        self.search.textChanged.connect(self.filter_choices)
        self.filter_choices()
        available = self.screen().availableGeometry()
        self.resize(min(620, int(available.width() * .85)), min(440, int(available.height() * .8)))
        self.search.setFocus()

    def eventFilter(self, watched, event):
        if watched is self.search and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Down:
            for row in range(self.list.count()):
                if not self.list.item(row).isHidden():
                    self.list.setCurrentRow(row)
                    self.list.setFocus()
                    return True
        return super().eventFilter(watched, event)

    def selection_changed(self, *_):
        item = self.list.currentItem()
        self.choose.setEnabled(item is not None and not item.isHidden())

    def filter_choices(self):
        terms = self.search.text().casefold().split()
        count = 0
        for row in range(self.list.count()):
            item = self.list.item(row)
            visible = all(term in item.text().casefold() for term in terms)
            item.setHidden(not visible)
            count += visible
        self.count.setText(f'{count} choice' + ('' if count == 1 else 's') if count else 'No matches. Try a different search.')
        self.selection_changed()

    def accept_selection(self):
        item = self.list.currentItem()
        if item is not None and not item.isHidden():
            self.selected_index = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


class ChoiceComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxVisibleItems(10)
        self.setMinimumContentsLength(16)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        # Qt's menu-style popup otherwise ignores maxVisibleItems on some styles.
        self.setStyleSheet('QComboBox { combobox-popup: 0; }')

    def showPopup(self):
        if self.count() <= 10:
            super().showPopup()
            return
        dialog = ChoiceDialog([self.itemText(i) for i in range(self.count())], self.currentIndex(), self,
                              self.accessibleName() or 'Choose an option')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            index = dialog.selected_index
            self.setCurrentIndex(index)
            self.activated.emit(index)
            self.textActivated.emit(self.itemText(index))
        self.hidePopup()


def choose_text(parent, title, choices):
    dialog = ChoiceDialog(choices, 0, parent, title)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return (choices[dialog.selected_index] if accepted else '', accepted)
