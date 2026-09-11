"""Searchable system library; no editing of source presets."""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)

from profilelab.library import VERSION, install_snapshot, library_home, read_snapshot, search_profiles

TYPE_LABELS = {"machine": "Printer", "machine_model": "Printer model", "filament": "Filament", "process": "Process"}


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


class LibraryView(QWidget):
    def __init__(self, parent=None, root=None):
        super().__init__(parent)
        self.root = root if root is not None else library_home()
        self.worker = None
        self.profiles = []
        self.matches = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("System profile library")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        note = QLabel("Official OrcaSlicer 2.4.2 profiles. Browse source settings locally; "
                      "inherited values are not yet expanded. Your installed OrcaSlicer profiles stay unchanged.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel("No library downloaded yet.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.download = QPushButton(f"Download {VERSION} library")
        self.download.clicked.connect(self.start_download)
        layout.addWidget(self.download)
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
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Profile", "Type", "Vendor", "Parent"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected)
        layout.addWidget(self.table, 2)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select a profile to inspect its stored settings.")
        layout.addWidget(self.details, 1)
        attribution = QLabel('Source: <a href="https://github.com/OrcaSlicer/OrcaSlicer/tree/v2.4.2/resources/profiles">'
                             'OrcaSlicer public profiles</a> · AGPL-3.0 · Offline after download')
        attribution.setOpenExternalLinks(True)
        layout.addWidget(attribution)
        try:
            snapshot = read_snapshot(self.root)
            if snapshot:
                self.show_snapshot(snapshot)
        except Exception as error:
            self.status.setText(f"Saved library could not be read: {error}")

    def start_download(self):
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
        metadata = snapshot["metadata"]
        self.status.setText(f"OrcaSlicer {metadata['version']} · Revision {metadata['revision'][:12]} · "
                            f"Downloaded {metadata['downloaded_at'][:10]}")
        self.download.setText("Library available offline")
        self.download.setEnabled(False)
        self.filter_profiles()

    def filter_profiles(self):
        self.matches = search_profiles(self.profiles, self.search.text(), self.kind.currentData())
        self.table.setRowCount(0)
        self.details.clear()
        self.table.setRowCount(len(self.matches))
        for row, profile in enumerate(self.matches):
            for column, text in enumerate((profile["name"], TYPE_LABELS[profile["type"]],
                                           profile["vendor"], profile["parent"])):
                self.table.setItem(row, column, QTableWidgetItem(str(text)))
        self.count.setText(f"{len(self.matches):,} of {len(self.profiles):,} profiles")

    def show_selected(self):
        row = self.table.currentRow()
        if not 0 <= row < len(self.matches):
            return
        profile = self.matches[row]
        import json
        category = "Base template / model" if profile["template"] else "Selectable preset"
        self.details.setPlainText(f"{category}\nSource file: {profile['path']}\n\n"
                                 + json.dumps(profile["settings"], indent=2, ensure_ascii=False))
