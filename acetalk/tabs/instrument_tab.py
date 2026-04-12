import json
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QPushButton, QLabel, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

INSTRUMENTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "instruments.json")
)


class ChipButton(QPushButton):
    """Toggleable chip-style button."""
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setFixedHeight(28)
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("background:#1976d2;color:white;border-radius:14px;padding:0 10px;")
        else:
            self.setStyleSheet("background:#37474f;color:#ccc;border-radius:14px;padding:0 10px;")


class InstrumentTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._data = self._load_data()
        self._mod_chips = {}
        self._build_ui()

    def _load_data(self) -> dict:
        try:
            with open(INSTRUMENTS_PATH) as f:
                return json.load(f)
        except Exception:
            return {"categories": {}, "modifiers": {}}

    def _build_ui(self):
        root = QHBoxLayout(self)

        # Left: category list
        left = QVBoxLayout()
        left.addWidget(QLabel("Category"))
        self.cat_list = QListWidget()
        self.cat_list.setFixedWidth(180)
        for cat in self._data.get("categories", {}):
            self.cat_list.addItem(cat)
        self.cat_list.currentTextChanged.connect(self._on_category_changed)
        left.addWidget(self.cat_list)
        root.addLayout(left)

        # Middle: instruments + modifiers
        mid = QVBoxLayout()

        mid.addWidget(QLabel("Instruments (double-click or use Add button)"))
        self.inst_list = QListWidget()
        self.inst_list.itemDoubleClicked.connect(self._add_instrument)
        mid.addWidget(self.inst_list)

        add_btn = QPushButton("Add Selected →")
        add_btn.clicked.connect(lambda: self._add_instrument(self.inst_list.currentItem()))
        mid.addWidget(add_btn)

        # Modifier chips
        mod_group = QGroupBox("Modifiers (apply to next added)")
        mod_layout = QVBoxLayout(mod_group)
        modifiers = self._data.get("modifiers", {})
        for group_name, keywords in modifiers.items():
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(f"{group_name.title()}:"))
            for kw in keywords:
                chip = ChipButton(kw)
                row_layout.addWidget(chip)
                self._mod_chips[kw] = chip
            row_layout.addStretch()
            mod_layout.addWidget(row_widget)
        mid.addWidget(mod_group)
        root.addLayout(mid)

        # Right: selected instruments
        right = QVBoxLayout()
        right.addWidget(QLabel("Selected Instruments"))
        self.selected_list = QListWidget()
        right.addWidget(self.selected_list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_instrument)
        right.addWidget(remove_btn)
        root.addLayout(right)

        # Select first category
        if self.cat_list.count() > 0:
            self.cat_list.setCurrentRow(0)

    def _on_category_changed(self, cat_name: str):
        self.inst_list.clear()
        categories = self._data.get("categories", {})
        cat_data = categories.get(cat_name, {})
        for subcategory, items in cat_data.items():
            for item in items:
                self.inst_list.addItem(item)

    def _get_active_modifiers(self) -> list[str]:
        return [kw for kw, chip in self._mod_chips.items() if chip.isChecked()]

    def _add_instrument(self, item):
        if item is None:
            return
        base = item.text()
        mods = self._get_active_modifiers()
        if mods:
            phrase = f"{', '.join(mods)} {base}"
        else:
            phrase = base
        self.selected_list.addItem(phrase)
        self.state.instruments.append(phrase)
        self.state_changed.emit()

    def _remove_instrument(self):
        row = self.selected_list.currentRow()
        if row >= 0:
            self.selected_list.takeItem(row)
            if row < len(self.state.instruments):
                self.state.instruments.pop(row)
            self.state_changed.emit()

    def load_from_state(self):
        """Reload the selected list from state (used when loading a preset)."""
        self.selected_list.clear()
        for phrase in self.state.instruments:
            self.selected_list.addItem(phrase)
