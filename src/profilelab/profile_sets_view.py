# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Mix-and-match workspace using frozen copies, not source-profile edits."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QListWidget, QInputDialog, QMessageBox, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QTabBar, QDialogButtonBox)
from profilelab.profile_sets import sets_home, new_set, save_set, load_sets, add_copy, prepare_set, review_set
from profilelab.library import read_snapshot, library_home
from profilelab.resolver import ProfileResolver, ResolutionError
from profilelab.drafts import load_drafts, drafts_home
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_sharing import share_prepared_package
from profilelab.package_preview import PackagePreview
from profilelab.setting_editor import SettingDialog, display_value, editable_value
from profilelab.scratch_dialog import ScratchDialog
from profilelab.library import VERSION
from profilelab.profile_picker import ProfilePicker
from profilelab.set_assignments import AssignmentsDialog
from profilelab.profile_sets import assignment_map
from profilelab.choice_combo import ChoiceComboBox as QComboBox, choose_text
from profilelab.library_choices import selectable_library_records


class ProfileSetsView(QWidget):
    def __init__(self, drafts_view, parent=None, root=None):
        super().__init__(parent)
        self.root = root or sets_home()
        self.drafts_view = drafts_view
        self.data = None
        self.member_indices = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(QLabel('My profile sets — mix, match, and customize'))
        self.status = QLabel('Choose profiles in any order. Copies are independent of library updates and original drafts.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.saved = QComboBox()
        self.saved.activated.connect(self.open_set)
        layout.addWidget(self.saved)
        self.steps = QTabBar()
        for title in ('1. Printers', '2. Filaments', '3. Processes', '4. Assignments and review'):
            self.steps.addTab(title)
        layout.addWidget(self.steps)
        actions = QHBoxLayout()
        for text, callback in [('New set', self.create), ('Create from scratch…', self.create_scratch), ('Add from library', self.add_library),
                               ('Add from drafts', self.add_draft)]:
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, fn=callback: self.run(fn))
            actions.addWidget(button)
        layout.addLayout(actions)
        package_actions = QHBoxLayout()
        for text, callback in [('Duplicate as variant…', self.duplicate), ('Remove selected', self.remove), ('Assign profiles and defaults…', self.defaults), ('Prepare and install…', self.package)]:
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, fn=callback: self.run(fn))
            package_actions.addWidget(button)
        layout.addLayout(package_actions)
        self.members = QListWidget()
        self.members.currentRowChanged.connect(self.show_profile)
        layout.addWidget(self.members)
        layout.addWidget(QLabel('Click a value to edit this copy. Setting names are read-only.'))
        self.values = QTableWidget(0, 2)
        self.values.setHorizontalHeaderLabels(['Setting', 'Value'])
        self.values.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.values.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.values.cellClicked.connect(lambda row, column: self.run(lambda: self.edit(row, column)))
        layout.addWidget(self.values)
        navigation = QHBoxLayout()
        self.back = QPushButton('Back')
        self.next = QPushButton('Next')
        self.back.clicked.connect(lambda: self.steps.setCurrentIndex(max(0, self.steps.currentIndex() - 1)))
        self.next.clicked.connect(lambda: self.steps.setCurrentIndex(min(3, self.steps.currentIndex() + 1)))
        navigation.addWidget(self.back)
        navigation.addStretch()
        navigation.addWidget(self.next)
        layout.addLayout(navigation)
        self.steps.currentChanged.connect(self.render)
        self.run(self.reload)

    def run(self, action):
        try:
            action()
        except Exception as error:
            QMessageBox.warning(self, 'Profile set', str(error))

    def reload(self):
        self.sets = load_sets(self.root)
        self.saved.clear()
        self.saved.addItem('Choose a saved set…')
        for item in self.sets:
            self.saved.addItem(item['name'])

    def open_set(self, index):
        if index > 0:
            self.data = deepcopy(self.sets[index - 1])
            self.render()

    def persist(self):
        save_set(self.root, self.data)
        self.reload()
        self.saved.setCurrentIndex(next(i + 1 for i, d in enumerate(self.sets) if d['id'] == self.data['id']))
        self.render()

    def render(self, *_):
        self.members.clear()
        self.member_indices = []
        self.back.setEnabled(self.steps.currentIndex() > 0)
        self.next.setEnabled(self.steps.currentIndex() < 3)
        if self.data is None:
            return
        kind = self.current_kind()
        for i, p in enumerate(self.data['profiles']):
            if kind and p['type'] != kind:
                continue
            self.member_indices.append(i)
            label = {'machine': 'Printer', 'filament': 'Filament', 'process': 'Process'}[p['type']]
            self.members.addItem(f"{p['name']} — {label}")
        self.status.setText(f"{self.data['name']} · Saved automatically. Incomplete sets can be reopened later.\nMixing profiles changes their compatibility links, not their physical suitability. Review temperatures, filament diameter, nozzle, extruder count, and G-code before use.")
        if kind is None:
            assignments = assignment_map(self.data)
            summaries = []
            for p in self.data['profiles']:
                if p['type'] == 'machine':
                    a = assignments.get(p['name'], {})
                    summaries.append(f"{p['name']}: {', '.join(a.get('filaments', [])) or 'No filaments assigned'} | {', '.join(a.get('processes', [])) or 'No processes assigned'}")
                    defaults = a.get('defaults', {})
                    slots = ', '.join(f'E{i}: {name or "Not selected"}' for i, name in enumerate(defaults.get('filaments', [])))
                    summaries.append(f"Defaults — {slots or 'Filaments not selected'}; process: {defaults.get('process') or 'Not selected'}")
            self.status.setText(self.status.text() + '\n' + '\n'.join(summaries))

    def current_kind(self):
        return ('machine', 'filament', 'process', None)[self.steps.currentIndex()]

    def selected_index(self):
        row = self.members.currentRow()
        return self.member_indices[row] if 0 <= row < len(self.member_indices) else -1

    def duplicate(self):
        index = self.selected_index()
        if index < 0:
            return
        profile = self.data['profiles'][index]
        name, ok = QInputDialog.getText(self, 'Duplicate as variant', 'Give the variant a unique name, then edit its nozzle size or dimensions:', text=profile['name'] + ' - Variant')
        if ok:
            source = self.data.get('sources', {}).get(profile['type'] + '/' + profile['name'])
            add_copy(self.data, profile['type'], name.strip(), profile, profile['version'], source=source)
            self.persist()
            self.members.setCurrentRow(self.members.count() - 1)

    def create(self):
        name, ok = QInputDialog.getText(self, 'New profile set', 'Set name:')
        if ok:
            self.data = new_set(name.strip())
            self.steps.setCurrentIndex(0)
            self.persist()

    def add(self, records, library=False):
        if self.data is None:
            raise ValueError('Create or open a set first.')
        recommendation_records = records
        if library:
            records = selectable_library_records(records)
        if self.current_kind():
            records = [r for r in records if r['type'] == self.current_kind()]
        labels = [f"{i+1}. {p['name']} — {p['type']} ({p.get('vendor', 'draft')})" for i, p in enumerate(records)]
        if not labels:
            raise ValueError('No profiles are available in this source yet.')
        if library or self.current_kind() in ('filament', 'process'):
            picker = ProfilePicker(records, self, multi=True, set_data=self.data, recommendation_records=recommendation_records)
            if self.current_kind():
                picker.category.setCurrentIndex(picker.category.findData(self.current_kind()))
                picker.category.setEnabled(False)
            if picker.exec() != QDialog.DialogCode.Accepted:
                return
            selected = picker.selected_records
        else:
            label, ok = choose_text(self, 'Choose a profile to copy — review suitability before printing', labels)
            if not ok:
                return
            record = records[labels.index(label)]
            selected = [record]
        if len(selected) > 1:
            preview = deepcopy(self.data)
            for record in selected:
                name = f"{record['name']} - {self.data['name']}"
                base, number = name, 2
                while any(p['type'] == record['type'] and p['name'].casefold() == name.casefold() for p in preview['profiles']):
                    name = f'{base} ({number})'
                    number += 1
                values, version = record['resolve']()
                source = dict(name=record['name'], vendor=record.get('vendor', ''), path=record.get('path', ''),
                              chain=record.get('source_chain', []), revision=record.get('source_revision', ''), version=version)
                add_copy(preview, record['type'], name, values, version, source=source)
            added = preview['profiles'][len(self.data['profiles']):]
            confirmation = QDialog(self)
            confirmation.setWindowTitle('Review selected copies')
            confirmation.resize(650, 440)
            layout = QVBoxLayout(confirmation)
            note = QLabel('Create these independent copies? Names include your set name; duplicates receive a number. '
                          'Next, confirm printer links in Assign profiles and defaults. No defaults are chosen automatically.')
            note.setWordWrap(True)
            layout.addWidget(note)
            names = QListWidget()
            names.addItems([p['name'] for p in added])
            layout.addWidget(names)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            buttons.button(QDialogButtonBox.StandardButton.Save).setText(f'Add {len(added)} copies')
            buttons.accepted.connect(confirmation.accept)
            buttons.rejected.connect(confirmation.reject)
            layout.addWidget(buttons)
            if confirmation.exec() != QDialog.DialogCode.Accepted:
                return
            save_set(self.root, preview)
            self.data = preview
            self.reload()
            self.saved.setCurrentIndex(next(i + 1 for i, d in enumerate(self.sets) if d['id'] == self.data['id']))
            self.render()
            return
        record = selected[0]
        name, ok = QInputDialog.getText(self, 'Name your independent copy', 'Profile name:', text=f"{record['name']} - {self.data['name']}")
        if ok:
            values, version = record['resolve']()
            source = None
            if library:
                source = dict(name=record['name'], vendor=record['vendor'], path=record['path'],
                              chain=record.get('source_chain', []), revision=record.get('source_revision', ''), version=version)
            add_copy(self.data, record['type'], name.strip(), values, version, source=source)
            self.persist()

    def add_library(self):
        snapshot = read_snapshot(library_home())
        if not snapshot:
            raise ValueError('Download the system library first.')
        resolver = ProfileResolver(snapshot['profiles'])
        records = []
        for p in snapshot['profiles']:
            if p['type'] in ('machine', 'filament', 'process') and not p['template']:
                # Group only by explicit, inherited metadata, never name suffixes.
                try:
                    resolved = resolver.resolve(p)
                    chain = [a['name'] for a in reversed(resolver.chain(p))]
                except ResolutionError as error:
                    # One broken library entry must not hide all valid choices.
                    records.append({**p, 'source_error': str(error),
                        'resolve': lambda p=p: ({k: deepcopy(v.value) for k, v in resolver.resolve(p).items()}, snapshot['metadata']['version'])})
                    continue
                values = {k: deepcopy(v.value) for k, v in resolved.items()}
                records.append({**p,
                    'values': values,
                    'source_revision': snapshot['metadata']['revision'],
                    'model': str(values.get('printer_model', '')) if p['type'] == 'machine' else '',
                    'variant': str(values.get('printer_variant', '')) if p['type'] == 'machine' else '',
                    'source_chain': chain,
                    'resolve': lambda values=values: (deepcopy(values), snapshot['metadata']['version'])})
        self.add(records, library=True)

    def create_scratch(self):
        if self.data is None:
            raise ValueError('Create or open a set first.')
        categories = {'Printer': 'machine', 'Filament': 'filament', 'Process': 'process'}
        if self.current_kind():
            label = next(label for label, kind in categories.items() if kind == self.current_kind())
        else:
            label, ok = QInputDialog.getItem(self, 'Create from scratch', 'Category:', list(categories), 0, False)
            if not ok:
                return
        dialog = ScratchDialog(categories[label], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            add_copy(self.data, categories[label], dialog.profile_name, dialog.result_values, VERSION)
            self.persist()

    def add_draft(self):
        drafts, errors = load_drafts(drafts_home())
        if errors:
            raise ValueError('Some drafts could not be read. Resolve them in My drafts first.')
        self.add([{**d, 'values': {**deepcopy(d['base_values']), **deepcopy(d['overrides'])}, 'resolve': lambda d=d: ({**deepcopy(d['base_values']), **deepcopy(d['overrides'])}, d['library']['version'])} for d in drafts])

    def remove(self):
        row = self.selected_index()
        if row < 0:
            return
        if QMessageBox.question(self, 'Remove copy?', 'Remove this copy from the set? Original profiles and installed files are unchanged.') == QMessageBox.StandardButton.Yes:
            removed = self.data['profiles'].pop(row)
            self.data.get('sources', {}).pop(removed['type'] + '/' + removed['name'], None)
            # Keep assignments so packaging identifies exactly what needs repair.
            self.persist()

    def defaults(self):
        if not self.data:
            return
        if not any(p['type'] == 'machine' for p in self.data['profiles']):
            raise ValueError('Add a printer first.')
        dialog = AssignmentsDialog(self.data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data['printer_assignments'] = dialog.assignments
            self.persist()

    def show_profile(self, row):
        self.values.setRowCount(0)
        if row < 0 or self.data is None:
            return
        profile = self.data['profiles'][self.member_indices[row]]
        self.keys = sorted(k for k in profile if k not in ('name', 'type', 'from', 'inherits', 'version', 'instantiation') and not k.endswith('_settings_id') and not k.startswith(('compatible_', 'default_')))
        self.values.setRowCount(len(self.keys))
        for i, key in enumerate(self.keys):
            self.values.setItem(i, 0, QTableWidgetItem(key.replace('_', ' ').capitalize()))
            self.values.setItem(i, 1, QTableWidgetItem(display_value(profile[key], key)))

    def edit(self, row, column):
        if column != 1:
            return
        profile = self.data['profiles'][self.selected_index()]
        key = self.keys[row]
        if not editable_value(profile[key]):
            return
        dialog = SettingDialog(key.replace('_', ' ').capitalize(), key, profile[key], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile[key] = dialog.value
            self.persist()

    def package(self):
        if not self.data:
            return
        profiles = prepare_set(self.data)
        warnings = review_set(self.data)
        if QMessageBox.warning(self, 'Review mixed-profile settings', '\n\n'.join(warnings) + '\n\nContinue to package review?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        if PackagePreview(profiles, self.data['name'], self).exec() != QDialog.DialogCode.Accepted:
            return
        folder = library_home().parent / 'sharing'
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"{self.data['name']}-{uuid4().hex[:8]}.orca_bundle"
        export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], destination)
        sharing = share_prepared_package(destination)
        self.status.setText(f'Ready to share: {sharing}\nImport this ZIP with File → Import → Import Configs.')
        self.drafts_view.last_package = destination
        if QMessageBox.question(self, 'Package ready', 'Install into OrcaSlicer now? Close Orca first.') == QMessageBox.StandardButton.Yes:
            self.drafts_view.install_package(str(destination))
