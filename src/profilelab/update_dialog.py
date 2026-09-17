# SPDX-License-Identifier: AGPL-3.0-only
"""Manual-only update dialog. Never launches an installer automatically."""
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout
from profilelab import __version__
from profilelab.app_updates import check_update, download_update, REPOSITORY


class UpdateWorker(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, update=None, parent=None):
        super().__init__(parent)
        self.update = update

    def run(self):
        try:
            self.result.emit(download_update(self.update, progress=self.progress.emit)
                             if self.update else check_update(__version__))
        except Exception as error:
            self.failed.emit(f'Could not complete the request. Check your connection and try again.\n{error}')


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Check for updates')
        self.resize(560, 280)
        self.worker = None
        self.update = None
        self.downloaded = None
        layout = QVBoxLayout(self)
        note = QLabel(f'Installed version: {__version__}\nChecks run only when you click Check now. '
                      'There are no automatic checks, downloads or installations.\n'
                      'Preview versions receive alpha/beta updates too.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel('Ready to check GitHub for a newer Windows installer.')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.check = QPushButton('Check now')
        self.check.clicked.connect(lambda: self.start())
        layout.addWidget(self.check)
        self.download = QPushButton('Download update')
        self.download.setEnabled(False)
        self.download.clicked.connect(lambda: self.start(self.update))
        layout.addWidget(self.download)
        self.open_folder = QPushButton('Open downloaded installer folder')
        self.open_folder.hide()
        self.open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.downloaded.parent))))
        layout.addWidget(self.open_folder)
        release = QPushButton('View releases and source code on GitHub')
        release.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPOSITORY + '/releases')))
        layout.addWidget(release)

    def start(self, update=None):
        if self.worker is not None:
            return
        self.check.setEnabled(False)
        self.download.setEnabled(False)
        self.open_folder.hide()
        self.status.setText('Downloading and verifying…' if update else 'Checking GitHub…')
        self.worker = UpdateWorker(update, self)
        self.worker.result.connect(self.download_ready if update else self.check_ready)
        self.worker.failed.connect(self.status.setText)
        self.worker.progress.connect(lambda size: self.status.setText(f'Downloading… {size // (1024 * 1024)} MB'))
        self.worker.finished.connect(self.finished_work)
        self.worker.start()

    def check_ready(self, update):
        self.update = update
        self.status.setText(f'{update.tag} is available. Click Download update to save its installer.' if update else
                            'No newer compatible release with an installer and checksums was found.')

    def download_ready(self, path):
        self.downloaded = path
        self.status.setText('Download verified. Open the folder, close Profile Lab, then run the installer. '
                            'Nothing has been installed automatically. Windows security checks still apply.')
        self.open_folder.show()

    def finished_work(self):
        self.worker.deleteLater()
        self.worker = None
        self.check.setEnabled(True)
        self.download.setEnabled(self.update is not None)

    def reject(self):
        if self.worker is None:
            super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
