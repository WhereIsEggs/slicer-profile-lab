# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Fictional offline presentation data. Never writes to OrcaSlicer's folders."""

from copy import deepcopy
import json
import os
from pathlib import Path

DEMO_REVISION = "fictional-demo-v1"


def demo_snapshot():
    printer = "Demo Dual Printer 0.4 nozzle"
    records = [
        ("machine", "Demo printer foundation", "", True, {
            "printer_technology": "FFF", "nozzle_diameter": ["0.4", "0.4"],
            "printable_height": "250", "printable_area": ["0x0", "250x0", "250x250", "0x250"],
            "retraction_length": ["0.8", "0.8"], "retraction_speed": ["35", "35"],
            "retract_when_changing_layer": ["1", "1"],
        }),
        ("machine", printer, "Demo printer foundation", False, {
            "default_print_profile": "Demo Standard 0.20mm",
            "default_filament_profile": ["Demo PLA", "Demo PETG"],
        }),
        ("process", "Demo process foundation", "", True, {
            "layer_height": "0.2", "wall_loops": "3", "sparse_infill_density": "15%",
            "enable_support": "0", "outer_wall_speed": "50",
        }),
        ("process", "Demo Standard 0.20mm", "Demo process foundation", False, {
            "compatible_printers": [printer],
        }),
        ("filament", "Demo PLA", "", False, {
            "filament_type": ["PLA"], "filament_vendor": ["Fictional Demo"],
            "filament_id": "P0000001", "nozzle_temperature": ["210"],
            "filament_flow_ratio": ["1.0"], "compatible_printers": [printer],
        }),
        ("filament", "Demo PETG", "", False, {
            "filament_type": ["PETG"], "filament_vendor": ["Fictional Demo"],
            "filament_id": "P0000002", "nozzle_temperature": ["240"],
            "filament_flow_ratio": ["0.98"], "compatible_printers": [printer],
        }),
    ]
    profiles = []
    for number, (kind, name, parent, template, values) in enumerate(records):
        profiles.append({"name": name, "type": kind, "vendor": "Fictional Demo", "parent": parent,
                         "template": template, "path": f"demo/{kind}/{number}.json",
                         "settings": {**deepcopy(values), "name": name, "type": kind, "inherits": parent,
                                      "instantiation": "false" if template else "true"}})
    return {"metadata": {"version": "2.4.2", "revision": DEMO_REVISION,
                         "downloaded_at": "Offline demo", "demo": True}, "profiles": profiles}


def initialize_demo(root: Path):
    """Create only clearly fictional, small validation examples in the demo root."""
    root = root.resolve()
    appdata = os.environ.get("APPDATA")
    if appdata and root.is_relative_to((Path(appdata) / "OrcaSlicer").resolve()):
        raise ValueError("The demo workspace must be outside OrcaSlicer's folders.")
    examples = {
        "valid": [{"name": "Demo Base", "type": "process"},
                  {"name": "Demo Child", "type": "process", "inherits": "Demo Base"}],
        "missing-parent": [{"name": "Demo Child", "type": "process", "inherits": "Missing Demo Parent"}],
    }
    for folder, profiles in examples.items():
        target = root / "examples" / folder
        target.mkdir(parents=True, exist_ok=True)
        for number, profile in enumerate(profiles):
            destination = target / f"demo-{number}.json"
            # Reruns never overwrite any existing demonstration artifacts.
            if not destination.exists():
                with destination.open("x", encoding="utf-8") as output:
                    json.dump(profile, output, indent=2)
    return demo_snapshot()
