# SPDX-License-Identifier: AGPL-3.0-only
"""Display-only Orca metadata. JSON keys and values remain untouched."""
from profilelab.orca_setting_labels import SETTINGS


def setting_label(key):
    info = SETTINGS.get(key, {})
    label = info.get('full_label') or info.get('label') or key.replace('_', ' ').capitalize()
    # Orca supplies the surrounding section in its UI; our flat table needs it.
    if key == 'additional_cooling_fan_speed':
        label = 'Auxiliary part-cooling fan — ' + label
    elif info.get('category'):
        label = info['category'] + ' — ' + label
    unit = info.get('sidetext', '')
    if unit and unit not in label:
        label += f' ({unit})'
    return label


def setting_help(key):
    info = SETTINGS.get(key, {})
    explanation = info.get('tooltip', 'No Orca description is available for this setting.')
    return explanation + '\n\nJSON setting: ' + key
