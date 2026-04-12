from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot


class _SearchWorker(QThread):
    result_ready = pyqtSignal(object)  # dict or None

    def __init__(self, name, source):
        super().__init__()
        self.name = name
        self.source = source

    def run(self):
        from acetalk.core.search import search_artist
        result = search_artist(self.name, source=self.source)
        self.result_ready.emit(result)


VOCAL_GROUPS = {
    "Tone": ["breathy", "raspy", "smooth", "nasal", "powerful", "clear"],
    "Style": ["whispered", "belted", "falsetto", "spoken word", "operatic"],
    "Texture": ["airy", "gritty", "warm", "bright", "vibrato", "melismatic"],
    "Gender": ["male vocal", "female vocal", "androgynous vocal"],
}


class VocalistTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._chips = {}
        self._worker = None
        self._last_descriptors = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Search row
        search_group = QGroupBox("Artist Search")
        search_layout = QHBoxLayout(search_group)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Artist or vocal style...")
        self.search_input.returnPressed.connect(self._do_search)
        self.source_combo = QComboBox()
        self.source_combo.addItems(["both", "local", "web"])
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._do_search)
        for w in [self.search_input, self.source_combo, self.search_btn]:
            search_layout.addWidget(w)
        root.addWidget(search_group)

        # Results card
        self.result_group = QGroupBox("Result")
        result_layout = QVBoxLayout(self.result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(100)
        self.use_btn = QPushButton("Use These Descriptors")
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._use_descriptors)
        result_layout.addWidget(self.result_text)
        result_layout.addWidget(self.use_btn)
        root.addWidget(self.result_group)

        # Descriptor picker
        picker_group = QGroupBox("Vocal Descriptor Picker")
        picker_layout = QVBoxLayout(picker_group)
        for group_name, keywords in VOCAL_GROUPS.items():
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(f"{group_name}:"))
            for kw in keywords:
                chip = QPushButton(kw)
                chip.setCheckable(True)
                chip.setFixedHeight(28)
                chip.toggled.connect(self._on_chip_toggled)
                self._chips[kw] = chip
                row_layout.addWidget(chip)
            row_layout.addStretch()
            picker_layout.addWidget(row_widget)
        root.addWidget(picker_group)

        # Selected tags display
        sel_group = QGroupBox("Selected Vocal Tags")
        sel_layout = QHBoxLayout(sel_group)
        self.selected_label = QLabel("(none)")
        self.selected_label.setWordWrap(True)
        sel_layout.addWidget(self.selected_label)
        root.addWidget(sel_group)

        root.addStretch()

    def _do_search(self):
        name = self.search_input.text().strip()
        if not name:
            return
        self.search_btn.setEnabled(False)
        self.result_text.setPlainText("Searching...")
        source = self.source_combo.currentText()
        self._worker = _SearchWorker(name, source)
        self._worker.result_ready.connect(self._on_result)
        self._worker.start()

    @pyqtSlot(object)
    def _on_result(self, result):
        self.search_btn.setEnabled(True)
        if result is None:
            self.result_text.setPlainText("No results found.")
            self.use_btn.setEnabled(False)
            return
        source_note = f" [{result.get('_source', '')}]" if '_source' in result else ""
        text = (
            f"{result['name']}{source_note}\n"
            f"Range: {result.get('range', '—')}  "
            f"Key: {result.get('preferred_key', '—')}  "
            f"Style: {result.get('style', '—')}\n"
            f"Known for: {', '.join(result.get('known_for', []))}\n"
            f"ACE-Step: {', '.join(result.get('ace_step_descriptors', []))}"
        )
        self.result_text.setPlainText(text)
        self._last_descriptors = result.get("ace_step_descriptors", [])
        self.use_btn.setEnabled(bool(self._last_descriptors))

    def _use_descriptors(self):
        for kw, chip in self._chips.items():
            chip.setChecked(kw in self._last_descriptors)
        self._sync_state()

    def _on_chip_toggled(self):
        self._sync_state()

    def _sync_state(self):
        selected = [kw for kw, chip in self._chips.items() if chip.isChecked()]
        self.state.vocal_tags = selected
        self.selected_label.setText(", ".join(selected) if selected else "(none)")
        self.state_changed.emit()
