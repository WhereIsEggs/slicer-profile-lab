# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Per-printer compatibility and defaults; all changes commit together."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QComboBox, QFormLayout, QDialogButtonBox, QScrollArea)
from profilelab.profile_sets import assignment_map
from profilelab.choice_combo import ChoiceComboBox as QComboBox


class AssignmentsDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Assign profiles to each printer')
        self.resize(760, 680)
        self.pages = []
        self.assignments = None
        layout = QVBoxLayout(self)
        note = QLabel('Check which materials and processes belong to each printer, then choose its defaults. A profile can support several printers. Unchecked profiles will not be linked to that printer.')
        note.setWordWrap(True)
        layout.addWidget(note)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        saved = assignment_map(data)
        for printer in (p for p in data['profiles'] if p['type'] == 'machine'):
            choice = saved.get(printer['name'], {})
            body = QWidget()
            form = QFormLayout(body)
            form.addRow(QLabel('Nozzles: ' + ' / '.join(printer.get('nozzle_diameter', [])) + ' mm'))
            lists = {}
            for field, kind in [('filaments', 'filament'), ('processes', 'process')]:
                widget = QListWidget()
                widget.setMaximumHeight(140)
                for profile in data['profiles']:
                    if profile['type'] != kind:
                        continue
                    item = QListWidgetItem(profile['name'])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Checked if profile['name'] in choice.get(field, []) else Qt.CheckState.Unchecked)
                    widget.addItem(item)
                lists[field] = widget
                form.addRow(field.capitalize(), widget)
            slots = []
            for i in range(len(printer.get('nozzle_diameter', []))):
                combo = QComboBox()
                slots.append(combo)
                label = ('E0 / Left', 'E1 / Right')[i] if i < 2 else f'E{i}'
                form.addRow('Default filament — ' + label, combo)
            process = QComboBox()
            form.addRow('Default process', process)
            page = dict(name=printer['name'], lists=lists, slots=slots, process=process)
            self.pages.append(page)
            self.refresh_defaults(page)
            defaults = choice.get('defaults', {})
            for combo, value in zip(slots, defaults.get('filaments', [])):
                combo.setCurrentIndex(max(0, combo.findData(value)))
            process.setCurrentIndex(max(0, process.findData(defaults.get('process'))))
            for widget in lists.values():
                widget.itemChanged.connect(lambda item, page=page: self.refresh_defaults(page))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(body)
            tabs.addTab(scroll, printer['name'])
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def checked(widget):
        return [widget.item(i).text() for i in range(widget.count()) if widget.item(i).checkState() == Qt.CheckState.Checked]

    def refresh_defaults(self, page):
        for field, combos in [('filaments', page['slots']), ('processes', [page['process']])]:
            names = self.checked(page['lists'][field])
            for combo in combos:
                old = combo.currentData()
                combo.clear()
                combo.addItem('Choose a default…', '')
                for name in names:
                    combo.addItem(name, name)
                combo.setCurrentIndex(max(0, combo.findData(old)))

    def save(self):
        self.assignments = {p['name']: {
            **{field: self.checked(widget) for field, widget in p['lists'].items()},
            'defaults': {'filaments': [c.currentData() for c in p['slots']], 'process': p['process'].currentData()},
        } for p in self.pages}
        self.accept()
