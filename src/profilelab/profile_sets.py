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


def prepare_set(data):
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
