"""Small, explicit guided forms; blank fields are not guessed."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QPlainTextEdit, QDialogButtonBox, QMessageBox, QScrollArea, QWidget)
from profilelab.scratch_profiles import scratch_values
from profilelab.profile_install import _safe_name


class ScratchDialog(QDialog):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.result_values = None
        self.setWindowTitle('Create ' + {'machine': 'printer', 'filament': 'filament', 'process': 'process'}[kind] + ' from scratch')
        self.resize(620, 690)
        layout = QVBoxLayout(self)
        note = QLabel('Enter values for your hardware/material. No existing profile is copied. These are core settings, not a full calibration: other settings use Orca defaults and must be reviewed before printing.')
        note.setWordWrap(True)
        layout.addWidget(note)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        self.fields = {}

        def text(key, label, multiline=False):
            widget = QPlainTextEdit() if multiline else QLineEdit()
            if multiline:
                widget.setMaximumHeight(100)
            self.fields[key] = widget
            form.addRow(label, widget)

        def choice(key, label, options):
            widget = QComboBox()
            widget.addItem('Choose…', '')
            for title, value in options:
                widget.addItem(title, value)
            self.fields[key] = widget
            form.addRow(label, widget)

        text('name', 'Profile name')
        if kind == 'machine':
            choice('firmware', 'Firmware', [('Marlin (legacy)', 'marlin'), ('Marlin 2', 'marlin2'), ('Klipper', 'klipper'), ('RepRapFirmware', 'reprapfirmware')])
            for key, label in [('width', 'Bed width (mm)'), ('depth', 'Bed depth (mm)'), ('height', 'Maximum print height (mm)')]:
                text(key, label)
            form.addRow(QLabel('Rectangular bed; front-left origin (0,0). Other bed geometries are not supported by this form yet.'))
            choice('extruders', 'Extruders', [('One', '1'), ('Two', '2')])
            text('nozzle_0', 'E0 / Left nozzle diameter (mm)')
            text('nozzle_1', 'E1 / Right nozzle diameter (mm)')
            text('offset_x', 'E1 offset X relative to E0 (mm)')
            text('offset_y', 'E1 offset Y relative to E0 (mm)')
            self.fields['extruders'].currentIndexChanged.connect(self.update_extruders)
            self.update_extruders()
            text('start_gcode', 'Machine start G-code', True)
            text('end_gcode', 'Machine end G-code', True)
        elif kind == 'filament':
            choice('material', 'Material', [(v, v) for v in ('PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'PA', 'PC', 'PVA', 'HIPS')])
            for key, label in [('diameter', 'Filament diameter (mm)'), ('temperature', 'Nozzle temperature (°C)'), ('bed_temperature', 'Smooth PEI / high-temp plate (°C)'), ('flow_ratio', 'Flow ratio (e.g. 1.0)')]:
                text(key, label)
            form.addRow(QLabel('First-layer temperatures use the same entered values. Other plate types need separate review.'))
        else:
            for key, label in [('layer_height', 'Layer height (mm)'), ('first_layer_height', 'First-layer height (mm)'), ('walls', 'Wall loops'), ('infill', 'Sparse infill (%)'), ('outer_speed', 'Outer wall speed (mm/s)'), ('inner_speed', 'Inner wall speed (mm/s)')]:
                text(key, label)
        scroll.setWidget(body)
        layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Add to set')
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_extruders(self):
        enabled = self.fields['extruders'].currentData() == '2'
        for key in ('nozzle_1', 'offset_x', 'offset_y'):
            self.fields[key].setEnabled(enabled)

    def submit(self):
        values = {key: (widget.currentData() if isinstance(widget, QComboBox) else widget.toPlainText() if isinstance(widget, QPlainTextEdit) else widget.text()).strip() for key, widget in self.fields.items()}
        try:
            _safe_name(values['name'])
            self.result_values = scratch_values(self.kind, values)
            self.profile_name = values['name']
        except ValueError as error:
            QMessageBox.warning(self, 'Check your entries', str(error))
            return
        self.accept()
