# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Independent, frozen profile sets. Never writes to Orca's data folders."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4
import math

from profilelab.library import library_home
from profilelab.profile_install import IDENTITIES, _safe_name


def sets_home():
    return library_home().parent / 'sets'


def new_set(name):
    _safe_name(name)
    return dict(id=str(uuid4()), name=name, format_version=1, profiles=[], defaults={})


def save_set(root, data):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / (str(UUID(data['id'])) + '.json')
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, suffix='.tmp', delete=False) as file:
        temporary = Path(file.name)
        try:
            json.dump(data, file, ensure_ascii=False, allow_nan=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_sets(root):
    result = []
    for path in sorted(Path(root).glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('format_version') != 1 or str(UUID(data['id'])) != path.stem:
            raise ValueError(f'Invalid saved set: {path.name}')
        result.append(data)
    return result


def delete_set(root, original):
    """Move one unchanged saved set to a recoverable backup; never touch exports."""
    root = Path(root).resolve()
    source = root / (str(UUID(original['id'])) + '.json')
    if source.resolve() != source:
        raise ValueError('Linked set files are not supported.')
    if json.loads(source.read_text(encoding='utf-8')) != original:
        raise ValueError('This set changed since it was opened. Reopen it before deleting.')
    backup_root = root / 'deleted'
    if backup_root.resolve() != backup_root:
        raise ValueError('Linked backup folders are not supported.')
    backup_root.mkdir(exist_ok=True)
    # A unique directory preserves the original UUID filename for manual restore.
    destination = backup_root / uuid4().hex
    destination.mkdir()
    backup = destination / source.name
    try:
        source.rename(backup)
    except Exception:
        destination.rmdir()
        raise
    return backup


def add_copy(data, kind, name, values, version, source=None):
    _safe_name(name)
    if kind not in IDENTITIES:
        raise ValueError('Select a printer variant, filament, or process.')
    if any(p['type'] == kind and p['name'].casefold() == name.casefold() for p in data['profiles']):
        raise ValueError('Choose a unique profile name in this category.')
    # Preserve a legacy single-printer set's choices before adding another printer.
    if kind == 'machine' and any(p['type'] == kind for p in data['profiles']):
        data.setdefault('printer_assignments', assignment_map(data))
    profile = deepcopy(values)
    for key in ('inherits', 'setting_id', 'settings_id', 'alias', 'renamed_from', *IDENTITIES.values()):
        profile.pop(key, None)
    profile.update(name=name, type=kind, version=version, inherits='', instantiation='true')
    profile['from'] = 'User'
    profile[IDENTITIES[kind]] = [name] if kind == 'filament' else name
    data['profiles'].append(profile)
    # Provenance belongs to the saved project, never to Orca's profile schema.
    key = kind + '/' + name
    data.setdefault('sources', {}).pop(key, None)
    if source is not None:
        data['sources'][key] = deepcopy(source)


def assignment_map(data):
    """Read old single-printer defaults without modifying the saved set."""
    if 'printer_assignments' in data:
        return deepcopy(data['printer_assignments'])
    printers = [p for p in data['profiles'] if p['type'] == 'machine']
    if len(printers) != 1:
        return {}
    return {printers[0]['name']: {
        'filaments': [p['name'] for p in data['profiles'] if p['type'] == 'filament'],
        'processes': [p['name'] for p in data['profiles'] if p['type'] == 'process'],
        'defaults': deepcopy(data.get('defaults', {})),
    }}


def rename_profile(data, index, name):
    _safe_name(name)
    profile = data['profiles'][index]
    kind, old = profile['type'], profile['name']
    if any(i != index and p['type'] == kind and p['name'].casefold() == name.casefold() for i, p in enumerate(data['profiles'])):
        raise ValueError('Choose a unique profile name in this category.')
    assignments = assignment_map(data)
    if kind == 'machine' and old in assignments:
        assignments[name] = assignments.pop(old)
    field = {'filament': 'filaments', 'process': 'processes'}.get(kind)
    for choice in assignments.values():
        if field:
            choice[field] = [name if n == old else n for n in choice.get(field, [])]
        defaults = choice.get('defaults', {})
        if kind == 'filament':
            defaults['filaments'] = [name if n == old else n for n in defaults.get('filaments', [])]
        elif kind == 'process' and defaults.get('process') == old:
            defaults['process'] = name
    data['printer_assignments'] = assignments
    sources = data.get('sources', {})
    if kind + '/' + old in sources:
        sources[kind + '/' + name] = sources.pop(kind + '/' + old)
    profile['name'] = name
    profile[IDENTITIES[kind]] = [name] if kind == 'filament' else name


def set_readiness(data):
    """Collect actionable assignment gaps without modifying an incomplete set."""
    issues = []
    profiles = data['profiles']
    printers = [p for p in profiles if p['type'] == 'machine']
    available = {kind: {p['name'] for p in profiles if p['type'] == kind} for kind in ('filament', 'process')}
    for kind, title in [('machine', 'printer'), ('filament', 'filament'), ('process', 'process')]:
        if not any(p['type'] == kind for p in profiles):
            issues.append(f'Add at least one {title}.')
    assignments = assignment_map(data)
    for printer in printers:
        name = printer['name']
        choice = assignments.get(name, {})
        nozzles = printer.get('nozzle_diameter', [])
        try:
            valid = isinstance(nozzles, list) and bool(nozzles) and all(math.isfinite(float(n)) and float(n) > 0 for n in nozzles)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            issues.append(f'{name}: set a positive nozzle diameter for each extruder.')
        for field, kind in [('filaments', 'filament'), ('processes', 'process')]:
            selected = choice.get(field, [])
            if not selected or any(n not in available[kind] for n in selected):
                issues.append(f'{name}: assign valid {field}.')
        defaults = choice.get('defaults', {})
        slots = defaults.get('filaments', [])
        if valid:
            for i in range(len(nozzles)):
                if i >= len(slots) or slots[i] not in choice.get('filaments', []):
                    issues.append(f'{name}: choose a default filament for E{i}.')
            if len(slots) > len(nozzles):
                issues.append(f'{name}: remove defaults for extruders no longer present.')
        if not defaults.get('process') or defaults['process'] not in choice.get('processes', []):
            issues.append(f'{name}: choose an assigned default process.')
    for kind, field in [('filament', 'filaments'), ('process', 'processes')]:
        for name in sorted(available[kind]):
            if printers and not any(name in assignments.get(p['name'], {}).get(field, []) for p in printers):
                issues.append(f'{name}: assign to a printer or remove this copy.')
    return issues


def prepare_set(data):
    from profilelab.printer_templates import sync_nozzle_variant
    profiles = deepcopy(data['profiles'])
    printers = [p for p in profiles if p['type'] == 'machine']
    filaments = [p for p in profiles if p['type'] == 'filament']
    processes = [p for p in profiles if p['type'] == 'process']
    if not printers or not filaments or not processes:
        raise ValueError('Add at least one printer, filament, and process before packaging.')
    assignments = assignment_map(data)
    for printer in printers:
        name = printer['name']
        choice = assignments.get(name, {})
        nozzles = printer.get('nozzle_diameter', [])
        if not isinstance(nozzles, list) or not nozzles:
            raise ValueError(f'{name}: set a nozzle diameter for every extruder.')
        try:
            valid_nozzles = all(math.isfinite(float(v)) and float(v) > 0 for v in nozzles)
        except (TypeError, ValueError):
            valid_nozzles = False
        if not valid_nozzles:
            raise ValueError(f'{name}: nozzle diameters must be positive numbers.')
        sync_nozzle_variant(printer)
        for field, available in [('filaments', filaments), ('processes', processes)]:
            names = choice.get(field, [])
            if not isinstance(names, list) or not names or any(n not in [p['name'] for p in available] for n in names):
                raise ValueError(f'{name}: choose valid {field} in Assignments and review.')
        defaults = choice.get('defaults', {})
        slots = defaults.get('filaments', [])
        process = defaults.get('process')
        if len(slots) != len(nozzles) or any(n not in choice['filaments'] for n in slots):
            raise ValueError(f'{name}: select an assigned default filament for every extruder.')
        if process not in choice['processes']:
            raise ValueError(f'{name}: select an assigned default process.')
        printer['default_filament_profile'] = slots
        printer['default_print_profile'] = process
    for profile in filaments + processes:
        field = 'filaments' if profile['type'] == 'filament' else 'processes'
        profile['compatible_printers'] = [p['name'] for p in printers if profile['name'] in assignments[p['name']][field]]
        if not profile['compatible_printers']:
            raise ValueError(f"{profile['name']}: assign this profile to at least one printer or remove it from the set.")
        profile['compatible_printers_condition'] = ''
        if profile['type'] == 'filament':
            profile['compatible_prints'] = []
            profile['compatible_prints_condition'] = ''
        else:
            profile.pop('compatible_prints', None)
            profile.pop('compatible_prints_condition', None)
    return profiles


def review_set(data):
    """Non-blocking checks on explicit values; never infer hardware safety."""
    def numbers(value):
        values = value if isinstance(value, list) else [value]
        try:
            result = [float(v) for v in values]
            return result if result and all(math.isfinite(v) and v > 0 for v in result) else []
        except (ValueError, TypeError):
            return []

    warnings = []
    printers = [p for p in data['profiles'] if p['type'] == 'machine']
    if not printers:
        return ['Add a printer to review the settings against it.']
    assignments = assignment_map(data)
    for printer in printers:
        if not numbers(printer.get('nozzle_diameter')):
            warnings.append(f"{printer['name']}: nozzle diameters are missing or invalid; review them before installation.")
        variant = numbers(printer.get('printer_variant'))
        nozzles = numbers(printer.get('nozzle_diameter'))
        if len(variant) == 1 and nozzles and any(v != variant[0] for v in nozzles):
            warnings.append(f"{printer['name']}: printer variant {printer['printer_variant']} does not match all nozzle diameters. Review model/variant metadata before testing Orca's nozzle selector.")
    diameters = set()
    for profile in data['profiles']:
        name = profile['name']
        if profile['type'] == 'filament':
            values = numbers(profile.get('filament_diameter'))
            if values:
                diameters.update(values)
            else:
                warnings.append(f'{name}: filament diameter is missing or invalid. Confirm it matches the hardware.')
        elif profile['type'] == 'process':
            height = numbers(profile.get('layer_height'))
            if not height:
                warnings.append(f'{name}: layer height is missing or invalid; review the process.')
            else:
                for printer in printers:
                    nozzles = numbers(printer.get('nozzle_diameter'))
                    if name in assignments.get(printer['name'], {}).get('processes', []) and nozzles and max(height) > min(nozzles):
                        warnings.append(f"{name} → {printer['name']}: layer height exceeds at least one nozzle diameter. Review which extruder will print it.")
    if len(diameters) > 1:
        warnings.append('This set mixes filament diameters. Confirm that the assigned extruders support each diameter.')
    warnings.append('Temperature limits, motion limits, and custom G-code are not verified against your hardware. Review them before printing.')
    return warnings
