# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Native desktop validation window. Profile files are read only."""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from profilelab.orca_status import OrcaStatus, get_orca_status
from profilelab.validation import validate_folder
from profilelab.engine_validator import run_orca_engine, run_orca_engine_for_user_profiles, validation_engine_resources
from profilelab.engine_installer import install_engine
from profilelab.library import install_validation_resources, library_home
from profilelab.library_view import LibraryView
from profilelab.drafts_view import DraftsView
from profilelab.profile_sets_view import ProfileSetsView
from profilelab.demo import initialize_demo
from profilelab.desktop_theme import apply_theme
from profilelab import DISPLAY_VERSION
from profilelab.legal import LEGAL_SUMMARY, show_legal_information


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


def default_user_profile_folder() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    folder = Path(appdata) / "OrcaSlicer" / "user" / "default"
    return folder if folder.is_dir() else None


class ValidationWorker(QThread):
    result_ready = Signal(object)
    failed = Signal(str)

    progress = Signal(str)

    def __init__(self, folder: Path, user_profiles=False, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.user_profiles = user_profiles

    def run(self):
        try:
            report = validate_folder(self.folder)
            if self.user_profiles:
                # Orca's engine resolves parents from the system library. The local-only
                # check cannot, so let the engine be authoritative for those references.
                report.issues = [issue for issue in report.issues if issue.kind != "missing_parent"]
                self.progress.emit("Preparing a safe copy of your system profiles…")
                resources = validation_engine_resources()
                self.progress.emit("Checking your profiles with OrcaSlicer…")
                engine_result = run_orca_engine_for_user_profiles(resources, self.folder)
            else:
                engine_result = run_orca_engine(self.folder)
            self.result_ready.emit((report, engine_result))
        except (OSError, UnicodeError) as error:
            self.failed.emit(f"Could not read the profiles: {error}")
        except Exception as error:
            self.failed.emit(f"The check could not finish ({type(error).__name__}): {error}")


class EngineInstallWorker(QThread):
    progress = Signal(str)
    installed = Signal(str)
    failed = Signal(str)

    def run(self):
        try:
            installed = install_engine(self.progress.emit)
            self.installed.emit(str(installed))
        except Exception as error:
            self.failed.emit(f"The Orca engine could not be installed: {error}")


class MainWindow(QMainWindow):
    def __init__(self, demo_root=None):
        super().__init__()
        self.worker = None
        self.engine_worker = None
        self.demo_root = Path(demo_root) if demo_root is not None else None
        demo = initialize_demo(self.demo_root) if self.demo_root is not None else None
        self.setWindowTitle(f"Slicer Profile Lab — {DISPLAY_VERSION}")
        self.resize(1180, 800)
        self.setMinimumSize(920, 620)
        if demo:
            self.setWindowTitle("Slicer Profile Lab — Safe demo")
            banner = QLabel("  DEMO  ·  Fictional profiles  ·  Offline  ·  Your OrcaSlicer profiles stay unchanged")
            banner.setStyleSheet("padding: 10px; background: #244a61; color: #ffffff;")
            banner.setWordWrap(True)
            self.setMenuWidget(banner)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 28, 32, 28)
        help_menu = self.menuBar().addMenu('Help')
        legal_action = help_menu.addAction('License and source code')
        legal_action.triggered.connect(lambda: show_legal_information(self))
        if not demo:
            alpha_note = QLabel('ALPHA TEST BUILD · Back up your Orca profiles before testing. Review settings before printing.')
            alpha_note.setWordWrap(True)
            layout.addWidget(alpha_note)
            about = help_menu.addAction('About / testing information')
            about.triggered.connect(lambda: QMessageBox.information(self, 'About Slicer Profile Lab',
                f'Slicer Profile Lab {DISPLAY_VERSION}\nPublisher: WhereIsEggs\n\n'
                'Experimental Windows x64 build. Share Profile Lab ZIP files, not Orca re-exported bundles. '
                'Uninstalling the app preserves drafts, packages and Orca profiles.\n\n'
                'Report issues: https://github.com/WhereIsEggs/slicer-profile-lab/issues\n'
                'Include this version, your Orca version, steps and a sanitized example. '
                'Do not post private profiles or personal information.\n\n' + LEGAL_SUMMARY))
        layout.setSpacing(16)
        title = QLabel("Check your profile set")
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(title)
        intro = QLabel("Use Check my OrcaSlicer profiles for profiles saved by OrcaSlicer. "
                       "Choose a folder for a separate profile library.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        if demo:
            intro.setText("Try both examples to see how Profile Lab catches a broken inheritance link. These are real built-in checks on fictional data.")
            examples = QHBoxLayout()
            valid = QPushButton("Try a valid profile set")
            broken = QPushButton("Find a missing parent")
            valid.clicked.connect(lambda: self.check_demo_example("valid"))
            broken.clicked.connect(lambda: self.check_demo_example("missing-parent"))
            examples.addWidget(valid)
            examples.addWidget(broken)
            examples.addStretch()
            layout.addLayout(examples)

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
        self.check = QPushButton("Check selected folder")
        self.check.setEnabled(False)
        self.check.clicked.connect(self.start_validation)
        row.addWidget(self.check)
        self.check_my_profiles = QPushButton("Check my OrcaSlicer profiles")
        self.check_my_profiles.clicked.connect(self.start_user_validation)
        row.addWidget(self.check_my_profiles)
        self.install_engine = QPushButton("Install Orca engine")
        self.install_engine.clicked.connect(self.start_engine_install)
        row.addWidget(self.install_engine)
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
        note = QLabel("This check never changes files. Check my OrcaSlicer profiles uses system parents privately. "
                      "Passing checks does not guarantee print quality.")
        note.setWordWrap(True)
        layout.addWidget(note)
        tabs = QTabWidget()
        tabs.addTab(body, "Check profiles")
        self.library = LibraryView(self, root=self.demo_root / "library" if demo else None,
                                   draft_root=self.demo_root / "drafts" if demo else None, snapshot=demo)
        tabs.addTab(self.library, "System library")
        self.drafts = DraftsView(self, root=self.demo_root / "drafts" if demo else None, snapshot=demo,
                                package_root=self.demo_root / "packages" if demo else None, demo=bool(demo))
        tabs.addTab(self.drafts, "My drafts")
        if not demo:
            self.profile_sets = ProfileSetsView(self.drafts, self)
            tabs.addTab(self.profile_sets, "My profile sets")
        self.library.draft_created.connect(self.open_draft)
        self.setCentralWidget(tabs)
        self.refresh_status()
        if demo:
            self.check_my_profiles.hide()
            self.install_engine.hide()
            self.browse.hide()
            self.folder.setReadOnly(True)
            self.folder.hide()
            self.check.hide()
            refresh.hide()
            tabs.setCurrentWidget(self.library)
            self.library.kind.setCurrentIndex(self.library.kind.findData("machine"))
            self.library.search.setText("Demo Dual")
            if self.library.matches:
                self.library.table.selectRow(0)
            self.library.panel_splitter.setSizes([140, 380])

    def check_demo_example(self, name):
        if self.demo_root is None or self.worker is not None:
            return
        self.folder.setText(str(self.demo_root / "examples" / name))
        self.start_validation()

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
        if self.demo_root is not None:
            self.orca_label.setText("Safe demo workspace. No installation or download is needed.")
            return
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
        self.check_my_profiles.setEnabled(False)
        self.results.clear()
        self.summary.setText("Checking profiles with Profile Lab and OrcaSlicer…")
        self.worker = ValidationWorker(folder, parent=self)
        self.worker.result_ready.connect(self.show_report)
        self.worker.progress.connect(self.summary.setText)
        self.worker.failed.connect(self.show_failure)
        self.worker.finished.connect(self.finish_validation)
        self.worker.start()

    def start_user_validation(self):
        if self.demo_root is not None:
            return
        if self.worker is not None:
            return
        folder = default_user_profile_folder()
        if folder is None:
            self.summary.setText("Your normal OrcaSlicer profile folder was not found.")
            self.results.setPlainText("Choose a folder instead if your OrcaSlicer profiles are stored somewhere else.")
            return
        self.folder.setText(str(folder))
        self.folder.setEnabled(False)
        self.browse.setEnabled(False)
        self.check.setEnabled(False)
        self.check_my_profiles.setEnabled(False)
        self.results.clear()
        self.summary.setText("Preparing your OrcaSlicer profile check…")
        self.worker = ValidationWorker(folder, user_profiles=True, parent=self)
        self.worker.result_ready.connect(self.show_report)
        self.worker.progress.connect(self.summary.setText)
        self.worker.failed.connect(self.show_failure)
        self.worker.finished.connect(self.finish_validation)
        self.worker.start()

    def start_engine_install(self):
        if self.demo_root is not None:
            return
        if self.engine_worker is not None:
            return
        answer = QMessageBox.question(
            self,
            "Install Orca engine",
            "Profile Lab will download about 252 MB from OrcaSlicer's official GitHub release. "
            "It verifies published checksums and installs the files only in Profile Lab's private folder. "
            "It will not change OrcaSlicer or your profiles. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.install_engine.setEnabled(False)
        self.results.clear()
        self.summary.setText("Preparing the Orca engine installation…")
        self.engine_worker = EngineInstallWorker(self)
        self.engine_worker.progress.connect(self.summary.setText)
        self.engine_worker.installed.connect(self.show_engine_installed)
        self.engine_worker.failed.connect(self.show_failure)
        self.engine_worker.finished.connect(self.finish_engine_install)
        self.engine_worker.start()

    def show_engine_installed(self, installed):
        self.summary.setText("Orca engine installed and ready for profile checks.")
        self.results.setPlainText("The optional Orca engine was installed in Profile Lab's private folder.\n" + installed)

    def finish_engine_install(self):
        self.engine_worker.deleteLater()
        self.engine_worker = None
        self.install_engine.setEnabled(True)

    def show_report(self, result):
        report, engine = result
        if self.demo_root is not None:
            count = len(report.issues)
            self.summary.setText("Built-in checks passed" if report.is_valid else f"Found {count} profile {'problem' if count == 1 else 'problems'}")
            messages = []
            for issue in report.issues:
                message = issue.message
                for path in issue.paths:
                    message = message.replace(str(path), path.name)
                messages.append(message)
            self.results.setPlainText("\n\n".join(messages) if report.issues else
                                     "Both fictional profiles loaded and the child's parent was found.")
            self.results.append("\nDemo: these are Profile Lab's built-in checks, not full Orca validation or a print-quality test.")
            return
        messages = [issue.message for issue in report.issues]
        if engine.status == "passed":
            messages.append(engine.message)
        else:
            messages.append(engine.message)
            if engine.details:
                messages.append("Details from OrcaSlicer:\n" + engine.details)
        if report.is_valid and engine.status == "passed":
            self.summary.setText("Validation checks passed. Slicing and print quality are separate checks.")
        elif report.is_valid:
            self.summary.setText("Basic checks completed. Full validation is not confirmed; see details below.")
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
        self.check_my_profiles.setEnabled(True)

    def closeEvent(self, event):
        if self.worker is not None or self.engine_worker is not None or self.library.worker is not None or self.library.update_worker is not None:
            self.summary.setText("Please wait for the check to finish before closing.")
            if self.library.worker is not None:
                self.library.status.setText("Please wait for the download to finish before closing.")
            if self.library.update_worker is not None:
                self.library.status.setText("Please wait for the update check to finish before closing.")
            event.ignore()
        else:
            event.accept()


def main():
    parser = argparse.ArgumentParser(description="Slicer Profile Lab desktop")
    parser.add_argument("--demo", action="store_true", help="Start a safe fictional offline demonstration")
    parser.add_argument("--demo-root", type=Path, help="Optional separate demo workspace (requires --demo)")
    args = parser.parse_args()
    if args.demo_root and not args.demo:
        parser.error("--demo-root requires --demo")
    demo_root = args.demo_root
    if args.demo and demo_root is None:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
        demo_root = base / "SlicerProfileLab" / "demo" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    app = QApplication([sys.argv[0]])
    apply_theme(app)
    window = MainWindow(demo_root=demo_root)
    if demo_root is not None:
        window.showMaximized()
    else:
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
