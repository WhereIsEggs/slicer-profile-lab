"""Native desktop validation window. Profile files are read only."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from profilelab.orca_status import OrcaStatus, get_orca_status
from profilelab.validation import validate_folder
from profilelab.engine_validator import run_orca_engine
from profilelab.library_view import LibraryView
from profilelab.drafts_view import DraftsView


def folder_picker_start(current_folder: str) -> str:
    """Prefer the current selection, then Orca's default user profiles."""
    if current_folder.strip():
        current = Path(current_folder.strip())
        if current.is_dir():
            return str(current)
    appdata = os.environ.get("APPDATA")
    if appdata:
        orca_folder = Path(appdata) / "OrcaSlicer"
        user_profiles = orca_folder / "user" / "default"
        if user_profiles.is_dir():
            return str(user_profiles)
        if orca_folder.is_dir():
            return str(orca_folder)
    return str(Path.home())


class ValidationWorker(QThread):
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, folder: Path, parent=None):
        super().__init__(parent)
        self.folder = folder

    def run(self):
        try:
            report = validate_folder(self.folder)
            engine_result = run_orca_engine(self.folder)
            self.result_ready.emit((report, engine_result))
        except (OSError, UnicodeError) as error:
            self.failed.emit(f"Could not read the profiles: {error}")
        except Exception as error:
            self.failed.emit(f"The check could not finish ({type(error).__name__}): {error}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("Slicer Profile Lab")
        self.resize(980, 700)
        self.setMinimumSize(720, 520)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        title = QLabel("Check your profile set")
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(title)
        intro = QLabel("Choose a folder of printer, filament, or process profiles. "
                       "Include their parent profiles; subfolders are checked too.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        row = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setPlaceholderText("Select a profile folder…")
        self.folder.textChanged.connect(self.clear_results)
        row.addWidget(self.folder, 1)
        self.browse = QPushButton("Choose folder…")
        self.browse.clicked.connect(self.choose_folder)
        row.addWidget(self.browse)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.check = QPushButton("Check profiles")
        self.check.setEnabled(False)
        self.check.clicked.connect(self.start_validation)
        row.addWidget(self.check)
        row.addStretch()
        refresh = QPushButton("Check OrcaSlicer status")
        refresh.clicked.connect(self.refresh_status)
        row.addWidget(refresh)
        layout.addLayout(row)
        self.orca_label = QLabel()
        self.orca_label.setWordWrap(True)
        layout.addWidget(self.orca_label)
        self.summary = QLabel("Ready when you are.")
        self.summary.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(self.summary)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Results will appear here after checking a folder.")
        layout.addWidget(self.results, 1)
        note = QLabel("This check does not change files. Passing these checks does not guarantee "
                      "OrcaSlicer import compatibility or print quality. Built-in parents are not loaded.")
        note.setWordWrap(True)
        layout.addWidget(note)
        tabs = QTabWidget()
        tabs.addTab(body, "Check profiles")
        self.library = LibraryView(self)
        tabs.addTab(self.library, "System library")
        self.drafts = DraftsView(self)
        tabs.addTab(self.drafts, "My drafts")
        self.library.draft_created.connect(self.open_draft)
        self.setCentralWidget(tabs)
        self.refresh_status()

    def open_draft(self, draft):
        self.drafts.refresh(draft["id"])
        self.centralWidget().setCurrentWidget(self.drafts)

    def clear_results(self):
        self.results.clear()
        self.summary.setText("Ready when you are.")
        self.check.setEnabled(bool(self.folder.text().strip()))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose profile folder", folder_picker_start(self.folder.text())
        )
        if folder:
            self.folder.setText(folder)

    def refresh_status(self):
        messages = {
            OrcaStatus.RUNNING: "OrcaSlicer is open. Read-only checks are available; close it before installing profiles.",
            OrcaStatus.CLOSED: "OrcaSlicer was not detected running. Status must be checked again before installation.",
            OrcaStatus.UNKNOWN: "OrcaSlicer status could not be confirmed. Read-only checks are still available.",
        }
        self.orca_label.setText(messages[get_orca_status()])

    def start_validation(self):
        if self.worker is not None:
            return
        folder = Path(self.folder.text().strip())
        self.folder.setEnabled(False)
        self.browse.setEnabled(False)
        self.check.setEnabled(False)
        self.results.clear()
        self.summary.setText("Checking profiles with Profile Lab and OrcaSlicer…")
        self.worker = ValidationWorker(folder, self)
        self.worker.result_ready.connect(self.show_report)
        self.worker.failed.connect(self.show_failure)
        self.worker.finished.connect(self.finish_validation)
        self.worker.start()

    def show_report(self, result):
        report, engine = result
        messages = [issue.message for issue in report.issues]
        if engine.status == "passed":
            messages.append(engine.message)
        else:
            messages.append(engine.message)
            if engine.details:
                messages.append("Details from OrcaSlicer:\n" + engine.details)
        if report.is_valid and engine.status == "passed":
            self.summary.setText("Ready to use: built-in and Orca engine checks passed.")
        elif report.is_valid:
            self.summary.setText("Built-in checks passed. See Orca engine status below.")
        else:
            self.summary.setText(f"{len(report.issues)} built-in issue(s) found. See results below.")
        self.results.setPlainText("\n\n".join(messages))

    def show_failure(self, message):
        self.summary.setText("Check could not finish")
        self.results.setPlainText(message)

    def finish_validation(self):
        self.worker.deleteLater()
        self.worker = None
        self.folder.setEnabled(True)
        self.browse.setEnabled(True)
        self.check.setEnabled(bool(self.folder.text().strip()))

    def closeEvent(self, event):
        if self.worker is not None or self.library.worker is not None:
            self.summary.setText("Please wait for the check to finish before closing.")
            if self.library.worker is not None:
                self.library.status.setText("Please wait for the download to finish before closing.")
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
