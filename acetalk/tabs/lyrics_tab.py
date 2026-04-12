import json
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QGroupBox, QRadioButton, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QTextCursor

TEMPLATES_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "templates.json")
)

STRUCTURE_TAGS = [
    "[Intro]", "[Intro: Atmospheric]", "[Verse]", "[Chorus]", "[Chorus: Anthemic]",
    "[Bridge]", "[Bridge: Modulated]", "[Build]", "[Drop]", "[Breakdown]",
    "[Solo: Virtuosic]", "[Drum Break]", "[Guitar Solo]", "[Piano Interlude]",
    "[Outro]", "[Fade Out]", "[Silence]",
]


class _OllamaWorker(QThread):
    token_ready = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, prompt, genre, key, mood, structure, model, subject, name_override):
        super().__init__()
        self.prompt = prompt
        self.genre = genre
        self.key = key
        self.mood = mood
        self.structure = structure
        self.model = model
        self.subject = subject
        self.name_override = name_override

    def run(self):
        from acetalk.core.llm import generate_lyrics
        generate_lyrics(
            prompt=self.prompt,
            genre=self.genre,
            key=self.key,
            mood=self.mood,
            structure=self.structure,
            model=self.model,
            subject=self.subject,
            name_override=self.name_override,
            on_token=lambda t: self.token_ready.emit(t),
        )
        self.finished.emit()


class LyricsTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._templates = self._load_templates()
        self._worker = None
        self._build_ui()
        self._populate_models()

    def _load_templates(self) -> dict:
        try:
            with open(TEMPLATES_PATH) as f:
                return json.load(f)
        except Exception:
            return {"structures": {}, "placeholders": {}}

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Mode toggle
        mode_row = QHBoxLayout()
        self.radio_template = QRadioButton("Template")
        self.radio_ollama = QRadioButton("Ollama Generate")
        self.radio_template.setChecked(True)
        self.radio_template.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.radio_template)
        mode_row.addWidget(self.radio_ollama)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # Template controls
        self.template_group = QGroupBox("Template")
        tpl_layout = QHBoxLayout(self.template_group)
        tpl_layout.addWidget(QLabel("Structure:"))
        self.structure_combo = QComboBox()
        self.structure_combo.addItems(list(self._templates.get("structures", {}).keys()))
        tpl_layout.addWidget(self.structure_combo)
        tpl_layout.addWidget(QLabel("Theme/Tone:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self._templates.get("placeholders", {}).keys()))
        tpl_layout.addWidget(self.theme_combo)
        self.apply_tpl_btn = QPushButton("Apply Template")
        self.apply_tpl_btn.clicked.connect(self._apply_template)
        tpl_layout.addWidget(self.apply_tpl_btn)
        tpl_layout.addStretch()
        root.addWidget(self.template_group)

        # Ollama controls
        self.ollama_group = QGroupBox("Ollama Generate")
        oll_layout = QVBoxLayout(self.ollama_group)

        # Row 1: model + generate button
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        row1.addWidget(self.model_combo)
        self.gen_btn = QPushButton("Generate")
        self.gen_btn.clicked.connect(self._start_generation)
        row1.addWidget(self.gen_btn)
        row1.addStretch()
        oll_layout.addLayout(row1)

        # Row 2: prompt + mood
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Topic:"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Song about... (e.g. goddess of night, lost love)")
        row2.addWidget(self.prompt_input)
        row2.addWidget(QLabel("Mood:"))
        self.mood_input = QLineEdit()
        self.mood_input.setPlaceholderText("e.g. dark, moody, sensual, euphoric")
        self.mood_input.setFixedWidth(200)
        row2.addWidget(self.mood_input)
        oll_layout.addLayout(row2)

        # Row 3: subject + name override
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Subject/Character:"))
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g. Nyx — goddess of night")
        row3.addWidget(self.subject_input)
        row3.addWidget(QLabel("Call them:"))
        self.name_override_input = QLineEdit()
        self.name_override_input.setPlaceholderText("e.g. Nicks  (replaces subject name in lyrics)")
        self.name_override_input.setFixedWidth(200)
        row3.addWidget(self.name_override_input)
        oll_layout.addLayout(row3)

        self.ollama_group.setVisible(False)
        root.addWidget(self.ollama_group)

        # Structure tag toolbar
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("Insert:"))
        for tag in STRUCTURE_TAGS:
            btn = QPushButton(tag)
            btn.setFixedHeight(24)
            btn.clicked.connect(lambda checked, t=tag: self._insert_tag(t))
            tag_row.addWidget(btn)
        tag_row.addStretch()
        root.addLayout(tag_row)

        # Lyrics editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Lyrics appear here. Edit freely.")
        self.editor.textChanged.connect(self._on_text_changed)
        root.addWidget(self.editor)

    def _on_mode_changed(self, template_active: bool):
        self.template_group.setVisible(template_active)
        self.ollama_group.setVisible(not template_active)

    def _populate_models(self):
        from acetalk.core.llm import list_models
        models = list_models()
        self.model_combo.clear()
        self.model_combo.addItems(models)

    def _apply_template(self):
        structure_key = self.structure_combo.currentText()
        theme_key = self.theme_combo.currentText()
        structures = self._templates.get("structures", {})
        placeholders = self._templates.get("placeholders", {}).get(theme_key, {})
        template = structures.get(structure_key, "")
        try:
            filled = template.format(**placeholders)
        except KeyError:
            filled = template
        self.editor.setPlainText(filled)

    def _insert_tag(self, tag: str):
        cursor = self.editor.textCursor()
        cursor.insertText(f"\n{tag}\n")

    def _start_generation(self):
        model = self.model_combo.currentText()
        if not model or "offline" in model.lower() or "no models" in model.lower():
            return
        prompt = self.prompt_input.text().strip() or f"Write a {self.state.genre or 'electronic'} song"
        self.editor.clear()
        self.gen_btn.setEnabled(False)
        self._worker = _OllamaWorker(
            prompt=prompt,
            genre=self.state.genre or "electronic",
            key=f"{self.state.key} {self.state.scale}".strip(),
            mood=self.mood_input.text().strip(),
            structure=self.structure_combo.currentText() if self.structure_combo.count() else "Verse-Chorus",
            model=model,
            subject=self.subject_input.text().strip(),
            name_override=self.name_override_input.text().strip(),
        )
        self._worker.token_ready.connect(self._on_token)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.start()

    def _on_generation_finished(self):
        self.gen_btn.setEnabled(True)
        raw = self.editor.toPlainText()
        # Strip <think>...</think> blocks leaked by reasoning models
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        # Fix literal \n sequences
        cleaned = cleaned.replace("\\n", "\n").replace("\\r", "")
        # Ensure section tags are on their own lines
        cleaned = re.sub(r"\s*(\[[^\]]+\])\s*", r"\n\1\n", cleaned).strip()
        if cleaned != raw:
            self.editor.setPlainText(cleaned)

    @pyqtSlot(str)
    def _on_token(self, token: str):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.editor.setTextCursor(cursor)

    def _on_text_changed(self):
        self.state.lyrics = self.editor.toPlainText()
        self.state_changed.emit()
