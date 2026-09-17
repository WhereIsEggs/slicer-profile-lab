"""Searchable system library; no editing of source presets."""

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget, QTabWidget, QSplitter, QSplitterHandle, QInputDialog, QMessageBox,
)

from profilelab.library import VERSION, install_snapshot, library_home, read_snapshot, search_profiles, check_library_updates
from profilelab.resolver import ProfileResolver, ResolutionError
from profilelab.drafts import create_draft, drafts_home
from profilelab.setting_editor import display_value

TYPE_LABELS = {"machine": "Printer", "machine_model": "Printer model", "filament": "Filament", "process": "Process"}


class GripHandle(QSplitterHandle):
    """A familiar three-line grab marker that keeps Qt's resize behavior."""

    def paintEvent(self, event):
        painter = QPainter(self)
        palette = self.palette()
        hovered = self.underMouse()
        painter.fillRect(self.rect(), palette.color(
            QPalette.ColorRole.Mid if hovered else QPalette.ColorRole.Window
        ))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(palette.color(
            QPalette.ColorRole.Highlight if hovered else QPalette.ColorRole.WindowText
        ), 1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        center = self.rect().center()
        for offset in (-2, 0, 2):
            painter.drawLine(center.x() - 6, center.y() + offset,
                             center.x() + 6, center.y() + offset)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()


class ProfileSplitter(QSplitter):
    def createHandle(self):
        handle = GripHandle(self.orientation(), self)
        handle.setCursor(Qt.CursorShape.SplitVCursor)
        handle.setToolTip("Drag up or down to resize the profile list and settings")
        return handle


class LibraryWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = root

    def run(self):
        try:
            self.ready.emit(install_snapshot(self.root, self.progress.emit))
        except Exception as error:
            self.failed.emit(f"Library could not be loaded: {error}")


class LibraryUpdateWorker(QThread):
    result = Signal(str)

    def run(self):
        try:
            self.result.emit(check_library_updates())
        except Exception as error:
            self.result.emit(f"Could not check for updates: {error}. Your saved library is still available.")


class LibraryView(QWidget):
    draft_created = Signal(object)

    def __init__(self, parent=None, root=None, draft_root=None, snapshot=None):
        super().__init__(parent)
        self.root = root if root is not None else library_home()
        self.worker = None
        self.update_worker = None
        self.demo_mode = bool(snapshot and snapshot["metadata"].get("demo"))
        self.profiles = []
        self.matches = []
        self.resolver = ProfileResolver([])
        self.resolved = {}
        self.metadata = {}
        self.draft_root = draft_root if draft_root is not None else drafts_home()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("System profile library")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        note = QLabel("Fictional offline library. Select the Demo Dual Printer, then create your own draft."
                      if self.demo_mode else "Official OrcaSlicer 2.4.2 profiles. Select a profile to see its own and inherited values.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel("No library downloaded yet.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.download = QPushButton(f"Download {VERSION} library")
        self.download.clicked.connect(self.start_download)
        layout.addWidget(self.download)
        self.download.setVisible(not self.demo_mode)
        self.check_updates = QPushButton("Check for updates")
        self.check_updates.setToolTip("Check GitHub for a newer stable OrcaSlicer release. Does not replace your library or drafts.")
        self.check_updates.clicked.connect(self.start_update_check)
        self.check_updates.setVisible(not self.demo_mode)
        layout.addWidget(self.check_updates)
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search profile, vendor, or parent…")
        self.search.textChanged.connect(self.filter_profiles)
        row.addWidget(self.search, 1)
        self.kind = QComboBox()
        self.kind.addItem("All profile types", "")
        for key, label in TYPE_LABELS.items():
            self.kind.addItem(label, key)
        self.kind.currentIndexChanged.connect(self.filter_profiles)
        row.addWidget(self.kind)
        layout.addLayout(row)
        self.count = QLabel("0 profiles")
        layout.addWidget(self.count)
        self.create_button = QPushButton("Create draft from selected profile…")
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.make_draft)
        layout.addWidget(self.create_button)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Profile", "Type", "Vendor", "Parent"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.itemSelectionChanged.connect(self.show_selected)
        self.panel_splitter = ProfileSplitter(Qt.Orientation.Vertical)
        self.panel_splitter.setChildrenCollapsible(False)
        self.panel_splitter.setHandleWidth(11)
        self.panel_splitter.addWidget(self.table)
        detail_tabs = QTabWidget()
        effective = QWidget()
        effective_layout = QVBoxLayout(effective)
        self.resolution_status = QLabel("Values from profile files only; OrcaSlicer's internal defaults are not included.")
        self.resolution_status.setWordWrap(True)
        effective_layout.addWidget(self.resolution_status)
        self.setting_search = QLineEdit()
        self.setting_search.setPlaceholderText("Find a setting…")
        self.setting_search.textChanged.connect(self.filter_settings)
        effective_layout.addWidget(self.setting_search)
        self.settings_table = QTableWidget(0, 4)
        self.settings_table.setHorizontalHeaderLabels(["Setting", "Value", "Origin", "Source profile"])
        self.settings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.settings_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.settings_table.setAlternatingRowColors(True)
        self.settings_table.verticalHeader().hide()
        effective_layout.addWidget(self.settings_table)
        detail_tabs.addTab(effective, "Resolved settings")
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select a profile to inspect its stored settings.")
        detail_tabs.addTab(self.details, "Source JSON")
        self.panel_splitter.addWidget(detail_tabs)
        self.panel_splitter.setSizes([300, 300])
        self.panel_splitter.setStretchFactor(0, 1)
        self.panel_splitter.setStretchFactor(1, 1)
        self.panel_splitter.handle(1).setToolTip("Drag up or down to resize the profile list and settings")
        self.panel_splitter.handle(1).setCursor(Qt.CursorShape.SplitVCursor)
        layout.addWidget(self.panel_splitter, 1)
        attribution = QLabel('Fictional demonstration data · Not manufacturer-approved print settings' if self.demo_mode else
                             'Source: <a href="https://github.com/OrcaSlicer/OrcaSlicer/tree/v2.4.2/resources/profiles">'
                             'OrcaSlicer public profiles</a> · AGPL-3.0 · Offline after download')
        attribution.setOpenExternalLinks(True)
        layout.addWidget(attribution)
        try:
            snapshot = snapshot if snapshot is not None else read_snapshot(self.root)
            if snapshot:
                self.show_snapshot(snapshot)
        except Exception as error:
            self.status.setText(f"Saved library could not be read: {error}")

    def start_update_check(self):
        if self.demo_mode or self.update_worker is not None:
            return
        self.check_updates.setEnabled(False)
        self.status.setText("Checking official OrcaSlicer releases on GitHub…")
        self.update_worker = LibraryUpdateWorker(self)
        self.update_worker.result.connect(self.status.setText)
        self.update_worker.finished.connect(self.update_check_finished)
        self.update_worker.start()

    def update_check_finished(self):
        self.update_worker.deleteLater()
        self.update_worker = None
        self.check_updates.setEnabled(True)

    def start_download(self):
        if self.demo_mode:
            return
        if self.worker is not None:
            return
        self.download.setEnabled(False)
        self.worker = LibraryWorker(self.root, self)
        self.worker.progress.connect(self.status.setText)
        self.worker.ready.connect(self.show_snapshot)
        self.worker.failed.connect(self.status.setText)
        self.worker.finished.connect(self.download_finished)
        self.worker.start()

    def download_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.download.setEnabled(not bool(self.profiles))

    def show_snapshot(self, snapshot):
        self.profiles = snapshot["profiles"]
        self.resolver = ProfileResolver(self.profiles)
        metadata = snapshot["metadata"]
        self.metadata = metadata
        self.status.setText("DEMO · Ready offline · Your real library is unchanged" if self.demo_mode else
                            f"OrcaSlicer {metadata['version']} · Revision {metadata['revision'][:12]} · "
                            f"Downloaded {metadata['downloaded_at'][:10]}")
        self.download.setText("Library available offline")
        self.download.setEnabled(False)
        self.filter_profiles()

    def filter_profiles(self):
        self.create_button.setEnabled(False)
        self.matches = search_profiles(self.profiles, self.search.text(), self.kind.currentData())
        self.table.setRowCount(0)
        self.details.clear()
        self.resolved = {}
        self.filter_settings()
        self.resolution_status.setText("Select a profile to see its resolved settings.")
        self.table.setRowCount(len(self.matches))
        for row, profile in enumerate(self.matches):
            for column, text in enumerate((profile["name"], TYPE_LABELS[profile["type"]],
                                           profile["vendor"], profile["parent"])):
                self.table.setItem(row, column, QTableWidgetItem(str(text)))
        self.count.setText(f"{len(self.matches):,} of {len(self.profiles):,} profiles")

    def show_selected(self):
        self.create_button.setEnabled(False)
        row = self.table.currentRow()
        if not 0 <= row < len(self.matches):
            return
        profile = self.matches[row]
        import json
        category = "Base template / model" if profile["template"] else "Selectable preset"
        self.details.setPlainText(f"{category}\nSource file: {profile['path']}\n\n"
                                 + json.dumps(profile["settings"], indent=2, ensure_ascii=False))
        self.resolved = {}
        try:
            self.resolved = self.resolver.resolve(profile)
            self.create_button.setEnabled(profile["type"] in {"machine", "filament", "process"} and not profile.get("template", False))
            self.resolution_status.setText(
                f"{len(self.resolved)} settings from the profile chain. "
                "OrcaSlicer's internal defaults are not included."
            )
        except ResolutionError as error:
            self.resolution_status.setText(f"Cannot resolve this profile: {error}")
        self.filter_settings()

    def make_draft(self):
        row = self.table.currentRow()
        if not self.create_button.isEnabled() or not 0 <= row < len(self.matches):
            return
        profile = self.matches[row]
        name, accepted = QInputDialog.getText(
            self, "Create profile draft", "Name your new draft:", text=f"{profile['name']} - Custom"
        )
        if not accepted:
            return
        try:
            draft = create_draft(self.draft_root, name, profile, self.metadata, self.resolver)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Draft could not be saved", str(error))
            return
        self.draft_created.emit(draft)

    def filter_settings(self):
        import json
        query = self.setting_search.text().casefold().strip()
        matches = [(key, setting) for key, setting in sorted(self.resolved.items())
                   if query in key.replace("_", " ").casefold() or query in key.casefold()]
        self.settings_table.setRowCount(0)
        self.settings_table.setRowCount(len(matches))
        for row, (key, setting) in enumerate(matches):
            value = display_value(setting.value, key)
            source = f"{setting.source_name} ({setting.source_vendor})"
            for column, text in enumerate((key.replace("_", " ").capitalize(), value, setting.status, source)):
                item = QTableWidgetItem(text)
                item.setToolTip(key if column == 0 else (setting.source_path if column == 3 else text))
                self.settings_table.setItem(row, column, item)
