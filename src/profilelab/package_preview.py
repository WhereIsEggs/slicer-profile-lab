# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""A readable package summary: selected presets first, supporting ancestry second."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout


def package_groups(profiles):
    groups = {"Printers": [], "Filaments": [], "Processes": [], "Supporting parents": []}
    labels = {"machine": "Printers", "filament": "Filaments", "process": "Processes"}
    for profile in profiles:
        group = "Supporting parents" if profile.get("instantiation") == "false" else labels[profile["type"]]
        groups[group].append(profile["name"])
    return groups


class PackagePreview(QDialog):
    def __init__(self, profiles, title, parent=None, *, demo=False):
        super().__init__(parent)
        self.setWindowTitle("Review your package")
        self.resize(760, 530)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(heading)
        note = QLabel("Your selected profiles and the parents they need will travel together. Original profiles stay unchanged.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        for group, names in package_groups(profiles).items():
            if not names:
                continue
            item = QTreeWidgetItem([f"{group} · {len(names)}"])
            self.tree.addTopLevelItem(item)
            for name in names:
                item.addChild(QTreeWidgetItem([name]))
            item.setExpanded(group != "Supporting parents")
        layout.addWidget(self.tree, 1)
        explanation = QLabel("Supporting parents preserve inherited settings; they are not extra printers you chose. "
                             "Package structure has been checked. Full Orca validation and print quality are not certified.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        if demo:
            safety = QLabel("DEMO · Fictional profiles only. Saving does not install anything into OrcaSlicer.")
            safety.setWordWrap(True)
            layout.addWidget(safety)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Create package")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
