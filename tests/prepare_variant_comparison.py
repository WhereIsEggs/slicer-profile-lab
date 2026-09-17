"""Generate fictional comparison inputs only; never install into normal Orca."""
from pathlib import Path
from uuid import uuid4
import json
from profilelab.profile_sets import new_set, add_copy, prepare_set
from profilelab.scratch_profiles import scratch_values
from profilelab.orca_bundle import export_orca_bundle
from profilelab.user_sharing import share_prepared_package


def comparison_set():
    data = new_set('Variant comparison')
    assignments = {}
    for model, width in [('Lab Standard', '200'), ('Lab XL', '300')]:
        for nozzle in ('0.4', '0.8'):
            name = f'{model} {nozzle}'
            values = scratch_values('machine', dict(firmware='klipper', width=width, depth=width,
                height='250', extruders='1', nozzle_0=nozzle,
                start_gcode='; FICTIONAL TEST ONLY - DO NOT PRINT', end_gcode='; FICTIONAL TEST ONLY'))
            values.update(printer_model=model, printer_variant=nozzle)
            add_copy(data, 'machine', name, values, '2.4.2')
            process = 'Lab Process ' + nozzle
            assignments[name] = dict(filaments=['Lab PLA'], processes=[process], defaults=dict(filaments=['Lab PLA'], process=process))
    values = scratch_values('machine', dict(firmware='klipper', width='200', depth='200', height='250',
        extruders='2', nozzle_0='0.4', nozzle_1='0.8', offset_x='25', offset_y='0',
        start_gcode='; FICTIONAL TEST ONLY - DO NOT PRINT', end_gcode='; FICTIONAL TEST ONLY'))
    values.update(printer_model='Lab Dual', printer_variant='0.4')
    add_copy(data, 'machine', 'Lab Dual 0.4 + 0.8', values, '2.4.2')
    assignments['Lab Dual 0.4 + 0.8'] = dict(filaments=['Lab PLA'], processes=['Lab Process 0.4'], defaults=dict(filaments=['Lab PLA'] * 2, process='Lab Process 0.4'))
    add_copy(data, 'filament', 'Lab PLA', scratch_values('filament', dict(material='PLA', diameter='1.75', temperature='200', bed_temperature='55', flow_ratio='1')), '2.4.2')
    for nozzle, layer in [('0.4', '0.2'), ('0.8', '0.4')]:
        add_copy(data, 'process', 'Lab Process ' + nozzle, scratch_values('process', dict(layer_height=layer, first_layer_height=layer, walls='2', infill='15', outer_speed='30', inner_speed='40')), '2.4.2')
    data['printer_assignments'] = assignments
    return data


if __name__ == '__main__':
    folder = Path(__file__).resolve().parents[1] / 'artifacts' / 'variant-comparison' / uuid4().hex[:8]
    folder.mkdir(parents=True)
    data = comparison_set()
    (folder / 'source-set.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    profiles = prepare_set(data)
    package = folder / 'Lab-family.orca_bundle'
    export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], package)
    print(share_prepared_package(package))
