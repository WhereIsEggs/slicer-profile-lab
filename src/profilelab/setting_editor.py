# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Human-readable value display and type-preserving draft editing."""

import math
from profilelab.setting_labels import setting_label, setting_help
from decimal import Decimal, InvalidOperation
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget,
)
from profilelab.setting_types import BOOLEAN_KEYS
from profilelab.choice_combo import ChoiceComboBox as QComboBox

# Narrow, explicitly supported input checks. These are not a complete Orca schema.
NUMERIC_BOUNDS = {
    "nozzle_diameter": (0, 10, False), "layer_height": (0, 10, False),
    "printable_height": (0, 100000, False), "retraction_length": (0, 1000, True),
    "retraction_speed": (0, 10000, True), "outer_wall_speed": (0, 10000, True),
    "nozzle_temperature": (0, 1000, True), "filament_flow_ratio": (0, 10, False),
    "wall_loops": (0, 10000, True), "sparse_infill_density": (0, 100, True),
}


def check_numeric_text(key, value):
    if key not in NUMERIC_BOUNDS:
        return
    text = str(value).strip()
    if key == "sparse_infill_density":
        text = text.removesuffix("%")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError("Enter a number for this setting.") from None
    low, high, allow_zero = NUMERIC_BOUNDS[key]
    if not number.is_finite() or number > high or number < low or (number == low and not allow_zero):
        raise ValueError(f"Enter a number {'from' if allow_zero else 'greater than'} {low} and no greater than {high}.")
    if key == "wall_loops" and number != number.to_integral_value():
        raise ValueError("Wall loops must be a whole number.")


def display_value(value, key=None):
    if key in BOOLEAN_KEYS and not isinstance(value, list) and str(value) in {"0", "1"}:
        return "On" if str(value) == "1" else "Off"
    if isinstance(value, bool):
        return "On" if value else "Off"
    if isinstance(value, list):
        return " · ".join(display_value(item, key) for item in value) if value else "No values set"
    if isinstance(value, dict):
        return "Structured setting"
    if value is None:
        return "Not set"
    return str(value) if str(value) else "Not set"


def editable_value(value):
    if isinstance(value, list):
        return bool(value) and all(isinstance(item, (str, int, float, bool)) for item in value)
    return isinstance(value, (str, int, float, bool))


class SettingDialog(QDialog):
    def __init__(self, label, key, value, parent=None, *, choices=None, extruder_slots=False):
        super().__init__(parent)
        self.setWindowTitle(setting_label(key))
        self.resize(460, 240)
        self.original = value
        self.key = key
        self.value = value
        self.editors = []
        layout = QVBoxLayout(self)
        description = QLabel(setting_help(key))
        description.setWordWrap(True)
        from PySide6.QtCore import Qt
        description.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(description)
        note = QLabel("Change the value below." if not isinstance(value, list)
                      else "This setting has multiple values. Edit each value separately.")
        note.setWordWrap(True)
        layout.addWidget(note)
        panel = QWidget()
        form = QFormLayout(panel)
        entries = value if isinstance(value, list) else [value]
        for index, entry in enumerate(entries):
            if choices is not None or key == "default_filament_profile":
                editor = QComboBox()
                editor.setEditable(False)
                editor.addItem("Choose a compatible profile…", None)
                for choice in choices or []:
                    editor.addItem(choice, choice)
                editor.setCurrentIndex(max(0, editor.findData(entry)))
                editor.setToolTip("Only verified compatible library profiles are listed. Current value: " + str(entry))
            elif isinstance(entry, bool) or key in BOOLEAN_KEYS:
                editor = QComboBox()
                editor.addItem("Off", False)
                editor.addItem("On", True)
                editor.setCurrentIndex(1 if entry is True or str(entry) == "1" else 0)
                if not isinstance(entry, bool) and str(entry) not in {"0", "1"}:
                    editor.addItem("Choose On or Off…", None)
                    editor.setCurrentIndex(2)
            elif isinstance(entry, str) and ("\n" in entry or "gcode" in key):
                editor = QPlainTextEdit(entry)
                editor.setMinimumHeight(140)
            else:
                editor = QLineEdit(str(entry))
            self.editors.append(editor)
            slot = ("E0 / Left", "E1 / Right")[index] if extruder_slots and len(entries) == 2 else f"E{index}"
            form.addRow(slot if extruder_slots else (f"Value {index + 1}" if isinstance(value, list) and len(value) > 1 else "Value"), editor)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        layout.addWidget(scroll)
        self.error = QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_values)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_values(self):
        originals = self.original if isinstance(self.original, list) else [self.original]
        values = []
        try:
            for old, editor in zip(originals, self.editors):
                if isinstance(editor, QComboBox):
                    selected = editor.currentData()
                    if selected is None:
                        self.error.setText("Choose an option for every field. Filament choices include only verified compatible profiles from the pinned system library; advanced conditions and local user profiles are not yet supported.")
                        return
                    new = type(old)(int(selected)) if isinstance(selected, bool) else selected
                else:
                    text = editor.toPlainText() if isinstance(editor, QPlainTextEdit) else editor.text()
                    if isinstance(old, int):
                        new = int(text)
                    elif isinstance(old, float):
                        new = float(text)
                        if not math.isfinite(new):
                            raise ValueError()
                    else:
                        new = text
                check_numeric_text(self.key, new)
                values.append(new)
        except ValueError as error:
            self.error.setText(str(error) or "Enter a valid number. Whole-number settings require a whole number.")
            return
        self.value = values if isinstance(self.original, list) else values[0]
        self.accept()
