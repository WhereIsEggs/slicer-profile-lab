# SPDX-License-Identifier: AGPL-3.0-only
"""Presentation-only exclusions for reviewed legacy entries in the pinned library."""

def selectable_library_records(records):
    """Keep selectable records; families organize legacy entries without hiding them."""
    return [r for r in records if not r.get('template')]


def filament_families(records):
    groups = {}
    for record in records:
        settings = record.get('settings', {})
        family = settings.get('filament_id')
        key = (record.get('vendor', ''), family) if isinstance(family, str) and family else ('individual', id(record))
        groups.setdefault(key, []).append(record)
    return list(groups.values())


def family_label(records):
    # Names only affect the label, never membership or compatibility.
    aliases = {r.get('settings', {}).get('alias') for r in records} - {None, ''}
    if len(aliases) == 1:
        return aliases.pop()
    return min((r['name'] for r in records), key=len).split(' @')[0]


def matching_variants(records, data):
    """Prefer the narrowest explicit printer link; never use diameter alone."""
    selected = set()
    for printer in data.get('profiles', []):
        if printer['type'] != 'machine':
            continue
        source = data.get('sources', {}).get('machine/' + printer['name'], {})
        identity = source.get('name', printer['name'])
        candidates = []
        for record in records:
            links = record.get('values', record.get('settings', {})).get('compatible_printers', [])
            if isinstance(links, list) and identity in links and not record.get('source_error') and (not source.get('vendor') or source['vendor'] == record.get('vendor')):
                candidates.append((record, set(links)))
        for record, links in candidates:
            if not any(other_links < links for _, other_links in candidates):
                selected.add(id(record))
    return selected
