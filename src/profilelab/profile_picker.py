# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Filter first, then choose a uniquely identified library record."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDialogButtonBox)
from profilelab.choice_combo import ChoiceComboBox as QComboBox


class ProfilePicker(QDialog):
    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.records = records
        self.selected_record = None
        self.setWindowTitle('Add from library')
        self.resize(850, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Choose a category, then search or filter by vendor. Original profiles stay unchanged.'))
        filters = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItem('Choose category…', '')
        for title, kind in [('Printers', 'machine'), ('Filaments', 'filament'), ('Processes', 'process')]:
            self.category.addItem(title, kind)
        filters.addWidget(self.category)
        self.vendor = QComboBox()
        self.vendor.setAccessibleName('Choose a vendor')
        self.vendor.addItem('All vendors', '')
        filters.addWidget(self.vendor)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search name, nozzle size, material…')
        self.search.setClearButtonEnabled(True)
        filters.addWidget(self.search, 1)
        layout.addLayout(filters)
        variants = QHBoxLayout()
        self.model = QComboBox()
        self.model.setAccessibleName('Choose a printer model')
        self.model.addItem('All printer models', '')
        self.nozzle = QComboBox()
        self.nozzle.setAccessibleName('Choose a nozzle variant')
        self.nozzle.addItem('All nozzle variants', '')
        variants.addWidget(self.model, 1)
        variants.addWidget(self.nozzle, 1)
        layout.addLayout(variants)
        self.count = QLabel()
        layout.addWidget(self.count)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Profile', 'Vendor'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
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
        self.model.currentIndexChanged.connect(self.nozzles_changed)
        self.nozzle.currentIndexChanged.connect(self.filter)
        self.search.textChanged.connect(self.filter)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.cellDoubleClicked.connect(lambda *_: self.accept_selected())
        self.filter()
        self.model.hide()
        self.nozzle.hide()

    def category_changed(self):
        self.vendor.blockSignals(True)
        self.vendor.clear()
        self.vendor.addItem('All vendors', '')
        for vendor in sorted({p.get('vendor', '') for p in self.records if p['type'] == self.category.currentData()}, key=str.casefold):
            if vendor:
                self.vendor.addItem(vendor, vendor)
        self.vendor.blockSignals(False)
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
        self.selected_record = None
        self.choose.setEnabled(False)
        self.table.setRowCount(0)
        self.details.setText('Select a profile to see its source and inherited settings.')
        kind, vendor = self.category.currentData(), self.vendor.currentData()
        model, variant = self.model.currentData(), self.nozzle.currentData()
        terms = self.search.text().casefold().split()
        self.matches = sorted((p for p in self.records if p['type'] == kind
                               and (not vendor or p.get('vendor') == vendor)
                               and (kind != 'machine' or not model or p.get('model') == model)
                               and (kind != 'machine' or not variant or p.get('variant') == variant)
                               and all(t in (p['name'] + ' ' + p.get('vendor', '')).casefold() for t in terms)),
                              key=lambda p: (p['name'].casefold(), p.get('vendor', '').casefold(), p.get('path', '')))
        self.table.setRowCount(len(self.matches))
        for row, p in enumerate(self.matches):
            item = QTableWidgetItem(p['name'])
            item.setToolTip(p.get('path', p['name']))
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem(p.get('vendor', '')))
        self.count.setText('Choose Printers, Filaments, or Processes to begin.' if not kind else
                           f'{len(self.matches)} profiles found' if self.matches else 'No matches. Try another search or vendor.')

    def selection_changed(self):
        self.choose.setEnabled(bool(self.table.selectedItems()))
        row = self.table.currentRow()
        if self.table.selectedItems() and 0 <= row < len(self.matches):
            p = self.matches[row]
            if p.get('source_error'):
                self.choose.setEnabled(False)
                self.details.setText('This profile has an unresolved source: ' + p['source_error'])
                return
            chain = p.get('source_chain', [])
            ancestry = ' → '.join(chain) if chain else 'No source chain available.'
            self.details.setText(f"{p['name']}\nSource: {p.get('vendor', '')}\n"
                                 f"Inheritance (base → selected): {ancestry}\n"
                                 'Your copy includes inherited values. Original library files stay unchanged.')

    def accept_selected(self):
        row = self.table.currentRow()
        if self.choose.isEnabled() and self.table.selectedItems() and 0 <= row < len(self.matches):
            self.selected_record = self.matches[row]
            self.accept()
