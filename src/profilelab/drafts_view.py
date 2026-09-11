"""Reopen saved drafts independently of future library downloads."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QDialog,
)
from profilelab.drafts import drafts_home, load_drafts, save_override
from profilelab.setting_editor import display_value, editable_value, SettingDialog
from profilelab.library import library_home, read_snapshot
from profilelab.profile_choices import compatible_filaments


class DraftsView(QWidget):
    def __init__(self, parent=None, root=None):
        super().__init__(parent)
        self.root = root if root is not None else drafts_home()
        self.drafts = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("My drafts")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        intro = QLabel("Click a value to edit it. Changes are saved to this draft. "
                       "Setting names and original system profiles stay unchanged.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        refresh = QPushButton("Refresh drafts")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.show_draft)
        layout.addWidget(self.list, 1)
        self.base_info = QLabel("Select a draft to review its starting values.")
        self.base_info.setWordWrap(True)
        layout.addWidget(self.base_info)
        self.values = QTableWidget(0, 2)
        self.values.setHorizontalHeaderLabels(["Setting", "Value — click to edit"])
        self.values.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.values.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.values.cellClicked.connect(self.edit_value)
        layout.addWidget(self.values, 2)
        reset = QPushButton("Reset selected setting to starting value")
        reset.clicked.connect(self.reset_value)
        layout.addWidget(reset)
        self.refresh()

    def refresh(self, selected_id=None):
        self.values.setRowCount(0)
        self.base_info.setText("Select a draft to review its starting values.")
        self.list.clear()
        try:
            self.drafts, errors = load_drafts(self.root)
            self.status.setText(f"{len(self.drafts)} saved draft(s)." +
                                (" Some files could not be loaded: " + "; ".join(errors) if errors else ""))
        except OSError as error:
            self.drafts = []
            self.status.setText(f"Could not read drafts: {error}")
        for row, draft in enumerate(self.drafts):
            self.list.addItem(f"{draft['name']} — {draft['type']}")
        if selected_id:
            for row, draft in enumerate(self.drafts):
                if draft.get("id") == selected_id:
                    self.list.setCurrentRow(row)
                    break

    def show_draft(self, row):
        self.values.setRowCount(0)
        if not 0 <= row < len(self.drafts):
            return
        draft = self.drafts[row]
        self.base_info.setText(
            f"Based on {draft['base'].get('name', 'Unknown')} · OrcaSlicer {draft['library'].get('version', 'Unknown')}\n"
            "Starting values are saved with the draft and do not change when the library updates. "
            "OrcaSlicer's internal defaults are not included."
        )
        self.values.setRowCount(len(draft["base_values"]))
        for row, (key, value) in enumerate(sorted(draft["base_values"].items())):
            value = draft.get("overrides", {}).get(key, value)
            name_item = QTableWidgetItem(key.replace("_", " ").capitalize())
            name_item.setData(Qt.ItemDataRole.UserRole, key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            value_item = QTableWidgetItem(display_value(value, key))
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            changed = key in draft.get("overrides", {})
            value_item.setToolTip(("Changed in this draft. " if changed else "Starting value. ") +
                                 ("Click to edit." if editable_value(value) else "This setting needs a specialized editor."))
            font = value_item.font()
            font.setBold(changed)
            value_item.setFont(font)
            self.values.setItem(row, 0, name_item)
            self.values.setItem(row, 1, value_item)

    def edit_value(self, row, column):
        if column != 1 or not 0 <= self.list.currentRow() < len(self.drafts):
            return
        draft = self.drafts[self.list.currentRow()]
        key = self.values.item(row, 0).data(Qt.ItemDataRole.UserRole)
        value = draft.get("overrides", {}).get(key, draft["base_values"][key])
        if not editable_value(value):
            QMessageBox.information(self, "Specialized setting", "This setting needs a dedicated editor and is read-only for now.")
            return
        options = {}
        if key == "default_filament_profile":
            try:
                snapshot = read_snapshot(library_home())
                choices = compatible_filaments(draft, snapshot)
            except (OSError, ValueError, KeyError):
                choices = []
            options = {"choices": choices, "extruder_slots": True}
        dialog = SettingDialog(self.values.item(row, 0).text(), key, value, self, **options)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store_change(draft, key, dialog.value)

    def reset_value(self):
        row = self.values.currentRow()
        if row < 0 or not 0 <= self.list.currentRow() < len(self.drafts):
            return
        draft = self.drafts[self.list.currentRow()]
        key = self.values.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.store_change(draft, key, draft["base_values"][key], reset=True)

    def store_change(self, draft, key, value, reset=False):
        try:
            updated = save_override(self.root, draft, key, value, reset=reset)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Change could not be saved", str(error))
            return
        self.drafts[self.list.currentRow()] = updated
        self.show_draft(self.list.currentRow())
        self.status.setText("Draft saved. Changed values are shown in bold.")
