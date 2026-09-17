# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Explicit starter settings for new FFF profiles; no hidden donor profile."""
from decimal import Decimal, InvalidOperation


def number(values, key, low, high, integer=False):
    try:
        value = Decimal(str(values.get(key, '')).strip())
    except InvalidOperation:
        raise ValueError(f'Enter a number for {key.replace("_", " ")}.') from None
    if not value.is_finite() or not low <= value <= high or (integer and value != value.to_integral_value()):
        raise ValueError(f'{key.replace("_", " ")}: enter {"a whole number" if integer else "a number"} from {low} to {high}.')
    return format(value, 'f')


def scratch_values(kind, values):
    """Construct only explicitly entered core settings. Orca supplies the rest."""
    if kind == 'machine':
        firmware = values.get('firmware')
        if firmware not in ('marlin', 'marlin2', 'klipper', 'reprapfirmware'):
            raise ValueError('Choose the firmware used by this printer.')
        width = number(values, 'width', 1, 100000)
        depth = number(values, 'depth', 1, 100000)
        height = number(values, 'height', 1, 100000)
        count = int(number(values, 'extruders', 1, 2, True))
        nozzles = [number(values, f'nozzle_{i}', Decimal('0.05'), 10) for i in range(count)]
        offsets = ['0x0']
        if count == 2:
            offsets.append(number(values, 'offset_x', -100000, 100000) + 'x' + number(values, 'offset_y', -100000, 100000))
        if not values.get('start_gcode', '').strip() or not values.get('end_gcode', '').strip():
            raise ValueError('Supply machine start and end G-code for this hardware. Profile Lab cannot generate a safe homing/heating sequence for an unknown printer.')
        return dict(printer_technology='FFF', gcode_flavor=firmware,
                    printable_area=['0x0', f'{width}x0', f'{width}x{depth}', f'0x{depth}'],
                    printable_height=height, nozzle_diameter=nozzles, extruder_offset=offsets,
                    machine_start_gcode=values['start_gcode'], machine_end_gcode=values['end_gcode'])
    if kind == 'filament':
        material = values.get('material', '').strip()
        if material not in ('PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'PA', 'PC', 'PVA', 'HIPS'):
            raise ValueError('Choose a supported material type.')
        diameter = number(values, 'diameter', Decimal('0.1'), 10)
        nozzle = number(values, 'temperature', 1, 1000, True)
        bed = number(values, 'bed_temperature', 0, 1000, True)
        flow = number(values, 'flow_ratio', Decimal('0.01'), 10)
        return dict(filament_type=[material], filament_diameter=[diameter],
                    nozzle_temperature=[nozzle], nozzle_temperature_initial_layer=[nozzle],
                    hot_plate_temp=[bed], hot_plate_temp_initial_layer=[bed],
                    filament_flow_ratio=[flow])
    if kind == 'process':
        return dict(layer_height=number(values, 'layer_height', Decimal('0.01'), 10),
                    initial_layer_print_height=number(values, 'first_layer_height', Decimal('0.01'), 10),
                    wall_loops=number(values, 'walls', 0, 100, True),
                    sparse_infill_density=number(values, 'infill', 0, 100) + '%',
                    outer_wall_speed=number(values, 'outer_speed', Decimal('0.1'), 10000),
                    inner_wall_speed=number(values, 'inner_speed', Decimal('0.1'), 10000))
    raise ValueError('Unsupported profile category.')
