from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QDoubleSpinBox, QSpinBox, QComboBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt


def _make_float_row(label: str, min_v: float, max_v: float, default: float,
                    decimals: int, step: float, tooltip: str):
    """Return (layout, spinbox) for a float parameter row with linked slider."""
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setFixedWidth(120)
    lbl.setToolTip(tooltip)
    spin = QDoubleSpinBox()
    spin.setRange(min_v, max_v)
    spin.setValue(default)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setToolTip(tooltip)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(int(min_v * 100), int(max_v * 100))
    slider.setValue(int(default * 100))
    # Keep slider and spinbox in sync
    slider.valueChanged.connect(lambda v: spin.setValue(v / 100))
    spin.valueChanged.connect(lambda v: slider.setValue(int(v * 100)))
    row.addWidget(lbl)
    row.addWidget(spin)
    row.addWidget(slider)
    return row, spin


class ParametersTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        params_group = QGroupBox("Generation Parameters")
        layout = QVBoxLayout(params_group)

        # cfg_scale
        row, self.cfg_spin = _make_float_row(
            "cfg_scale", 1.0, 20.0, self.state.cfg_scale, 1, 0.5,
            "How strictly the model follows your prompt. Higher = more literal, lower = more creative."
        )
        self.cfg_spin.valueChanged.connect(lambda v: self._update("cfg_scale", v))
        layout.addLayout(row)

        # temperature
        row, self.temp_spin = _make_float_row(
            "temperature", 0.1, 2.0, self.state.temperature, 2, 0.05,
            "Randomness of token selection. Higher = more varied output."
        )
        self.temp_spin.valueChanged.connect(lambda v: self._update("temperature", v))
        layout.addLayout(row)

        # top_p
        row, self.top_p_spin = _make_float_row(
            "top_p", 0.0, 1.0, self.state.top_p, 2, 0.01,
            "Cumulative probability cutoff. Lower = more focused output."
        )
        self.top_p_spin.valueChanged.connect(lambda v: self._update("top_p", v))
        layout.addLayout(row)

        # min_p
        row, self.min_p_spin = _make_float_row(
            "min_p", 0.0, 1.0, self.state.min_p, 2, 0.01,
            "Minimum probability threshold. Filters low-confidence tokens."
        )
        self.min_p_spin.valueChanged.connect(lambda v: self._update("min_p", v))
        layout.addLayout(row)

        # top_k (integer)
        top_k_row = QHBoxLayout()
        top_k_lbl = QLabel("top_k")
        top_k_lbl.setFixedWidth(120)
        top_k_lbl.setToolTip("Maximum number of tokens considered at each step.")
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(0, 200)
        self.top_k_spin.setValue(self.state.top_k)
        self.top_k_spin.setToolTip("Maximum number of tokens considered at each step.")
        self.top_k_spin.valueChanged.connect(lambda v: self._update("top_k", v))
        top_k_slider = QSlider(Qt.Orientation.Horizontal)
        top_k_slider.setRange(0, 200)
        top_k_slider.setValue(self.state.top_k)
        top_k_slider.valueChanged.connect(self.top_k_spin.setValue)
        self.top_k_spin.valueChanged.connect(top_k_slider.setValue)
        top_k_row.addWidget(top_k_lbl)
        top_k_row.addWidget(self.top_k_spin)
        top_k_row.addWidget(top_k_slider)
        layout.addLayout(top_k_row)

        # Duration
        dur_row = QHBoxLayout()
        dur_lbl = QLabel("Duration (s)")
        dur_lbl.setFixedWidth(120)
        self.dur_spin = QSpinBox()
        self.dur_spin.setRange(10, 300)
        self.dur_spin.setValue(self.state.duration)
        self.dur_spin.valueChanged.connect(lambda v: self._update("duration", v))
        dur_row.addWidget(dur_lbl)
        dur_row.addWidget(self.dur_spin)
        dur_row.addStretch()
        layout.addLayout(dur_row)

        # Steps
        steps_row = QHBoxLayout()
        steps_lbl = QLabel("Steps")
        steps_lbl.setFixedWidth(120)
        steps_lbl.setToolTip("Diffusion steps. More = higher quality, slower generation.")
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 150)
        self.steps_spin.setValue(self.state.steps)
        self.steps_spin.setToolTip("Diffusion steps. More = higher quality, slower.")
        self.steps_spin.valueChanged.connect(lambda v: self._update("steps", v))
        steps_row.addWidget(steps_lbl)
        steps_row.addWidget(self.steps_spin)
        steps_row.addStretch()
        layout.addLayout(steps_row)

        # task_type
        task_row = QHBoxLayout()
        task_lbl = QLabel("task_type")
        task_lbl.setFixedWidth(120)
        self.task_combo = QComboBox()
        self.task_combo.addItems(["text2music", "lego", "repaint", "extract"])
        self.task_combo.setCurrentText(self.state.task_type)
        self.task_combo.currentTextChanged.connect(lambda v: self._update("task_type", v))
        task_row.addWidget(task_lbl)
        task_row.addWidget(self.task_combo)
        task_row.addStretch()
        layout.addLayout(task_row)

        root.addWidget(params_group)
        root.addStretch()

    def _update(self, field: str, value):
        setattr(self.state, field, value)
        self.state_changed.emit()
