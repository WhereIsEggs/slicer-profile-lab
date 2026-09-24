# SPDX-License-Identifier: AGPL-3.0-only
"""Freeze generic Orca settings while retaining the user's hardware identity."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from profilelab.resolver import ProfileResolver


def sync_nozzle_variant(profile):
    """A single selector diameter only describes matching-nozzle configurations."""
    values = profile.get('nozzle_diameter', [])
    if not isinstance(values, list) or not values:
        return
    try:
        diameters = [Decimal(str(v)) for v in values]
    except InvalidOperation:
        return
    if all(v.is_finite() and v > 0 for v in diameters) and len(set(diameters)) == 1:
        profile['printer_variant'] = format(diameters[0].normalize(), 'f')


def generic_printer(name, entered, snapshot):
    models = {'klipper': 'Generic Klipper Printer', 'marlin': 'Generic Marlin Printer',
              'marlin2': 'Generic Marlin Printer', 'reprapfirmware': 'Generic RRF Printer'}
    flavor = entered.get('gcode_flavor')
    if flavor not in models:
        raise ValueError('No supported generic template for this firmware.')
    if not snapshot:
        raise ValueError('Download the system library before creating a generic printer.')
    resolver = ProfileResolver(snapshot['profiles'])
    candidates = []
    for record in snapshot['profiles']:
        if record.get('vendor') != 'Custom' or record['type'] != 'machine' or record.get('template'):
            continue
        values = {k: deepcopy(v.value) for k, v in resolver.resolve(record).items()}
        if values.get('printer_model') == models[flavor] and str(values.get('printer_variant')) == '0.4':
            candidates.append((record, values))
    if len(candidates) != 1:
        raise ValueError(f'The library does not contain one unambiguous {models[flavor]} 0.4 template. No printer was created.')
    record, values = candidates[0]
    # References to template presets must not leak into an independent set.
    for key in list(values):
        if key.startswith(('default_', 'compatible_')):
            values.pop(key)
    values.update(deepcopy(entered))
    values['printer_model'] = name
    values.pop('printer_variant', None)
    sync_nozzle_variant(values)
    source = dict(name=record['name'], vendor=record['vendor'], path=record['path'],
                  chain=[p['name'] for p in reversed(resolver.chain(record))],
                  revision=snapshot['metadata']['revision'], version=snapshot['metadata']['version'])
    return values, source
