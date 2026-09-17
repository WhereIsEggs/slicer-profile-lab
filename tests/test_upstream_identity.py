# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Opt-in comparison with an explicitly pinned, locally checked-out upstream."""
import importlib.util
import os
from pathlib import Path
import subprocess
import unittest

from profilelab.orca_rules import system_setting_id, system_filament_id

DEVELOPMENT_REVISION = 'f520e9221f220657f752d269ead37dd61e9cb0c3'


@unittest.skipUnless(os.environ.get('PROFILELAB_UPSTREAM_SOURCE'), 'Opt-in pinned upstream comparison')
class UpstreamIdentityTests(unittest.TestCase):
    def test_system_ids_match_pinned_development_tool(self):
        source = Path(os.environ['PROFILELAB_UPSTREAM_SOURCE'])
        revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(revision, DEVELOPMENT_REVISION, 'Review upstream changes before updating the test pin')
        spec = importlib.util.spec_from_file_location('upstream_profile_tool', source / 'scripts/orca_profile_tool.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for vendor, kind, name in [('Lab', 'machine', 'Lab Standard 0.4'),
                                   ('Lab', 'process', 'Fine 0.8'),
                                   ('Lab', 'filament', 'PLA @0.4'),
                                   ('Véndor', 'filament', 'PLA β')]:
            self.assertEqual(system_setting_id(vendor, kind, name), module.generate_preset_setting_id(vendor, kind, name))
        for vendor, material, name in [('Lab', 'PLA', 'Lab PLA'), ('Lab', 'PETG', 'Lab PETG Pro')]:
            self.assertEqual(system_filament_id(vendor, material, name), module.generate_filament_id(vendor, material, name))
