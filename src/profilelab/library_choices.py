# SPDX-License-Identifier: AGPL-3.0-only
"""Presentation-only exclusions for reviewed legacy entries in the pinned library."""

LEGACY_RE3D_FILAMENTS = frozenset({
    're3D PC', 're3D PETG', 're3D PLA', 're3D rPP', 're3D Greengate rPETG',
})


def selectable_library_records(records):
    """Keep the full catalog for resolution; never infer parenthood from names.

    Orca 2.4.2 marks these thin legacy entries as instantiated even though its
    nozzle-specific siblings contain the intended settings. Hide only this
    reviewed vendor/name set, and only when a selectable variant is present.
    Unrelated unsuffixed profiles remain available.
    """
    result = []
    for record in records:
        if record.get('template'):
            continue
        legacy = record.get('vendor') == 're3D' and record.get('type') == 'filament' and record['name'] in LEGACY_RE3D_FILAMENTS
        variants = legacy and any(other.get('vendor') == 're3D' and other.get('type') == 'filament'
                                  and not other.get('template') and not other.get('source_error')
                                  and other['name'].startswith(record['name'] + ' @') for other in records)
        if not variants:
            result.append(record)
    return result
