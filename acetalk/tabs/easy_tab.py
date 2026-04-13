"""
Easy tab — enter a band + vocalist, click Research & Generate,
get a fully populated caption and lyrics ready to send to ACE-Step.
Results are fully editable and push back into session state.
"""
import json
import logging
import os
import re

import requests

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot, Qt
from PyQt6.QtGui import QFont

from ..core.state import SessionState
from ..core.llm import list_models

logger = logging.getLogger(__name__)

CARD_STYLE = """
    QFrame {
        background: #1e1e2e;
        border: 1px solid #3a3a5c;
        border-radius: 6px;
    }
"""
INPUT_STYLE = """
    background: #2a2a3e;
    color: #e0e0f0;
    border: 1px solid #4a4a6c;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
"""
LABEL_STYLE = "color: #a0a0d0; font-size: 10px; border: none;"
STATUS_STYLE = "color: #80c0ff; font-size: 10px; font-style: italic; border: none;"


def _web_search(query: str) -> str:
    """Brave first, DDG fallback. Returns combined text or empty string."""
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if brave_key:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
                params={"q": query, "count": 6},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("web", {}).get("results", [])
            return " ".join(r.get("description", "") for r in results)
        except Exception as exc:
            logger.warning("Brave failed: %s", exc)
    try:
        from duckduckgo_search import DDGS
        with DDGS(timeout=10) as ddgs:
            results = ddgs.text(query, max_results=6)
            return " ".join(r.get("body", "") for r in results)
    except Exception as exc:
        logger.warning("DDG failed: %s", exc)
    return ""


class _ResearchWorker(QThread):
    status_update = pyqtSignal(str)
    result_ready = pyqtSignal(str, str)   # (caption, lyrics)
    error = pyqtSignal(str)

    def __init__(self, band, vocalist, topic, mood, name_override, structure, model, ollama_url):
        super().__init__()
        self.band = band
        self.vocalist = vocalist
        self.topic = topic
        self.mood = mood
        self.name_override = name_override
        self.structure = structure
        self.model = model
        self.ollama_url = ollama_url

    def run(self):
        try:
            # 1. Research band
            self.status_update.emit(f"Researching band: {self.band}…")
            band_text = _web_search(
                f"{self.band} music genre BPM style instruments typical tempo key signature"
            )

            # 2. Research vocalist
            self.status_update.emit(f"Researching vocalist: {self.vocalist}…")
            vocalist_text = _web_search(
                f"{self.vocalist} vocal style tone range technique singing characteristics"
            )

            # 3. Synthesise with Ollama
            self.status_update.emit("Generating with Ollama…")

            name_instruction = (
                f"In the lyrics, refer to the subject as '{self.name_override}' — do not use any other name."
                if self.name_override else ""
            )
            topic_instruction = f"Song topic: {self.topic}." if self.topic else ""
            mood_instruction = f"Mood/vibe: {self.mood}." if self.mood else ""

            prompt = f"""You are a professional music producer and lyricist specialising in ACE-Step 1.5 AI music generation.

BAND RESEARCH for "{self.band}":
{band_text[:1500]}

VOCALIST RESEARCH for "{self.vocalist}":
{vocalist_text[:1000]}

TASK:
Using the research above, create a complete ACE-Step 1.5 music prompt.
{topic_instruction}
{mood_instruction}
{name_instruction}
Song structure: {self.structure}

ACE-Step structural tags you MUST use to control song flow and energy:
  Structure:  [Intro]  [Verse]  [Pre-Chorus]  [Chorus]  [Bridge]  [Outro]
  Energy:     [Build]  [Drop]  [Breakdown]  [Fade Out]  [Silence]
  Performance:[Guitar Solo]  [Piano Interlude]  [Drum Break]  [Solo]  [Instrumental]
  Qualifiers: add ": descriptor" for energy/mood — e.g.
              [Intro: Atmospheric]  [Chorus: Anthemic]  [Build: Heavy]
              [Drop: Euphoric]  [Verse: Intimate]  [Bridge: Haunting]
              [Outro: Fading]  [Solo: Virtuosic]  [Breakdown: Sparse]

Rules:
- Every section MUST start with a tag on its own line
- Choose tags that match the genre and mood (e.g. EDM needs [Build] and [Drop], rock needs [Guitar Solo])
- Use qualifier variants to set energy and production character for each section
- No plain text before the first tag, no explanations inside the lyrics

Return ONLY valid JSON with exactly two keys:
- "caption": a comma-separated string of ACE-Step style tags (genre, BPM, key, scale, mode, time signature, instruments, vocal descriptors — modelled on {self.band}'s sound and {self.vocalist}'s vocal style)
- "lyrics": full structured song using the tags above — no text outside section tags and lyric lines

Return ONLY the JSON object. No explanation, no markdown fences.
"""
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
                timeout=120,
            )
            raw = resp.json().get("response", "{}")
            # Strip think blocks if reasoning model
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            data = json.loads(raw)
            caption = data.get("caption", "")
            lyrics = data.get("lyrics", "")
            if not caption and not lyrics:
                self.error.emit("Ollama returned empty result. Try a different model or simpler inputs.")
                return
            # Fix literal \n sequences that some models embed in JSON strings
            lyrics = lyrics.replace("\\n", "\n").replace("\\r", "").strip()
            # Ensure each section tag starts on its own line
            lyrics = re.sub(r"\s*(\[[^\]]+\])\s*", r"\n\1\n", lyrics).strip()
            self.status_update.emit("Done.")
            self.result_ready.emit(caption, lyrics)
        except Exception as exc:
            self.error.emit(str(exc))


class EasyTab(QWidget):
    state_changed = pyqtSignal()
    go_to_overview = pyqtSignal()   # tells main_window to switch to Overview tab

    def __init__(self, state: SessionState, config: dict, parent=None):
        super().__init__(parent)
        self.state = state
        self.config = config
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        # Title
        title = QLabel("Easy Mode — Research & Generate")
        title.setFont(QFont("monospace", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #c0b0ff; border: none;")
        root.addWidget(title)

        sub = QLabel("Enter a band and vocalist — AceTalk will research both and build your full prompt automatically.")
        sub.setStyleSheet("color: #8080a0; font-size: 10px; border: none;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        # ── Input card ────────────────────────────────────────────────────────
        input_card = QFrame()
        input_card.setStyleSheet(CARD_STYLE)
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(12, 10, 12, 12)
        input_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(self._lbl("Band / Artist"))
        self.band_edit = QLineEdit()
        self.band_edit.setStyleSheet(INPUT_STYLE)
        self.band_edit.setPlaceholderText("e.g. Pink Floyd, Massive Attack, Billie Eilish")
        row1.addWidget(self.band_edit)
        input_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(self._lbl("Lead Vocalist"))
        self.vocalist_edit = QLineEdit()
        self.vocalist_edit.setStyleSheet(INPUT_STYLE)
        self.vocalist_edit.setPlaceholderText("e.g. Roger Waters, Elizabeth Fraser, Billie Eilish")
        row2.addWidget(self.vocalist_edit)
        input_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(self._lbl("Song Topic"))
        self.topic_edit = QLineEdit()
        self.topic_edit.setStyleSheet(INPUT_STYLE)
        self.topic_edit.setPlaceholderText("e.g. goddess of night, lost in space, forbidden love")
        row3.addWidget(self.topic_edit)
        input_layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(self._lbl("Mood"))
        self.mood_edit = QLineEdit()
        self.mood_edit.setStyleSheet(INPUT_STYLE)
        self.mood_edit.setPlaceholderText("e.g. dark, euphoric, melancholic, sensual")
        row4.addWidget(self.mood_edit)
        row4.addSpacing(16)
        row4.addWidget(self._lbl("Call subject:"))
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(INPUT_STYLE)
        self.name_edit.setPlaceholderText("e.g. Nicks  (use this name in lyrics)")
        self.name_edit.setFixedWidth(180)
        row4.addWidget(self.name_edit)
        input_layout.addLayout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(self._lbl("Structure"))
        self.structure_combo = QComboBox()
        self.structure_combo.setStyleSheet(INPUT_STYLE)
        self.structure_combo.addItems([
            "Verse-Chorus", "Verse-Chorus-Bridge", "Verse-Pre-Chorus-Chorus",
            "Through-Composed", "Extended Club Edit"
        ])
        row5.addWidget(self.structure_combo)
        row5.addSpacing(16)
        row5.addWidget(self._lbl("Ollama Model"))
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(INPUT_STYLE)
        self.model_combo.setMinimumWidth(200)
        row5.addWidget(self.model_combo)
        row5.addStretch()
        input_layout.addLayout(row5)

        # Generate button + status
        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("Research & Generate")
        self.gen_btn.setFixedHeight(32)
        self.gen_btn.setStyleSheet("""
            QPushButton {
                background: #3a3aaf;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover { background: #5050cf; }
            QPushButton:disabled { background: #2a2a5f; color: #666; }
        """)
        self.gen_btn.clicked.connect(self._start)
        btn_row.addWidget(self.gen_btn)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(STATUS_STYLE)
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()
        input_layout.addLayout(btn_row)

        root.addWidget(input_card)

        # ── Results card ──────────────────────────────────────────────────────
        results_card = QFrame()
        results_card.setStyleSheet(CARD_STYLE)
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(12, 10, 12, 12)
        results_layout.setSpacing(8)

        res_hdr = QHBoxLayout()
        res_lbl = QLabel("GENERATED PROMPT  (editable)")
        res_lbl.setStyleSheet("color: #a0a0d0; font-size: 9px; font-weight: bold; border: none;")
        res_hdr.addWidget(res_lbl)
        res_hdr.addStretch()
        self.apply_btn = QPushButton("Send to Overview for Editing →")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: #1a6a3a;
                color: white;
                border-radius: 4px;
                padding: 3px 12px;
                font-size: 10px;
            }
            QPushButton:hover { background: #2a8a50; }
        """)
        self.apply_btn.clicked.connect(self._apply_to_session)
        res_hdr.addWidget(self.apply_btn)
        results_layout.addLayout(res_hdr)

        results_layout.addWidget(self._lbl("Caption / Tags"))
        self.caption_edit = QTextEdit()
        self.caption_edit.setStyleSheet(INPUT_STYLE)
        self.caption_edit.setFixedHeight(70)
        self.caption_edit.setPlaceholderText("Caption will appear here after generation…")
        results_layout.addWidget(self.caption_edit)

        results_layout.addWidget(self._lbl("Lyrics"))
        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setStyleSheet(INPUT_STYLE)
        self.lyrics_edit.setMinimumHeight(220)
        self.lyrics_edit.setPlaceholderText("Lyrics will appear here after generation…")
        results_layout.addWidget(self.lyrics_edit)

        root.addWidget(results_card)

        self._populate_models()

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(LABEL_STYLE)
        lbl.setFixedWidth(110)
        return lbl

    def _populate_models(self):
        models = list_models()
        self.model_combo.clear()
        self.model_combo.addItems(models)

    def _start(self):
        band = self.band_edit.text().strip()
        vocalist = self.vocalist_edit.text().strip()
        if not band or not vocalist:
            self.status_label.setText("Enter both a band and a vocalist first.")
            return
        model = self.model_combo.currentText()
        if not model or "offline" in model.lower():
            self.status_label.setText("Ollama is offline — start a model first.")
            return

        self.gen_btn.setEnabled(False)
        self.caption_edit.clear()
        self.lyrics_edit.clear()
        ollama_url = self.config.get("ollama_url", "http://localhost:11434")

        self._worker = _ResearchWorker(
            band=band,
            vocalist=vocalist,
            topic=self.topic_edit.text().strip(),
            mood=self.mood_edit.text().strip(),
            name_override=self.name_edit.text().strip(),
            structure=self.structure_combo.currentText(),
            model=model,
            ollama_url=ollama_url,
        )
        self._worker.status_update.connect(self._on_status)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @pyqtSlot(str)
    def _on_status(self, msg: str):
        self.status_label.setText(msg)

    @pyqtSlot(str, str)
    def _on_result(self, caption: str, lyrics: str):
        self.gen_btn.setEnabled(True)
        self.status_label.setText("Ready — edit below then click Apply to Session.")
        self.caption_edit.setPlainText(caption)
        self.lyrics_edit.setPlainText(lyrics)

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self.gen_btn.setEnabled(True)
        self.status_label.setText(f"Error: {msg}")

    def _apply_to_session(self):
        """Parse generated caption into state fields, then switch to Overview for editing."""
        caption = self.caption_edit.toPlainText().strip()
        lyrics = self.lyrics_edit.toPlainText().strip()
        if not caption and not lyrics:
            return

        VOCAL_KEYWORDS = {
            "breathy", "raspy", "smooth", "nasal", "powerful", "clear",
            "whispered", "belted", "falsetto", "spoken word", "operatic",
            "airy", "gritty", "warm", "bright", "vibrato", "melismatic",
            "female vocal", "male vocal", "androgynous vocal", "close-mic vocal",
            "soulful", "husky", "soft", "intimate",
        }
        SCALES = {"major", "minor", "dorian", "phrygian", "lydian",
                  "mixolydian", "locrian", "harmonic minor", "pentatonic"}
        NOTES = {"C", "C#", "Db", "D", "D#", "Eb", "E", "F",
                 "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"}
        TIME_SIGS = {"4/4", "3/4", "6/8", "2/4", "5/4", "7/8", "12/8"}

        parts = [p.strip() for p in caption.split(",") if p.strip()]
        instruments = []
        vocal_tags = []
        genre = ""
        bpm = None
        key = ""
        scale = ""
        mode = ""
        time_sig = ""

        for part in parts:
            low = part.lower()

            # BPM  e.g. "145 BPM"
            bpm_m = re.search(r"(\d{2,3})\s*bpm", low)
            if bpm_m:
                bpm = int(bpm_m.group(1))
                continue

            # Time signature  e.g. "4/4 time" or just "4/4"
            ts_m = re.search(r"(\d/\d)", part)
            if ts_m and ts_m.group(1) in TIME_SIGS:
                time_sig = ts_m.group(1)
                continue

            # Mode  e.g. "Phrygian mode"
            mode_m = re.search(r"(phrygian|dorian|lydian|mixolydian|locrian)\s*mode?", low)
            if mode_m:
                mode = mode_m.group(1).capitalize()
                continue

            # Key + scale  e.g. "A Minor" or "C# Major"
            key_m = re.match(r"^([A-Ga-g][#b]?)\s+(major|minor|dorian|phrygian|lydian|mixolydian|locrian|harmonic minor|pentatonic)$", part, re.IGNORECASE)
            if key_m:
                candidate_key = key_m.group(1).upper() if len(key_m.group(1)) == 1 else key_m.group(1)[0].upper() + key_m.group(1)[1:]
                candidate_scale = key_m.group(2).capitalize()
                if candidate_key in NOTES:
                    key = candidate_key
                    scale = candidate_scale
                    continue

            # Vocal keyword
            if low in VOCAL_KEYWORDS:
                vocal_tags.append(part)
                continue

            # First non-matched part that has no numbers → treat as genre
            if not genre and not any(c.isdigit() for c in part):
                genre = part
                continue

            # Everything else → instrument
            instruments.append(part)

        # Apply to state
        if genre:
            self.state.genre = genre
        if bpm:
            self.state.bpm = bpm
        if key:
            self.state.key = key
        if scale:
            self.state.scale = scale
        if mode:
            self.state.mode = mode
        if time_sig:
            self.state.time_sig = time_sig
        self.state.instruments = instruments
        self.state.vocal_tags = vocal_tags
        self.state.lyrics = lyrics

        self.state_changed.emit()
        self.status_label.setText("Sent to Overview for editing.")
        self.go_to_overview.emit()
