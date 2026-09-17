# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Offline license and source access for source, wheel and frozen installations."""
from importlib.metadata import distribution, PackageNotFoundError
from pathlib import Path
import sys

LEGAL_SUMMARY = (
    'Copyright (C) 2026 WhereIsEggs (original contributions).\n'
    'GNU AGPL version 3 (AGPL-3.0-only).\n'
    'Provided WITHOUT ANY WARRANTY. You may modify and redistribute this '
    'program under the license. Upstream contributions retain their copyrights.'
)


def legal_root():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / 'LICENSE.txt').is_file():
        return checkout
    try:
        package = distribution('slicer-profile-lab')
        for file in package.files or []:
            if file.name == 'LICENSE.txt' and '.dist-info' in str(file):
                return Path(package.locate_file(file)).parent
    except PackageNotFoundError:
        pass
    return checkout


def show_legal_information(parent):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout
    root = legal_root()
    dialog = QDialog(parent)
    dialog.setWindowTitle('License and source code')
    dialog.resize(820, 650)
    layout = QVBoxLayout(dialog)
    summary = QLabel(LEGAL_SUMMARY)
    summary.setWordWrap(True)
    layout.addWidget(summary)
    source = QLabel('Matching release source: installed _internal/profilelab-source.zip and '
                    '_internal/dependency-sources, or the source ZIP beside your release download.\n'
                    'Source checkout: https://github.com/WhereIsEggs/slicer-profile-lab')
    source.setWordWrap(True)
    layout.addWidget(source)
    text = QTextBrowser()
    sections = []
    for name in ('LICENSE.txt', 'NOTICE.md'):
        path = root / name
        sections.append(path.read_text(encoding='utf-8') if path.is_file()
                        else f'{name} is missing. See https://github.com/WhereIsEggs/slicer-profile-lab')
    text.setPlainText('\n\n'.join(sections))
    layout.addWidget(text)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    open_files = buttons.addButton('Open license/source folder', QDialogButtonBox.ButtonRole.ActionRole)
    open_files.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(root))))
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()
