import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QComboBox, QGroupBox,
    QListWidget, QListWidgetItem, QLineEdit, QScrollArea,
    QSplitter, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt

GENRES_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "genres.json")
)

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SCALES = ["Major", "Minor", "Harmonic Minor", "Melodic Minor", "Pentatonic Major", "Pentatonic Minor"]
MODES = ["", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Aeolian", "Locrian"]
TIME_SIGS = ["4/4", "3/4", "6/8", "5/4", "7/8", "2/4"]


class StyleTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._genres = self._load_genres()
        self._categories = self._build_categories()
        self._selected_genre = None
        self._genre_buttons: dict[str, QPushButton] = {}  # genre name -> button
        self._build_ui()
        # Show first category
        if self._categories:
            self.category_list.setCurrentRow(0)

    def _load_genres(self) -> list:
        try:
            with open(GENRES_PATH) as f:
                return json.load(f).get("genres", [])
        except Exception:
            return []

    def _build_categories(self) -> list[str]:
        seen = []
        for g in self._genres:
            p = g.get("parent", "Other")
            if p not in seen:
                seen.append(p)
        return sorted(seen)

    def _genres_for_category(self, category: str) -> list:
        return [g for g in self._genres if g.get("parent", "Other") == category]

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Search bar
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter genres…")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_edit)
        search_row.addStretch()
        root.addLayout(search_row)

        # Main splitter: category list | genre grid
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: category list
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(160)
        for cat in self._categories:
            self.category_list.addItem(cat)
        self.category_list.currentTextChanged.connect(self._on_category_selected)
        splitter.addWidget(self.category_list)
        splitter.setCollapsible(0, False)

        # Right: scrollable genre grid
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.genre_grid_widget = QWidget()
        self.genre_grid_layout = QGridLayout(self.genre_grid_widget)
        self.genre_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.genre_grid_widget)
        right_layout.addWidget(scroll)

        splitter.addWidget(right_frame)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)

        # Controls row
        controls = QGroupBox("Style Details")
        ctrl_layout = QHBoxLayout(controls)

        ctrl_layout.addWidget(QLabel("Genre:"))
        self.genre_label = QLabel("—")
        self.genre_label.setStyleSheet("font-weight: bold; color: #80c0ff;")
        ctrl_layout.addWidget(self.genre_label)

        ctrl_layout.addSpacing(12)
        ctrl_layout.addWidget(QLabel("BPM:"))
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(30, 300)
        self.bpm_spin.setValue(self.state.bpm)
        self.bpm_spin.valueChanged.connect(self._on_bpm_changed)
        ctrl_layout.addWidget(self.bpm_spin)

        ctrl_layout.addWidget(QLabel("Key:"))
        self.key_combo = QComboBox()
        self.key_combo.addItems(KEYS)
        self.key_combo.setCurrentText(self.state.key)
        self.key_combo.currentTextChanged.connect(self._on_key_changed)
        ctrl_layout.addWidget(self.key_combo)

        ctrl_layout.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(SCALES)
        self.scale_combo.setCurrentText(self.state.scale)
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        ctrl_layout.addWidget(self.scale_combo)

        ctrl_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODES)
        self.mode_combo.setCurrentText(self.state.mode)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        ctrl_layout.addWidget(self.mode_combo)

        ctrl_layout.addWidget(QLabel("Time:"))
        self.time_combo = QComboBox()
        self.time_combo.addItems(TIME_SIGS)
        self.time_combo.setCurrentText(self.state.time_sig)
        self.time_combo.currentTextChanged.connect(self._on_time_changed)
        ctrl_layout.addWidget(self.time_combo)

        ctrl_layout.addStretch()
        root.addWidget(controls)

        # Description
        self.desc_label = QLabel("Select a genre above.")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #a0a0c0; font-size: 10px; padding: 2px 4px;")
        root.addWidget(self.desc_label)

    def _populate_grid(self, genres: list):
        """Clear and repopulate genre button grid."""
        # Remove all existing widgets
        while self.genre_grid_layout.count():
            item = self.genre_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 4
        for i, genre in enumerate(genres):
            name = genre["name"]
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(self._selected_genre == name)
            btn.clicked.connect(lambda checked, g=genre: self._select_genre(g))
            btn.setMinimumWidth(130)
            self.genre_grid_layout.addWidget(btn, i // cols, i % cols)
            self._genre_buttons[name] = btn

    def _on_category_selected(self, category: str):
        if not category:
            return
        self._genre_buttons.clear()
        self._populate_grid(self._genres_for_category(category))

    def _on_search_changed(self, text: str):
        text = text.strip().lower()
        if not text:
            # Restore current category
            cat = self.category_list.currentItem()
            if cat:
                self._on_category_selected(cat.text())
            return
        # Search all genres
        matches = [g for g in self._genres if text in g["name"].lower()
                   or text in g.get("parent", "").lower()
                   or any(text in t.lower() for t in g.get("tags", []))]
        self._genre_buttons.clear()
        self._populate_grid(matches)

    def _select_genre(self, genre: dict):
        self._selected_genre = genre["name"]
        # Uncheck all visible buttons, check selected
        for name, btn in self._genre_buttons.items():
            btn.setChecked(name == self._selected_genre)

        self.state.genre = genre["name"]
        self.genre_label.setText(genre["name"])
        bpm_mid = (genre["bpm_min"] + genre["bpm_max"]) // 2
        self.bpm_spin.setValue(bpm_mid)
        self.key_combo.setCurrentText(genre.get("default_key", "C"))
        self.scale_combo.setCurrentText(genre.get("default_scale", "Major"))
        self.mode_combo.setCurrentText(genre.get("default_mode", ""))
        self.time_combo.setCurrentText(genre.get("default_time_sig", "4/4"))
        desc = genre.get("description", "")
        tips = genre.get("typical_instruments", [])
        if tips:
            desc += f"\n\nTypical instruments: {', '.join(tips)}"
        self.desc_label.setText(desc)
        self.state_changed.emit()

    def _on_bpm_changed(self, val):
        self.state.bpm = val
        self.state_changed.emit()

    def _on_key_changed(self, val):
        self.state.key = val
        self.state_changed.emit()

    def _on_scale_changed(self, val):
        self.state.scale = val
        self.state_changed.emit()

    def _on_mode_changed(self, val):
        self.state.mode = val
        self.state_changed.emit()

    def _on_time_changed(self, val):
        self.state.time_sig = val
        self.state_changed.emit()
