"""Reopen saved drafts independently of future library downloads."""

import os
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit,
)
from profilelab.drafts import drafts_home, load_drafts, save_override, delete_draft
from profilelab.user_sharing import share_prepared_package
from profilelab.setting_editor import display_value, editable_value, SettingDialog
from profilelab.library import library_home, read_snapshot
from profilelab.profile_choices import compatible_filaments, compatible_processes
from profilelab.profile_install import read_install_bundle
from profilelab.user_install import exportable_profiles, install_user_profiles
from profilelab.draft_package import prepare_draft_profiles, save_named_package
from profilelab.orca_bundle import export_orca_bundle
from profilelab.package_preview import PackagePreview, package_groups


class DraftsView(QWidget):
    def __init__(self, parent=None, root=None, snapshot=None, package_root=None, demo=False):
        super().__init__(parent)
        self.root = root if root is not None else drafts_home()
        self.drafts = []
        self.snapshot = snapshot
        self.package_root = package_root
        self.demo_mode = demo
        self.last_package = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("My drafts")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        intro = QLabel("Click a value to edit it. Changes are saved to this draft. "
                       "Setting names and original system profiles stay unchanged.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        actions = QHBoxLayout()
        refresh = QPushButton("Refresh drafts")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        self.delete_button = QPushButton("Delete draft…")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_draft)
        actions.addWidget(self.delete_button)
        prepare = QPushButton("Prepare sharing package…")
        self.prepare_button = prepare
        prepare.setEnabled(False)
        prepare.clicked.connect(self.prepare_package)
        actions.addWidget(prepare)
        install = QPushButton("Install prepared package into OrcaSlicer…")
        install.clicked.connect(self.install_package)
        self.install_button = install
        install.setVisible(not demo)
        actions.addWidget(install)
        actions.addStretch()
        layout.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.open_package = QPushButton("Open saved package folder")
        self.open_package.setVisible(False)
        self.open_package.clicked.connect(self.open_package_folder)
        layout.addWidget(self.open_package)
        self.list = QListWidget()
        self.list.setMaximumHeight(125)
        self.list.currentRowChanged.connect(self.show_draft)
        layout.addWidget(self.list, 1)
        self.base_info = QLabel("Select a draft to review its starting values.")
        self.base_info.setWordWrap(True)
        layout.addWidget(self.base_info)
        self.setting_search = QLineEdit()
        self.setting_search.setPlaceholderText("Find a setting…")
        self.setting_search.textChanged.connect(self.filter_settings)
        layout.addWidget(self.setting_search)
        self.values = QTableWidget(0, 2)
        self.values.setHorizontalHeaderLabels(["Setting", "Value — click to edit"])
        self.values.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.values.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.values.setAlternatingRowColors(True)
        self.values.verticalHeader().hide()
        self.values.cellClicked.connect(self.edit_value)
        layout.addWidget(self.values, 2)
        reset = QPushButton("Reset selected setting to starting value")
        reset.clicked.connect(self.reset_value)
        layout.addWidget(reset)
        self.refresh()

    def prepare_package(self):
        row = self.list.currentRow()
        if not 0 <= row < len(self.drafts):
            self.status.setText("Select a draft to prepare for sharing.")
            return
        try:
            current, errors = load_drafts(self.root)
            if errors:
                raise ValueError("Some drafts could not be read. Fix those drafts before preparing a package.")
            snapshot = self.snapshot if self.snapshot is not None else read_snapshot(library_home())
            profiles, selected = prepare_draft_profiles(self.drafts[row]["id"], current, snapshot)
            preview = PackagePreview(profiles, selected[1], self, demo=self.demo_mode)
            if preview.exec() != QDialog.DialogCode.Accepted:
                return
            destination = save_named_package(profiles, selected, self.package_root if self.package_root is not None else library_home().parent / "sharing", demo=self.demo_mode)
            read_install_bundle(destination)
            sharing = share_prepared_package(destination) if not self.demo_mode else None
            self.last_package = destination
            self.open_package.setVisible(True)
            self.status.setText(f"Package created: {destination.name}\nSaved automatically. Package structure checked; full Orca validation is not certified.")
            if sharing:
                self.status.setText(f"Ready to share: {sharing.name}\nSend the ZIP. In OrcaSlicer, use File → Import → Import Configs. It imports as user profiles, not bundle presets.")
            if self.demo_mode:
                self.status.setText(self.status.text() + "\nDemo only — nothing was installed into OrcaSlicer.")
                return
            if QMessageBox.question(self, "Package saved", "Install this package into OrcaSlicer now? Close OrcaSlicer first.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.install_package(str(destination))
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            QMessageBox.warning(self, "Package could not be prepared", str(error))

    def install_package(self, selected=None):
        if self.demo_mode:
            self.status.setText("Installation is disabled in demo mode. Your OrcaSlicer profiles are unchanged.")
            return
        if not isinstance(selected, str):
            if self.last_package is not None:
                selected = str(self.last_package)
            else:
                selected, _ = QFileDialog.getOpenFileName(self, "Choose prepared package", "", "Orca bundle (*.orca_bundle)")
        if not selected:
            return
        try:
            if not os.environ.get("APPDATA"):
                raise ValueError("The Windows user profile location could not be found.")
            target = Path(os.environ["APPDATA"]) / "OrcaSlicer" / "user" / "default"
            profiles = exportable_profiles(Path(selected))
            groups = package_groups(profiles)
            preview = "\n".join(f"{group}: {len(names)}" for group, names in groups.items() if names)
            answer = QMessageBox.question(self, "Install prepared profiles", "Close OrcaSlicer before continuing.\n\n" + preview + "\n\nYour printer, materials and processes will be installed as user profiles, ready to export from OrcaSlicer. Their saved parent settings are included automatically. Existing profiles will not be replaced.\n\nAfter installation, open OrcaSlicer and select the new printer.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            installed = install_user_profiles(Path(selected), target)
            printers = ", ".join(groups["Printers"])
            outcome = "Installed successfully." if installed else "This exact package is already installed."
            self.status.setText(outcome + (f"\nOpen OrcaSlicer and select: {printers}" if printers else "\nOpen OrcaSlicer to review the installed profiles.") + "\nCheck the filament and process selectors before printing. Installation does not certify print safety.")
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            QMessageBox.warning(self, "Installation could not finish", str(error))

    def delete_selected_draft(self):
        row = self.list.currentRow()
        if not 0 <= row < len(self.drafts):
            return
        draft = self.drafts[row]
        answer = QMessageBox.question(self, "Delete draft?", f"Remove '{draft['name']}' from My drafts?\n\nIt will be moved to the deleted-drafts backup. Saved packages and profiles installed in OrcaSlicer will not be removed.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_draft(self.root, draft)
            self.last_package = None
            self.open_package.setVisible(False)
            self.refresh()
            self.status.setText("Draft removed. A recoverable copy is in the deleted-drafts folder. Packages and installed profiles are unchanged.")
        except (OSError, ValueError, KeyError) as error:
            QMessageBox.warning(self, "Draft could not be deleted", str(error))

    def refresh(self, selected_id=None):
        self.values.setRowCount(0)
        self.base_info.setText("Select a draft to review its starting values.")
        self.list.clear()
        self.prepare_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        try:
            self.drafts, errors = load_drafts(self.root)
            self.status.setText(f"{len(self.drafts)} saved draft(s)." +
                                (" Some files could not be loaded: " + "; ".join(errors) if errors else ""))
        except OSError as error:
            self.drafts = []
            self.status.setText(f"Could not read drafts: {error}")
        for row, draft in enumerate(self.drafts):
            label = {"machine": "Printer", "process": "Process", "filament": "Filament"}[draft["type"]]
            self.list.addItem(f"{draft['name']} — {label}")
        if selected_id:
            for row, draft in enumerate(self.drafts):
                if draft.get("id") == selected_id:
                    self.list.setCurrentRow(row)
                    break

    def show_draft(self, row):
        self.values.setRowCount(0)
        self.prepare_button.setEnabled(0 <= row < len(self.drafts))
        self.delete_button.setEnabled(0 <= row < len(self.drafts))
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
        self.filter_settings()

    def filter_settings(self):
        query = self.setting_search.text().strip().casefold()
        for row in range(self.values.rowCount()):
            item = self.values.item(row, 0)
            self.values.setRowHidden(row, bool(item and query not in item.text().casefold()))

    def open_package_folder(self):
        if self.last_package is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_package.parent)))

    def edit_value(self, row, column):
        if column != 1 or not 0 <= self.list.currentRow() < len(self.drafts):
            return
        draft = self.drafts[self.list.currentRow()]
        key = self.values.item(row, 0).data(Qt.ItemDataRole.UserRole)
        value = draft.get("overrides", {}).get(key, draft["base_values"][key])
        if not editable_value(value):
            QMessageBox.information(self, "Specialized setting", "This setting needs a dedicated editor and is read-only for now.")
            return
        options = {"extruder_slots": key in {"nozzle_diameter", "retraction_length", "retraction_speed", "retract_when_changing_layer", "extruder_offset"}}
        if key in {"default_filament_profile", "default_print_profile"}:
            try:
                snapshot = self.snapshot if self.snapshot is not None else read_snapshot(library_home())
                choices = (compatible_filaments if key == "default_filament_profile" else compatible_processes)(draft, snapshot)
            except (OSError, ValueError, KeyError):
                choices = []
            options = {"choices": choices, "extruder_slots": key == "default_filament_profile"}
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
