# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Read-only visual regression capture using the real cached library."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication
from profilelab.desktop_theme import apply_theme
from profilelab.library import library_home, read_snapshot
from profilelab.resolver import ProfileResolver
from profilelab.profile_picker import ProfilePicker


if __name__ == '__main__':
    app = QApplication([])
    apply_theme(app)
    snapshot = read_snapshot(library_home())
    resolver = ProfileResolver(snapshot['profiles'])
    records = []
    for record in snapshot['profiles']:
        if record['type'] != 'machine' or record['template'] or record['vendor'] != 're3D':
            continue
        resolved = resolver.resolve(record)
        records.append({**record,
            'model': resolved['printer_model'].value,
            'variant': resolved['printer_variant'].value,
            'source_chain': [p['name'] for p in reversed(resolver.chain(record))]})
    picker = ProfilePicker(records)
    picker.category.setCurrentIndex(1)
    picker.vendor.setCurrentIndex(picker.vendor.findData('re3D'))
    picker.table.selectRow(0)
    picker.show()
    app.processEvents()
    destination = Path(__file__).resolve().parents[1] / 'artifacts' / 'variant-comparison' / 'library-picker.png'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not picker.grab().save(str(destination)):
        raise RuntimeError('Could not save picker capture')
    print(destination)
    picker.close()
