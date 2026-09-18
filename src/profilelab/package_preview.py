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
        links = QTreeWidgetItem(['Printer assignments and initial selections'])
        self.tree.addTopLevelItem(links)
        for printer in profiles:
            if printer['type'] != 'machine' or printer.get('instantiation') == 'false':
                continue
            node = QTreeWidgetItem([printer['name'] + ' — nozzles: ' + ' / '.join(map(str, printer.get('nozzle_diameter', []))) + ' mm'])
            links.addChild(node)
            for kind, title in [('filament', 'Available filaments'), ('process', 'Available processes')]:
                group = QTreeWidgetItem([title])
                node.addChild(group)
                for profile in profiles:
                    if profile['type'] == kind and printer['name'] in profile.get('compatible_printers', []):
                        group.addChild(QTreeWidgetItem([profile['name']]))
            defaults = printer.get('default_filament_profile', [])
            for i, name in enumerate(defaults if isinstance(defaults, list) else [defaults]):
                node.addChild(QTreeWidgetItem([f'Initial filament E{i}: {name}']))
            node.addChild(QTreeWidgetItem(['Initial process: ' + str(printer.get('default_print_profile', 'Not selected'))]))
        links.setExpanded(True)
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
