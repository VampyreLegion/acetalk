from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QDoubleSpinBox, QSpinBox, QComboBox, QGroupBox,
    QPushButton, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
import random


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
            "Controls how strictly the song follows your tags and lyrics.\n\n"
            "Low (1–2): More creative, may drift from your prompt — unexpected musical ideas.\n"
            "Default (2): Recommended for ACE-Step XL Turbo — balanced and expressive.\n"
            "High (5+): Very literal — the model tries hard to match every tag exactly.\n\n"
            "Start at 2.0 and raise it if the output sounds too different from your tags."
        )
        self.cfg_spin.valueChanged.connect(lambda v: self._update("cfg_scale", v))
        layout.addLayout(row)

        # temperature
        row, self.temp_spin = _make_float_row(
            "temperature", 0.1, 2.0, self.state.temperature, 2, 0.05,
            "Controls how adventurous or predictable the music sounds.\n\n"
            "Low (0.5–0.7): Safer, more conventional arrangements and melodies.\n"
            "Default (0.85): Natural variation — sounds musical and dynamic.\n"
            "High (1.2+): Surprising, unpredictable, sometimes experimental.\n\n"
            "Raise it if every generation sounds too similar; lower it for cleaner results."
        )
        self.temp_spin.valueChanged.connect(lambda v: self._update("temperature", v))
        layout.addLayout(row)

        # top_p
        row, self.top_p_spin = _make_float_row(
            "top_p", 0.0, 1.0, self.state.top_p, 2, 0.01,
            "Nucleus sampling — limits which musical choices the model considers at each step.\n\n"
            "Low (0.5–0.7): Tight focus — stays close to the most likely, genre-appropriate sounds.\n"
            "Default (0.9): Broad palette — allows varied but still coherent choices.\n"
            "1.0: All options considered — maximum variety.\n\n"
            "Lower this if the song sounds chaotic or off-genre."
        )
        self.top_p_spin.valueChanged.connect(lambda v: self._update("top_p", v))
        layout.addLayout(row)

        # min_p
        row, self.min_p_spin = _make_float_row(
            "min_p", 0.0, 1.0, self.state.min_p, 2, 0.01,
            "Cuts out any musical choices the model is unsure about.\n\n"
            "0.0 (default): No filtering — all options are on the table.\n"
            "0.05–0.1: Removes weak/unlikely choices, tightens the sound.\n"
            "Higher values: Very conservative — only the most confident choices survive.\n\n"
            "Leave at 0 unless you're getting weird or jarring output."
        )
        self.min_p_spin.valueChanged.connect(lambda v: self._update("min_p", v))
        layout.addLayout(row)

        # top_k (integer)
        top_k_tt = (
            "Limits how many different musical choices the model considers at each step.\n\n"
            "0 (default): No limit — uses top_p to control variety instead.\n"
            "20–50: Restricts the palette — more focused, genre-consistent output.\n"
            "Higher: More variety allowed.\n\n"
            "Leave at 0 unless you want to manually cap variety. top_p is usually enough."
        )
        top_k_row = QHBoxLayout()
        top_k_lbl = QLabel("top_k")
        top_k_lbl.setFixedWidth(120)
        top_k_lbl.setToolTip(top_k_tt)
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(0, 200)
        self.top_k_spin.setValue(self.state.top_k)
        self.top_k_spin.setToolTip(top_k_tt)
        self.top_k_spin.valueChanged.connect(lambda v: self._update("top_k", v))
        top_k_slider = QSlider(Qt.Orientation.Horizontal)
        top_k_slider.setRange(0, 200)
        top_k_slider.setValue(self.state.top_k)
        top_k_slider.setToolTip(top_k_tt)
        top_k_slider.valueChanged.connect(self.top_k_spin.setValue)
        self.top_k_spin.valueChanged.connect(top_k_slider.setValue)
        top_k_row.addWidget(top_k_lbl)
        top_k_row.addWidget(self.top_k_spin)
        top_k_row.addWidget(top_k_slider)
        layout.addLayout(top_k_row)

        # Duration
        dur_tt = (
            "How long the generated audio will be, in seconds.\n\n"
            "30–60s: Short clip or intro — good for testing a sound quickly.\n"
            "90–120s: Full song arrangement with intro, verses, chorus, and outro.\n"
            "180–240s: Extended version — room for solos, breakdowns, and fades.\n\n"
            "Longer durations take more VRAM and generation time."
        )
        dur_row = QHBoxLayout()
        dur_lbl = QLabel("Duration (s)")
        dur_lbl.setFixedWidth(120)
        dur_lbl.setToolTip(dur_tt)
        self.dur_spin = QSpinBox()
        self.dur_spin.setRange(10, 300)
        self.dur_spin.setValue(self.state.duration)
        self.dur_spin.setToolTip(dur_tt)
        self.dur_spin.valueChanged.connect(lambda v: self._update("duration", v))
        dur_row.addWidget(dur_lbl)
        dur_row.addWidget(self.dur_spin)
        dur_row.addStretch()
        layout.addLayout(dur_row)

        # Steps
        steps_tt = (
            "Number of diffusion steps — more steps = more refined audio detail.\n\n"
            "8 (default): Correct for ACE-Step XL Turbo — fast, high quality.\n"
            "12–20: Slightly more polish, noticeably slower.\n"
            "30+: Diminishing returns on Turbo — use the base model instead.\n\n"
            "Do not raise above 8–10 when using the XL Turbo model."
        )
        steps_row = QHBoxLayout()
        steps_lbl = QLabel("Steps")
        steps_lbl.setFixedWidth(120)
        steps_lbl.setToolTip(steps_tt)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 150)
        self.steps_spin.setValue(self.state.steps)
        self.steps_spin.setToolTip(steps_tt)
        self.steps_spin.valueChanged.connect(lambda v: self._update("steps", v))
        steps_row.addWidget(steps_lbl)
        steps_row.addWidget(self.steps_spin)
        steps_row.addStretch()
        layout.addLayout(steps_row)

        # task_type
        task_tt = (
            "Sets the generation mode for the ACE-Step node.\n\n"
            "text2music: Generate a new song from your tags and lyrics (normal mode).\n"
            "lego:       Combine/stitch multiple audio segments together.\n"
            "repaint:    Re-generate a section of an existing audio file.\n"
            "extract:    Separate stems or extract components from audio.\n\n"
            "Use text2music for all standard song generation."
        )
        task_row = QHBoxLayout()
        task_lbl = QLabel("task_type")
        task_lbl.setFixedWidth(120)
        task_lbl.setToolTip(task_tt)
        self.task_combo = QComboBox()
        self.task_combo.addItems(["text2music", "lego", "repaint", "extract"])
        self.task_combo.setToolTip(task_tt)
        self.task_combo.setCurrentText(self.state.task_type)
        self.task_combo.currentTextChanged.connect(lambda v: self._update("task_type", v))
        task_row.addWidget(task_lbl)
        task_row.addWidget(self.task_combo)
        task_row.addStretch()
        layout.addLayout(task_row)

        # Seed row
        seed_tt = (
            "The random seed used for generation.\n\n"
            "Each seed produces a completely different song from the same tags and lyrics.\n"
            "Lock the seed to keep the same musical foundation while tweaking your prompt."
        )
        seed_row = QHBoxLayout()
        seed_lbl = QLabel("Seed")
        seed_lbl.setFixedWidth(120)
        seed_lbl.setToolTip(seed_tt)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2**31 - 1)
        self.seed_spin.setFixedWidth(120)
        self.seed_spin.setToolTip(seed_tt)
        self.seed_spin.valueChanged.connect(self._on_seed_changed)
        self.seed_spin.setValue(self.state.seed)  # connect signal first, then set value

        self.lock_check = QCheckBox("Lock seed (iterate on same base)")
        self.lock_check.setChecked(self.state.lock_seed)
        self.lock_check.setToolTip(
            "Locked: same seed every run — tweak tags, lyrics, BPM, or instruments\n"
            "to refine the same song without changing its core musical character.\n\n"
            "Unlocked: new random seed every run — every generation is a fresh take.\n\n"
            "Tip: find a seed you like, lock it, then make small adjustments."
        )
        self.lock_check.stateChanged.connect(self._on_lock_changed)

        self.btn_new_seed = QPushButton("New Random Seed")
        self.btn_new_seed.setFixedWidth(130)
        self.btn_new_seed.clicked.connect(self._randomize_seed)

        seed_row.addWidget(seed_lbl)
        seed_row.addWidget(self.seed_spin)
        seed_row.addWidget(self.lock_check)
        seed_row.addWidget(self.btn_new_seed)
        seed_row.addStretch()
        layout.addLayout(seed_row)

        root.addWidget(params_group)
        root.addStretch()

    def _update(self, field: str, value):
        setattr(self.state, field, value)
        self.state_changed.emit()

    def _on_seed_changed(self, val: int):
        self.state.seed = val
        self.state_changed.emit()

    def _on_lock_changed(self, state):
        self.state.lock_seed = self.lock_check.isChecked()
        # Auto-generate a seed the moment the user locks, so they have something to work with
        if self.state.lock_seed and self.state.seed == 0:
            self._randomize_seed()
        self.state_changed.emit()

    def _randomize_seed(self):
        new_seed = random.randint(0, 2**31 - 1)
        self.seed_spin.setValue(new_seed)   # triggers _on_seed_changed

    def update_seed(self, seed: int):
        """Called externally to display the seed that was actually used."""
        self.seed_spin.blockSignals(True)
        self.seed_spin.setValue(seed)
        self.seed_spin.blockSignals(False)
        self.state.seed = seed

    def load_from_state(self):
        """Sync all parameter widgets from state (e.g. after Easy tab populates state)."""
        for w in (self.cfg_spin, self.temp_spin, self.top_p_spin, self.min_p_spin,
                  self.top_k_spin, self.dur_spin, self.steps_spin,
                  self.task_combo, self.seed_spin, self.lock_check):
            w.blockSignals(True)
        self.cfg_spin.setValue(self.state.cfg_scale)
        self.temp_spin.setValue(self.state.temperature)
        self.top_p_spin.setValue(self.state.top_p)
        self.min_p_spin.setValue(self.state.min_p)
        self.top_k_spin.setValue(self.state.top_k)
        self.dur_spin.setValue(self.state.duration)
        self.steps_spin.setValue(self.state.steps)
        self.task_combo.setCurrentText(self.state.task_type)
        self.seed_spin.setValue(self.state.seed)
        self.lock_check.setChecked(self.state.lock_seed)
        for w in (self.cfg_spin, self.temp_spin, self.top_p_spin, self.min_p_spin,
                  self.top_k_spin, self.dur_spin, self.steps_spin,
                  self.task_combo, self.seed_spin, self.lock_check):
            w.blockSignals(False)
