# SPDX-License-Identifier: AGPL-3.0-only
"""Explainable suggestions, never a hardware-safety or Orca-expression evaluator."""
import math


def names(value):
    return [v for v in (value if isinstance(value, list) else [value]) if isinstance(v, str) and v]


def diameters(value):
    try:
        values = [float(v) for v in (value if isinstance(value, list) else [value])]
        return set(values) if values and all(math.isfinite(v) and v > 0 for v in values) else set()
    except (ValueError, TypeError):
        return set()


def recommendation(record, data, records):
    """Return reasons based on exact source links and explicit diameter evidence."""
    if record.get('source_error'):
        return []
    candidate = record.get('values', {})
    kind = record['type']
    reasons = []
    for profile in data.get('profiles', []):
        source = data.get('sources', {}).get(profile['type'] + '/' + profile['name'], {})
        identity = source.get('name', profile['name'])
        vendor = source.get('vendor')
        label = profile['name']
        printer = profile if profile['type'] == 'machine' else candidate if kind == 'machine' else None
        filament = candidate if kind == 'filament' else profile if profile['type'] == 'filament' else None
        if printer is not None and filament is not None:
            expected = diameters(printer.get('filament_diameter'))
            if not expected:
                # Only use unambiguous default filament metadata, never nozzle diameter.
                defaults = names(printer.get('default_filament_profile'))
                for default in defaults:
                    matches = [r for r in records if r['type'] == 'filament' and r['name'] == default
                               and not r.get('source_error')]
                    preferred = [r for r in matches if r.get('vendor') == (vendor if profile['type'] == 'machine' else record.get('vendor'))]
                    matches = preferred or matches
                    if len(matches) == 1:
                        expected.update(diameters(matches[0].get('values', {}).get('filament_diameter')))
            actual = diameters(filament.get('filament_diameter'))
            if expected and actual and not actual.issubset(expected):
                continue  # A known diameter mismatch overrides a stale named link.
            if expected and actual:
                reasons.append(f"Diameter match ({'/'.join(str(v) for v in sorted(actual))} mm) with {label}; review other settings")
        if profile['type'] == 'machine' and kind in ('filament', 'process'):
            defaults = names(profile.get('default_filament_profile' if kind == 'filament' else 'default_print_profile'))
            if record['name'] in defaults and (not vendor or vendor == record.get('vendor')):
                reasons.append(f'Original default for {label}')
            if identity in names(candidate.get('compatible_printers')) and (not vendor or vendor == record.get('vendor')):
                reasons.append(f'Explicit printer link to {label}')
        elif kind == 'machine' and profile['type'] in ('filament', 'process'):
            if record['name'] in names(profile.get('compatible_printers')) and (not vendor or vendor == record.get('vendor')):
                reasons.append(f'Explicit printer link from {label}')
            defaults = names(candidate.get('default_filament_profile' if profile['type'] == 'filament' else 'default_print_profile'))
            if identity in defaults and (not vendor or vendor == record.get('vendor')):
                reasons.append(f'Uses {label} as an original default')
        elif kind == 'process' and profile['type'] == 'filament':
            if record['name'] in names(profile.get('compatible_prints')) and (not vendor or vendor == record.get('vendor')):
                reasons.append(f'Explicit process link from {label}')
        elif kind == 'filament' and profile['type'] == 'process':
            if identity in names(candidate.get('compatible_prints')) and (not vendor or vendor == record.get('vendor')):
                reasons.append(f'Explicit process link to {label}')
    if reasons and (candidate.get('compatible_printers_condition') or candidate.get('compatible_prints_condition')):
        reasons.append('Orca compatibility conditions still need review')
    return sorted(dict.fromkeys(reasons), key=lambda reason: (reason.startswith('Orca '), reason.startswith('Diameter match')))
