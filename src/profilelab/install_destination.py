# SPDX-License-Identifier: AGPL-3.0-only
"""Local development override; packaged apps retain the normal Orca destination."""
import json
import os
from pathlib import Path
import sys


def install_destination():
    root = Path(__file__).resolve().parents[2]
    config = root / 'local-orca-test.json'
    if not getattr(sys, 'frozen', False) and config.is_file():
        data = json.loads(config.read_text(encoding='utf-8'))
        folder = (root / data['data_dir']).resolve()
        if not folder.is_dir():
            raise ValueError('The configured Orca test data folder is missing. No profiles were installed.')
        return folder / 'user' / 'default', 'Orca 2.5 test environment — open with Start Orca 2.5 Test'
    if not os.environ.get('APPDATA'):
        raise ValueError('The Windows user profile location could not be found.')
    return Path(os.environ['APPDATA']) / 'OrcaSlicer' / 'user' / 'default', 'Normal OrcaSlicer user profiles'
