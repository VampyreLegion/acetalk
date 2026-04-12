from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QFrame, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..core.state import SessionState
from ..core.prompt_builder import build_caption

CARD_STYLE = """
    QFrame {{
        background: #1e1e2e;
        border: 1px solid #3a3a5c;
        border-radius: 6px;
    }}
"""
LABEL_STYLE = "color: #a0a0d0; font-size: 9px; font-weight: bold; border: none;"
INPUT_STYLE = """
    background: #2a2a3e;
    color: #e0e0f0;
    border: 1px solid #4a4a6c;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
"""
TITLE_STYLE = "color: #c0b0ff; font-size: 13px; font-weight: bold; padding-bottom: 4px; border: none;"


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setStyleSheet(CARD_STYLE.format())
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 8, 12, 10)
    layout.setSpacing(6)
    hdr = QLabel(title)
    hdr.setStyleSheet(LABEL_STYLE)
    layout.addWidget(hdr)
    return frame, layout


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #8080a0; font-size: 10px; border: none;")
    return lbl


class OverviewTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state: SessionState, parent=None):
        super().__init__(parent)
        self.state = state
        self._updating = False
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #13131f; }")

        container = QWidget()
        container.setStyleSheet("background: #13131f;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Song Overview")
        title.setStyleSheet(TITLE_STYLE)
        layout.addWidget(title)

        layout.addWidget(self._build_style_card())
        layout.addWidget(self._build_instruments_card())
        layout.addWidget(self._build_vocals_card())
        layout.addWidget(self._build_lyrics_card())
        layout.addWidget(self._build_params_card())
        layout.addWidget(self._build_caption_card())
        layout.addWidget(self._build_metadata_card())
        layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ── Style card ──────────────────────────────────────────────────────────

    def _build_style_card(self):
        frame, layout = _card("STYLE")

        row1 = QHBoxLayout()
        row2 = QHBoxLayout()

        # Genre
        col_genre = QVBoxLayout()
        col_genre.addWidget(_label("Genre"))
        self.genre_edit = QLineEdit()
        self.genre_edit.setStyleSheet(INPUT_STYLE)
        self.genre_edit.setPlaceholderText("e.g. Psytrance")
        col_genre.addWidget(self.genre_edit)
        row1.addLayout(col_genre)

        # BPM
        col_bpm = QVBoxLayout()
        col_bpm.addWidget(_label("BPM"))
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(40, 300)
        self.bpm_spin.setStyleSheet(INPUT_STYLE)
        col_bpm.addWidget(self.bpm_spin)
        row1.addLayout(col_bpm)

        # Key
        col_key = QVBoxLayout()
        col_key.addWidget(_label("Key"))
        self.key_edit = QLineEdit()
        self.key_edit.setStyleSheet(INPUT_STYLE)
        self.key_edit.setPlaceholderText("e.g. A")
        col_key.addWidget(self.key_edit)
        row1.addLayout(col_key)

        # Scale
        col_scale = QVBoxLayout()
        col_scale.addWidget(_label("Scale"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Major", "Minor", "Dorian", "Phrygian", "Lydian",
                                   "Mixolydian", "Locrian", "Harmonic Minor", "Pentatonic"])
        self.scale_combo.setStyleSheet(INPUT_STYLE)
        col_scale.addWidget(self.scale_combo)
        row2.addLayout(col_scale)

        # Mode
        col_mode = QVBoxLayout()
        col_mode.addWidget(_label("Mode"))
        self.mode_edit = QLineEdit()
        self.mode_edit.setStyleSheet(INPUT_STYLE)
        self.mode_edit.setPlaceholderText("e.g. Phrygian")
        col_mode.addWidget(self.mode_edit)
        row2.addLayout(col_mode)

        # Time Sig
        col_ts = QVBoxLayout()
        col_ts.addWidget(_label("Time Signature"))
        self.timesig_combo = QComboBox()
        self.timesig_combo.addItems(["4/4", "3/4", "6/8", "2/4", "5/4", "7/8"])
        self.timesig_combo.setStyleSheet(INPUT_STYLE)
        col_ts.addWidget(self.timesig_combo)
        row2.addLayout(col_ts)

        layout.addLayout(row1)
        layout.addLayout(row2)

        # Connect signals
        self.genre_edit.textChanged.connect(self._on_style_changed)
        self.bpm_spin.valueChanged.connect(self._on_style_changed)
        self.key_edit.textChanged.connect(self._on_style_changed)
        self.scale_combo.currentTextChanged.connect(self._on_style_changed)
        self.mode_edit.textChanged.connect(self._on_style_changed)
        self.timesig_combo.currentTextChanged.connect(self._on_style_changed)

        return frame

    # ── Instruments card ─────────────────────────────────────────────────────

    def _build_instruments_card(self):
        frame, layout = _card("INSTRUMENTS")
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(_label("One instrument per line"))
        self.instruments_count = QLabel("")
        self.instruments_count.setStyleSheet("color: #6080ff; font-size: 10px; border: none;")
        hdr_row.addStretch()
        hdr_row.addWidget(self.instruments_count)
        layout.addLayout(hdr_row)
        self.instruments_edit = QTextEdit()
        self.instruments_edit.setStyleSheet(INPUT_STYLE)
        self.instruments_edit.setMinimumHeight(160)
        self.instruments_edit.setPlaceholderText("TB-303 synth bass\nlayered analog pads\n...")
        layout.addWidget(self.instruments_edit)
        self.instruments_edit.textChanged.connect(self._on_instruments_changed)
        return frame

    # ── Vocals card ──────────────────────────────────────────────────────────

    def _build_vocals_card(self):
        frame, layout = _card("VOCALS")
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(_label("Comma separated tags  (e.g.  breathy, female vocal, airy)"))
        self.vocals_count = QLabel("")
        self.vocals_count.setStyleSheet("color: #6080ff; font-size: 10px; border: none;")
        hdr_row.addStretch()
        hdr_row.addWidget(self.vocals_count)
        layout.addLayout(hdr_row)
        self.vocals_edit = QLineEdit()
        self.vocals_edit.setStyleSheet(INPUT_STYLE)
        self.vocals_edit.setPlaceholderText("breathy, female vocal, airy")
        layout.addWidget(self.vocals_edit)
        self.vocals_edit.textChanged.connect(self._on_vocals_changed)
        return frame

    # ── Lyrics card ──────────────────────────────────────────────────────────

    def _build_lyrics_card(self):
        frame, layout = _card("LYRICS")
        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setStyleSheet(INPUT_STYLE)
        self.lyrics_edit.setMinimumHeight(180)
        self.lyrics_edit.setPlaceholderText("[Intro]\n...\n[Verse]\n...\n[Chorus]\n...")
        layout.addWidget(self.lyrics_edit)
        self.lyrics_edit.textChanged.connect(self._on_lyrics_changed)
        return frame

    # ── Parameters card ───────────────────────────────────────────────────────

    def _build_params_card(self):
        frame, layout = _card("GENERATION PARAMETERS")

        def spin_row(label_text, widget):
            row = QHBoxLayout()
            lbl = _label(label_text)
            lbl.setFixedWidth(120)
            row.addWidget(lbl)
            row.addWidget(widget)
            row.addStretch()
            return row

        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 20.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setStyleSheet(INPUT_STYLE)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.1, 2.0)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setDecimals(2)
        self.temp_spin.setStyleSheet(INPUT_STYLE)

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setDecimals(2)
        self.top_p_spin.setStyleSheet(INPUT_STYLE)

        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(0, 200)
        self.top_k_spin.setStyleSheet(INPUT_STYLE)

        self.min_p_spin = QDoubleSpinBox()
        self.min_p_spin.setRange(0.0, 1.0)
        self.min_p_spin.setSingleStep(0.01)
        self.min_p_spin.setDecimals(3)
        self.min_p_spin.setStyleSheet(INPUT_STYLE)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 300)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.setStyleSheet(INPUT_STYLE)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 150)
        self.steps_spin.setStyleSheet(INPUT_STYLE)

        self.task_combo = QComboBox()
        self.task_combo.addItems(["text2music", "lego", "repaint", "extract"])
        self.task_combo.setStyleSheet(INPUT_STYLE)

        # Two-column grid
        grid = QHBoxLayout()
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()

        col_left.addLayout(spin_row("cfg_scale", self.cfg_spin))
        col_left.addLayout(spin_row("temperature", self.temp_spin))
        col_left.addLayout(spin_row("top_p", self.top_p_spin))
        col_left.addLayout(spin_row("top_k", self.top_k_spin))
        col_right.addLayout(spin_row("min_p", self.min_p_spin))
        col_right.addLayout(spin_row("duration", self.duration_spin))
        col_right.addLayout(spin_row("steps", self.steps_spin))
        col_right.addLayout(spin_row("task_type", self.task_combo))

        grid.addLayout(col_left)
        grid.addSpacing(20)
        grid.addLayout(col_right)
        layout.addLayout(grid)

        for w in [self.cfg_spin, self.temp_spin, self.top_p_spin, self.top_k_spin,
                  self.min_p_spin, self.duration_spin, self.steps_spin]:
            w.valueChanged.connect(self._on_params_changed)
        self.task_combo.currentTextChanged.connect(self._on_params_changed)

        return frame

    # ── Caption display (read-only) ───────────────────────────────────────────

    def _build_caption_card(self):
        frame, layout = _card("ASSEMBLED CAPTION  (sent to ACE-Step)")
        self.caption_display = QTextEdit()
        self.caption_display.setReadOnly(True)
        self.caption_display.setFixedHeight(60)
        self.caption_display.setStyleSheet(INPUT_STYLE + "color: #9aefb0;")
        layout.addWidget(self.caption_display)
        return frame

    # ── Metadata card ─────────────────────────────────────────────────────────

    def _build_metadata_card(self):
        frame, layout = _card("SONG METADATA  (embedded into exported MP3)")

        row1 = QHBoxLayout()
        c1 = QVBoxLayout()
        c1.addWidget(_label("Song Title"))
        self.meta_title = QLineEdit()
        self.meta_title.setStyleSheet(INPUT_STYLE)
        self.meta_title.setPlaceholderText("e.g. Nyx — Queen of Night")
        c1.addWidget(self.meta_title)
        row1.addLayout(c1)

        c2 = QVBoxLayout()
        c2.addWidget(_label("Artist"))
        self.meta_artist = QLineEdit()
        self.meta_artist.setStyleSheet(INPUT_STYLE)
        self.meta_artist.setPlaceholderText("e.g. Legion & Nyx")
        c2.addWidget(self.meta_artist)
        row1.addLayout(c2)

        c3 = QVBoxLayout()
        c3.addWidget(_label("Album"))
        self.meta_album = QLineEdit()
        self.meta_album.setStyleSheet(INPUT_STYLE)
        self.meta_album.setPlaceholderText("e.g. Nyx Studios Vol. 1")
        c3.addWidget(self.meta_album)
        row1.addLayout(c3)

        c4 = QVBoxLayout()
        c4.addWidget(_label("Year"))
        self.meta_year = QLineEdit()
        self.meta_year.setStyleSheet(INPUT_STYLE)
        self.meta_year.setPlaceholderText("2026")
        self.meta_year.setFixedWidth(70)
        c4.addWidget(self.meta_year)
        row1.addLayout(c4)

        layout.addLayout(row1)

        row2 = QHBoxLayout()
        c5 = QVBoxLayout()
        c5.addWidget(_label("Genres (ID3 tags)"))
        self.meta_genres = QLineEdit()
        self.meta_genres.setStyleSheet(INPUT_STYLE)
        self.meta_genres.setPlaceholderText("e.g. Psytrance, Electronic, Ambient  (comma separated)")
        c5.addWidget(self.meta_genres)
        row2.addLayout(c5)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        c6 = QVBoxLayout()
        c6.addWidget(_label("Description / Comment"))
        self.meta_desc = QLineEdit()
        self.meta_desc.setStyleSheet(INPUT_STYLE)
        self.meta_desc.setPlaceholderText("Optional notes or liner info")
        c6.addWidget(self.meta_desc)
        row3.addLayout(c6)
        layout.addLayout(row3)

        for w in [self.meta_title, self.meta_artist, self.meta_album,
                  self.meta_year, self.meta_genres, self.meta_desc]:
            w.textChanged.connect(self._on_meta_changed)

        return frame

    def _on_meta_changed(self):
        if self._updating:
            return
        self.state.song_title = self.meta_title.text().strip()
        self.state.artist = self.meta_artist.text().strip()
        self.state.album = self.meta_album.text().strip()
        self.state.year = self.meta_year.text().strip()
        self.state.genre_tags = self.meta_genres.text().strip()
        self.state.description = self.meta_desc.text().strip()
        self.state_changed.emit()

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_style_changed(self):
        if self._updating:
            return
        self.state.genre = self.genre_edit.text().strip()
        self.state.bpm = self.bpm_spin.value()
        self.state.key = self.key_edit.text().strip()
        self.state.scale = self.scale_combo.currentText()
        self.state.mode = self.mode_edit.text().strip()
        self.state.time_sig = self.timesig_combo.currentText()
        self._refresh_caption()
        self.state_changed.emit()

    def _on_instruments_changed(self):
        if self._updating:
            return
        lines = self.instruments_edit.toPlainText().splitlines()
        self.state.instruments = [l.strip() for l in lines if l.strip()]
        self._refresh_caption()
        self.state_changed.emit()

    def _on_vocals_changed(self):
        if self._updating:
            return
        raw = self.vocals_edit.text()
        # Split by comma to preserve multi-word tags like "female vocal"
        tags = [t.strip() for t in raw.split(",") if t.strip()]
        self.state.vocal_tags = tags
        self._refresh_caption()
        self.state_changed.emit()

    def _on_lyrics_changed(self):
        if self._updating:
            return
        self.state.lyrics = self.lyrics_edit.toPlainText()
        self.state_changed.emit()

    def _on_params_changed(self):
        if self._updating:
            return
        self.state.cfg_scale = self.cfg_spin.value()
        self.state.temperature = self.temp_spin.value()
        self.state.top_p = self.top_p_spin.value()
        self.state.top_k = self.top_k_spin.value()
        self.state.min_p = self.min_p_spin.value()
        self.state.duration = self.duration_spin.value()
        self.state.steps = self.steps_spin.value()
        self.state.task_type = self.task_combo.currentText()
        self.state_changed.emit()

    def _refresh_caption(self):
        self.caption_display.setPlainText(build_caption(self.state))

    # ── Called by main_window whenever any tab changes state ─────────────────

    def refresh(self):
        self._updating = True
        try:
            self.genre_edit.setText(self.state.genre)
            self.bpm_spin.setValue(self.state.bpm)
            self.key_edit.setText(self.state.key)
            idx = self.scale_combo.findText(self.state.scale)
            if idx >= 0:
                self.scale_combo.setCurrentIndex(idx)
            self.mode_edit.setText(self.state.mode)
            ts_idx = self.timesig_combo.findText(self.state.time_sig)
            if ts_idx >= 0:
                self.timesig_combo.setCurrentIndex(ts_idx)

            self.instruments_edit.setPlainText("\n".join(self.state.instruments))
            n_inst = len(self.state.instruments)
            self.instruments_count.setText(f"{n_inst} selected" if n_inst else "")
            self.vocals_edit.setText(", ".join(self.state.vocal_tags))
            n_voc = len(self.state.vocal_tags)
            self.vocals_count.setText(f"{n_voc} tags" if n_voc else "")
            self.lyrics_edit.setPlainText(self.state.lyrics)

            self.cfg_spin.setValue(self.state.cfg_scale)
            self.temp_spin.setValue(self.state.temperature)
            self.top_p_spin.setValue(self.state.top_p)
            self.top_k_spin.setValue(self.state.top_k)
            self.min_p_spin.setValue(self.state.min_p)
            self.duration_spin.setValue(self.state.duration)
            self.steps_spin.setValue(self.state.steps)
            tt_idx = self.task_combo.findText(self.state.task_type)
            if tt_idx >= 0:
                self.task_combo.setCurrentIndex(tt_idx)

            self.caption_display.setPlainText(build_caption(self.state))

            self.meta_title.setText(self.state.song_title)
            self.meta_artist.setText(self.state.artist)
            self.meta_album.setText(self.state.album)
            self.meta_year.setText(self.state.year)
            self.meta_genres.setText(self.state.genre_tags)
            self.meta_desc.setText(self.state.description)
        finally:
            self._updating = False
