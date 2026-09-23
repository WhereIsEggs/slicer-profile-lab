# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Filter first, then choose a uniquely identified library record."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDialogButtonBox, QCheckBox, QTreeWidget, QTreeWidgetItem)
from profilelab.choice_combo import ChoiceComboBox as QComboBox


def filament_brands(record):
    """Use resolved print settings, not the bundle owner or product name."""
    if record['type'] != 'filament':
        return []
    value = record.get('values', record.get('settings', {})).get('filament_vendor', [])
    if isinstance(value, str):
        value = [value]
    return sorted({v.strip() for v in value if isinstance(v, str) and v.strip()}, key=str.casefold) if isinstance(value, list) else []


def printer_scope(record):
    """Describe stored restrictions, not an assertion of physical suitability."""
    if record.get('source_error'):
        return 'Printer restrictions unresolved'
    values = record.get('values', record.get('settings', {}))
    links = values.get('compatible_printers', [])
    condition = values.get('compatible_printers_condition', '')
    if not isinstance(links, list) or not isinstance(condition, str):
        return 'Printer restrictions need review'
    if links:
        return 'Linked to specific printers' + ('; conditional restriction' if condition.strip() else '')
    if condition.strip():
        return 'Conditional printer restriction'
    return 'No explicit printer restriction'


class ProfilePicker(QDialog):
    def __init__(self, records, parent=None, *, multi=False, set_data=None, recommendation_records=None):
        super().__init__(parent)
        self.records = records
        self.selected_record = None
        self.selected_records = []
        self.multi = multi
        self.checked = set()
        self.set_data = set_data or {}
        from profilelab.recommendations import recommendation
        self.reasons = {id(r): recommendation(r, set_data or {}, recommendation_records or records) for r in records}
        self.setWindowTitle('Add from library')
        self.resize(850, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Search by name or filament brand; profile source identifies the library bundle. Originals stay unchanged.'))
        filters = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItem('Choose category…', '')
        for title, kind in [('Printers', 'machine'), ('Filaments', 'filament'), ('Processes', 'process')]:
            self.category.addItem(title, kind)
        filters.addWidget(self.category)
        self.vendor = QComboBox()
        self.vendor.setAccessibleName('Profile source')
        self.vendor.addItem('All profile sources', '')
        filters.addWidget(self.vendor)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search name, nozzle size, material…')
        self.search.setClearButtonEnabled(True)
        filters.addWidget(self.search, 1)
        layout.addLayout(filters)
        variants = QHBoxLayout()
        self.brand = QComboBox()
        self.brand.setAccessibleName('Filament brand')
        self.brand.addItem('All filament brands', '')
        self.brand.setToolTip('Filament manufacturer, including values inherited from parent profiles.')
        variants.addWidget(self.brand)
        self.location = QComboBox()
        self.location.setAccessibleName('Library location')
        self.location.addItem('All library locations', '')
        self.location.addItem('Shared filament library', 'shared')
        self.location.addItem('Printer-vendor libraries', 'printer')
        self.location.setToolTip('Where the file is stored, not which printers it supports.')
        variants.addWidget(self.location)
        self.model = QComboBox()
        self.model.setAccessibleName('Choose a printer model')
        self.model.addItem('All printer models', '')
        self.nozzle = QComboBox()
        self.nozzle.setAccessibleName('Choose a nozzle variant')
        self.nozzle.addItem('All nozzle variants', '')
        variants.addWidget(self.model, 1)
        variants.addWidget(self.nozzle, 1)
        layout.addLayout(variants)
        self.recommended = QCheckBox('Recommended only — based on this set')
        self.recommended.setEnabled(bool(set_data and set_data.get('profiles')))
        self.recommended.toggled.connect(self.filter)
        layout.addWidget(self.recommended)
        self.group_families = QCheckBox('Group filament families — expand to inspect exact profiles')
        self.group_families.setChecked(True)
        self.group_families.toggled.connect(self.filter)
        layout.addWidget(self.group_families)
        hint = QLabel('Check several filaments or processes; printers are added one at a time. '
                      'Recommendations explain existing links or diameter matches, not print safety. Other choices remain available.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.count = QLabel()
        layout.addWidget(self.count)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Profile', 'Profile source', 'Recommendation / why'])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        self.family_tree = QTreeWidget()
        self.family_tree.setHeaderLabels(['Material family / exact profile', 'Profile source', 'Selection guidance'])
        self.family_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.family_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.family_tree.setAlternatingRowColors(True)
        self.family_tree.itemChanged.connect(self.family_checked)
        layout.addWidget(self.family_tree)
        self.details = QLabel('Select a profile to see its source and inherited settings.')
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.details)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.choose = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.choose.setText('Use selected profile')
        self.choose.setEnabled(False)
        buttons.accepted.connect(self.accept_selected)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.category.currentIndexChanged.connect(self.category_changed)
        self.vendor.currentIndexChanged.connect(self.models_changed)
        self.brand.currentIndexChanged.connect(self.filter)
        self.location.currentIndexChanged.connect(self.filter)
        self.model.currentIndexChanged.connect(self.nozzles_changed)
        self.nozzle.currentIndexChanged.connect(self.filter)
        self.search.textChanged.connect(self.filter)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.itemChanged.connect(self.check_changed)
        self.table.cellDoubleClicked.connect(lambda *_: self.accept_selected())
        self.filter()
        self.model.hide()
        self.nozzle.hide()
        self.brand.hide()
        self.location.hide()

    def category_changed(self):
        self.checked.clear()
        self.vendor.blockSignals(True)
        self.vendor.clear()
        self.vendor.addItem('All profile sources', '')
        for vendor in sorted({p.get('vendor', '') for p in self.records if p['type'] == self.category.currentData()}, key=str.casefold):
            if vendor:
                self.vendor.addItem(vendor, vendor)
        self.vendor.blockSignals(False)
        self.brand.blockSignals(True)
        self.brand.clear()
        self.brand.addItem('All filament brands', '')
        for brand in sorted({b for p in self.records for b in filament_brands(p)}, key=str.casefold):
            self.brand.addItem(brand, brand)
        self.brand.blockSignals(False)
        self.brand.setVisible(self.category.currentData() == 'filament')
        self.location.blockSignals(True)
        self.location.setCurrentIndex(0)
        self.location.blockSignals(False)
        self.location.setVisible(self.category.currentData() == 'filament')
        self.models_changed()

    def models_changed(self):
        machine = self.category.currentData() == 'machine'
        self.model.setVisible(machine)
        self.nozzle.setVisible(machine)
        self.model.blockSignals(True)
        self.model.clear()
        self.model.addItem('All printer models', '')
        vendor = self.vendor.currentData()
        for name in sorted({p.get('model', '') for p in self.records
                            if p['type'] == 'machine' and (not vendor or p.get('vendor') == vendor)}):
            if name:
                self.model.addItem(name, name)
        self.model.blockSignals(False)
        self.nozzles_changed()

    def nozzles_changed(self):
        self.nozzle.blockSignals(True)
        self.nozzle.clear()
        self.nozzle.addItem('All nozzle variants', '')
        vendor, model = self.vendor.currentData(), self.model.currentData()
        for value in sorted({p.get('variant', '') for p in self.records
                             if p['type'] == 'machine' and (not vendor or p.get('vendor') == vendor)
                             and (not model or p.get('model') == model)}):
            if value:
                self.nozzle.addItem(value, value)
        self.nozzle.blockSignals(False)
        self.filter()

    def filter(self):
        self.table.blockSignals(True)
        self.selected_record = None
        self.choose.setEnabled(False)
        self.table.setRowCount(0)
        self.details.setText('Select a profile to see its source and inherited settings.')
        kind, vendor = self.category.currentData(), self.vendor.currentData()
        brand = self.brand.currentData() if kind == 'filament' else ''
        location = self.location.currentData() if kind == 'filament' else ''
        model, variant = self.model.currentData(), self.nozzle.currentData()
        terms = self.search.text().casefold().split()
        self.matches = sorted((p for p in self.records if p['type'] == kind
                               and (not vendor or p.get('vendor') == vendor)
                               and (not brand or brand in filament_brands(p))
                               and (not location or (p.get('vendor') == 'OrcaFilamentLibrary' if location == 'shared'
                                                     else bool(p.get('vendor')) and p.get('vendor') != 'OrcaFilamentLibrary'))
                               and (kind != 'machine' or not model or p.get('model') == model)
                               and (kind != 'machine' or not variant or p.get('variant') == variant)
                               and (not self.recommended.isChecked() or self.reasons[id(p)])
                               and all(t in (p['name'] + ' ' + p.get('vendor', '') + ' ' + ' '.join(filament_brands(p))).casefold() for t in terms)),
                              key=lambda p: (not bool(self.reasons[id(p)]), p['name'].casefold(), p.get('vendor', '').casefold(), p.get('path', '')))
        self.table.setRowCount(len(self.matches))
        for row, p in enumerate(self.matches):
            item = QTableWidgetItem(p['name'])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            item.setToolTip(p.get('path', p['name']) + '\nFilament brand: ' + (', '.join(filament_brands(p)) or 'Not specified'))
            if self.multi and kind in ('filament', 'process') and not p.get('source_error'):
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if id(p) in self.checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem(p.get('vendor', '')))
            reason = QTableWidgetItem('; '.join(self.reasons[id(p)]) or 'No verified recommendation — manual review')
            if kind == 'filament':
                reason.setText(printer_scope(p) + ' — ' + reason.text())
            reason.setToolTip(reason.text())
            self.table.setItem(row, 2, reason)
        self.table.blockSignals(False)
        self.update_selection_count()
        self.count.setText('Choose Printers, Filaments, or Processes to begin.' if not kind else
                           f'{len(self.matches)} profiles found' if self.matches else 'No matches. Try another search, brand, location, or profile source.')
        grouped = self.multi and kind == 'filament' and self.group_families.isChecked()
        self.group_families.setVisible(self.multi and kind == 'filament')
        self.table.setVisible(not grouped)
        self.family_tree.setVisible(grouped)
        if grouped:
            self.render_families()

    def render_families(self):
        from profilelab.library_choices import filament_families, family_label, matching_variants
        self.family_tree.blockSignals(True)
        self.family_tree.clear()
        groups = filament_families(self.matches)
        full_groups = {id(r): family for family in filament_families([r for r in self.records if r['type'] == 'filament']) for r in family}
        for records in groups:
            targets = matching_variants(full_groups[id(records[0])], self.set_data) & {id(r) for r in records}
            parent = QTreeWidgetItem([f'{family_label(records)} · {len(records)} profiles', records[0].get('vendor', ''),
                                     f'{len(targets)} explicitly linked variants; expand to review' if targets else 'Expand and choose variants manually'])
            parent.setData(0, Qt.ItemDataRole.UserRole, list(targets))
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self.family_tree.addTopLevelItem(parent)
            if targets:
                parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                selected = targets & self.checked
                parent.setCheckState(0, Qt.CheckState.Checked if selected == targets else Qt.CheckState.PartiallyChecked if selected else Qt.CheckState.Unchecked)
            for record in records:
                child = QTreeWidgetItem([record['name'], record.get('vendor', ''), '; '.join(self.reasons[id(record)]) or 'Manual review'])
                child.setText(2, printer_scope(record) + '\n' + child.text(2))
                child.setData(0, Qt.ItemDataRole.UserRole, id(record))
                child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                child.setToolTip(0, 'Exact profile: ' + record['name'] + '\nSource chain: ' + ' → '.join(record.get('source_chain', [])))
                child.setToolTip(0, child.toolTip(0) + '\nFilament brand: ' + (', '.join(filament_brands(record)) or 'Not specified'))
                child.setToolTip(2, child.text(2))
                parent.addChild(child)
                if not record.get('source_error'):
                    child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.CheckState.Checked if id(record) in self.checked else Qt.CheckState.Unchecked)
            parent.setExpanded(bool(self.search.text()))
        self.family_tree.blockSignals(False)
        self.count.setText(f'{len(groups)} material families · {len(self.matches)} exact profiles')

    def family_checked(self, item, column):
        if column != 0:
            return
        target = item.data(0, Qt.ItemDataRole.UserRole)
        ids = set(target) if isinstance(target, list) else {target}
        if item.checkState(0) == Qt.CheckState.Checked:
            self.checked.update(ids)
        else:
            self.checked.difference_update(ids)
        # Synchronize children/parent states without rebuilding the active item.
        self.family_tree.blockSignals(True)
        for i in range(self.family_tree.topLevelItemCount()):
            parent = self.family_tree.topLevelItem(i)
            targets = set(parent.data(0, Qt.ItemDataRole.UserRole))
            if targets:
                chosen = targets & self.checked
                parent.setCheckState(0, Qt.CheckState.Checked if chosen == targets else Qt.CheckState.PartiallyChecked if chosen else Qt.CheckState.Unchecked)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    child.setCheckState(0, Qt.CheckState.Checked if child.data(0, Qt.ItemDataRole.UserRole) in self.checked else Qt.CheckState.Unchecked)
        self.family_tree.blockSignals(False)
        self.update_selection_count()

    def selection_changed(self):
        multiple = self.multi and self.category.currentData() in ('filament', 'process')
        if multiple:
            self.update_selection_count()
        else:
            self.choose.setEnabled(bool(self.table.selectedItems()))
        row = self.table.currentRow()
        if self.table.selectedItems() and 0 <= row < len(self.matches):
            p = self.matches[row]
            if p.get('source_error'):
                if not multiple:
                    self.choose.setEnabled(False)
                self.details.setText('This profile has an unresolved source: ' + p['source_error'])
                return
            chain = p.get('source_chain', [])
            ancestry = ' → '.join(chain) if chain else 'No source chain available.'
            self.details.setText(f"{p['name']}\nSource: {p.get('vendor', '')}\n"
                                 f"Inheritance (base → selected): {ancestry}\n"
                                 'Your copy includes inherited values. Original library files stay unchanged.\n'
                                 + '; '.join(self.reasons[id(p)]))

    def accept_selected(self):
        if self.multi and self.category.currentData() in ('filament', 'process'):
            self.selected_records = [r for r in self.records if id(r) in self.checked and not r.get('source_error')]
            if self.selected_records:
                self.selected_record = self.selected_records[0]
                self.accept()
            return
        row = self.table.currentRow()
        if self.choose.isEnabled() and self.table.selectedItems() and 0 <= row < len(self.matches):
            self.selected_record = self.matches[row]
            self.selected_records = [self.selected_record]
            self.accept()

    def check_changed(self, item):
        if item.column() != 0 or not self.multi or self.category.currentData() == 'machine':
            return
        record = self.matches[item.row()]
        if item.checkState() == Qt.CheckState.Checked:
            self.checked.add(id(record))
        else:
            self.checked.discard(id(record))
        self.update_selection_count()

    def update_selection_count(self):
        if self.multi and self.category.currentData() in ('filament', 'process'):
            self.choose.setText(f'Add {len(self.checked)} selected profiles')
            self.choose.setEnabled(bool(self.checked))
            self.details.setText(f'{len(self.checked)} selected across all filters. Uncheck a profile to remove it; Cancel adds nothing.')
        else:
            self.choose.setText('Use selected profile')
