# AceTalk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PyQt6 desktop app that assembles ACE-Step 1.5 music prompts from a structured UI and outputs them via clipboard, ComfyUI API, or saved presets.

**Architecture:** Single `QMainWindow` with a `QTabWidget` (5 tabs) and a persistent output panel docked at the bottom. A shared `SessionState` dataclass flows through all tabs; `prompt_builder.py` assembles the final caption and lyrics strings from it on every change.

**Tech Stack:** PyQt6, requests, duckduckgo-search, pytest, pytest-qt

---

## File Map

```
AceUser/
  acetalk.py                        # Entry point — creates QApplication, launches MainWindow
  requirements.txt
  config.json                       # Created at runtime; stores ComfyUI URL, Brave key
  acetalk/
    __init__.py
    tabs/
      __init__.py
      style_tab.py                  # Tab 1: genre grid, BPM/key/scale/mode controls
      instrument_tab.py             # Tab 2: category tree, keyword chips, modifier chips
      vocalist_tab.py               # Tab 3: artist search, vocal descriptor picker
      lyrics_tab.py                 # Tab 4: template mode + Ollama mode + editor
      parameters_tab.py             # Tab 5: cfg_scale, temperature, top_p, top_k, min_p, etc.
    core/
      __init__.py
      state.py                      # SessionState dataclass + to_dict/from_dict
      prompt_builder.py             # Assembles caption + lyrics from SessionState
      comfyui_api.py                # ComfyUI REST client: ping, fill_fields, queue_workflow
      search.py                     # Brave + DDG artist/vocal search, caches to vocals.json
      llm.py                        # Ollama: list_models() + streaming generate()
    ui/
      __init__.py
      main_window.py                # QMainWindow: tab widget + output panel splitter
      output_panel.py               # Persistent bottom panel: caption/lyrics display + action buttons
      settings_dialog.py            # Gear-icon dialog for config.json settings
    data/
      genres.json
      instruments.json
      vocals.json
      templates.json
  presets/
    .gitkeep
  tests/
    __init__.py
    conftest.py                     # pytest fixtures: app (QApplication), sample SessionState
    test_state.py
    test_prompt_builder.py
    test_comfyui_api.py
    test_search.py
    test_llm.py
```

---

## Task 1: Scaffold — directory structure, requirements, entry point

**Files:**
- Create: `acetalk.py`
- Create: `requirements.txt`
- Create: `acetalk/__init__.py`, `acetalk/tabs/__init__.py`, `acetalk/core/__init__.py`, `acetalk/ui/__init__.py`
- Create: `presets/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create all directories**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
mkdir -p acetalk/tabs acetalk/core acetalk/ui acetalk/data presets tests
touch acetalk/__init__.py acetalk/tabs/__init__.py acetalk/core/__init__.py acetalk/ui/__init__.py tests/__init__.py presets/.gitkeep
```

- [ ] **Step 2: Write requirements.txt**

```
PyQt6
requests
duckduckgo-search
pytest
pytest-qt
```

Save to `requirements.txt`.

- [ ] **Step 3: Install dependencies**

```bash
pip install PyQt6 requests duckduckgo-search pytest pytest-qt
```

- [ ] **Step 4: Write minimal entry point**

`acetalk.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AceTalk — ACE-Step 1.5 Prompt Builder")
        self.setMinimumSize(1100, 750)
        label = QLabel("Loading...", alignment=Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Verify it runs**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
python acetalk.py
```

Expected: A window titled "AceTalk — ACE-Step 1.5 Prompt Builder" appears with "Loading..." in the center.

- [ ] **Step 6: Commit**

```bash
git add acetalk.py requirements.txt acetalk/ presets/.gitkeep tests/
git commit -m "feat: scaffold AceTalk project structure and entry point"
```

---

## Task 2: SessionState

**Files:**
- Create: `acetalk/core/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

`tests/test_state.py`:
```python
from acetalk.core.state import SessionState


def test_defaults():
    s = SessionState()
    assert s.genre == ""
    assert s.bpm == 120
    assert s.key == "C"
    assert s.scale == "Major"
    assert s.mode == ""
    assert s.time_sig == "4/4"
    assert s.instruments == []
    assert s.vocal_tags == []
    assert s.lyrics == ""
    assert s.cfg_scale == 7.0
    assert s.temperature == 1.0
    assert s.top_p == 0.95
    assert s.top_k == 50
    assert s.min_p == 0.05
    assert s.duration == 30
    assert s.steps == 60
    assert s.task_type == "text2music"


def test_round_trip():
    s = SessionState(genre="Psytrance", bpm=140, key="A", scale="Minor",
                     instruments=["TB-303 bass"], vocal_tags=["breathy"])
    d = s.to_dict()
    s2 = SessionState.from_dict(d)
    assert s2.genre == "Psytrance"
    assert s2.bpm == 140
    assert s2.instruments == ["TB-303 bass"]
    assert s2.vocal_tags == ["breathy"]


def test_from_dict_ignores_unknown_keys():
    d = {"genre": "EDM", "bpm": 128, "unknown_field": "ignored"}
    s = SessionState.from_dict(d)
    assert s.genre == "EDM"
    assert s.bpm == 128
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
pytest tests/test_state.py -v
```

Expected: `ImportError: cannot import name 'SessionState'`

- [ ] **Step 3: Write implementation**

`acetalk/core/state.py`:
```python
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class SessionState:
    # Style tab
    genre: str = ""
    bpm: int = 120
    key: str = "C"
    scale: str = "Major"
    mode: str = ""
    time_sig: str = "4/4"

    # Instruments tab — list of fully-rendered ACE-Step phrases
    instruments: List[str] = field(default_factory=list)

    # Vocals tab
    vocal_tags: List[str] = field(default_factory=list)

    # Lyrics tab
    lyrics: str = ""

    # Parameters tab
    cfg_scale: float = 7.0
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 50
    min_p: float = 0.05
    duration: int = 30
    steps: int = 60
    task_type: str = "text2music"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SessionState":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_state.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add acetalk/core/state.py tests/test_state.py
git commit -m "feat: add SessionState dataclass with round-trip serialization"
```

---

## Task 3: prompt_builder

**Files:**
- Create: `acetalk/core/prompt_builder.py`
- Create: `tests/test_prompt_builder.py`

- [ ] **Step 1: Write the failing test**

`tests/test_prompt_builder.py`:
```python
from acetalk.core.state import SessionState
from acetalk.core.prompt_builder import build_caption, build_lyrics, build_prompt


def test_caption_empty_state():
    s = SessionState()
    caption = build_caption(s)
    assert caption == ""


def test_caption_genre_and_bpm():
    s = SessionState(genre="Psytrance", bpm=140)
    caption = build_caption(s)
    assert "psytrance" in caption
    assert "140 BPM" in caption


def test_caption_key_and_scale():
    s = SessionState(key="A", scale="Minor")
    caption = build_caption(s)
    assert "A Minor" in caption


def test_caption_mode():
    s = SessionState(key="A", scale="Minor", mode="Phrygian")
    caption = build_caption(s)
    assert "Phrygian mode" in caption


def test_caption_instruments_and_vocals():
    s = SessionState(
        instruments=["warm TB-303 synth bass", "punchy electronic drums"],
        vocal_tags=["breathy female vocal", "whispery"]
    )
    caption = build_caption(s)
    assert "warm TB-303 synth bass" in caption
    assert "breathy female vocal" in caption


def test_caption_full():
    s = SessionState(
        genre="Psytrance", bpm=140, key="A", scale="Minor", mode="Phrygian",
        time_sig="4/4", instruments=["TB-303 bass"], vocal_tags=["breathy"]
    )
    caption = build_caption(s)
    parts = [p.strip() for p in caption.split(",")]
    assert "psytrance" in parts
    assert "140 BPM" in parts
    assert "A Minor" in parts
    assert "Phrygian mode" in parts
    assert "4/4 time" in parts
    assert "TB-303 bass" in parts
    assert "breathy" in parts


def test_build_lyrics():
    s = SessionState(lyrics="[Intro]\nHello world")
    assert build_lyrics(s) == "[Intro]\nHello world"


def test_build_prompt_returns_tuple():
    s = SessionState(genre="EDM", bpm=128, lyrics="[Chorus]\nDrop")
    caption, lyrics = build_prompt(s)
    assert "edm" in caption
    assert lyrics == "[Chorus]\nDrop"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: `ImportError: cannot import name 'build_caption'`

- [ ] **Step 3: Write implementation**

`acetalk/core/prompt_builder.py`:
```python
from .state import SessionState


def build_caption(state: SessionState) -> str:
    """Assemble the ACE-Step caption/tags string from current session state."""
    parts = []

    if state.genre:
        parts.append(state.genre.lower())

    if state.bpm:
        parts.append(f"{state.bpm} BPM")

    if state.key:
        key_str = state.key
        if state.scale:
            key_str += f" {state.scale}"
        parts.append(key_str)

    if state.mode:
        parts.append(f"{state.mode} mode")

    if state.time_sig:
        parts.append(f"{state.time_sig} time")

    parts.extend(state.instruments)
    parts.extend(state.vocal_tags)

    return ", ".join(parts)


def build_lyrics(state: SessionState) -> str:
    """Return the lyrics string from state."""
    return state.lyrics


def build_prompt(state: SessionState) -> tuple[str, str]:
    """Return (caption, lyrics) tuple."""
    return build_caption(state), build_lyrics(state)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add acetalk/core/prompt_builder.py tests/test_prompt_builder.py
git commit -m "feat: add prompt_builder — assembles caption and lyrics from SessionState"
```

---

## Task 4: Data files

**Files:**
- Create: `acetalk/data/genres.json`
- Create: `acetalk/data/instruments.json`
- Create: `acetalk/data/vocals.json`
- Create: `acetalk/data/templates.json`

- [ ] **Step 1: Write genres.json**

`acetalk/data/genres.json`:
```json
{
  "genres": [
    {
      "name": "Psytrance",
      "tags": ["psytrance", "dark", "hypnotic", "driving"],
      "bpm_min": 138, "bpm_max": 148,
      "default_key": "A", "default_scale": "Minor", "default_mode": "Phrygian",
      "default_time_sig": "4/4",
      "description": "High-energy psychedelic trance with dark, hypnotic basslines and full-on production.",
      "typical_instruments": ["TB-303 synth bass", "layered analog pads", "electronic drums", "tribal percussion", "FM synth leads"]
    },
    {
      "name": "EDM",
      "tags": ["EDM", "electronic dance", "energetic", "euphoric"],
      "bpm_min": 128, "bpm_max": 140,
      "default_key": "F", "default_scale": "Major", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Broad umbrella of electronic dance music: uplifting, high-energy, crowd-focused.",
      "typical_instruments": ["sidechain synth bass", "lead synth", "TR-909 kit", "layered pads", "arp sequence"]
    },
    {
      "name": "House",
      "tags": ["house", "groovy", "four-on-the-floor", "soulful"],
      "bpm_min": 120, "bpm_max": 130,
      "default_key": "C", "default_scale": "Minor", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Soulful, groove-driven dance music built on a four-on-the-floor kick pattern.",
      "typical_instruments": ["electric bass", "Rhodes", "TR-808 kit", "organ", "warm analog pads", "congas"]
    },
    {
      "name": "Trance",
      "tags": ["trance", "uplifting", "melodic", "euphoric", "arpeggiated"],
      "bpm_min": 130, "bpm_max": 145,
      "default_key": "D", "default_scale": "Minor", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Melodic, uplifting electronic genre with driving arpeggios and powerful breakdowns.",
      "typical_instruments": ["arpeggio synth", "supersaw lead", "electronic drums", "lush string pads", "synth bass"]
    },
    {
      "name": "Blues",
      "tags": ["blues", "soulful", "raw", "expressive", "12-bar"],
      "bpm_min": 60, "bpm_max": 120,
      "default_key": "E", "default_scale": "Minor", "default_mode": "Dorian",
      "default_time_sig": "4/4",
      "description": "Expressive American roots music built on call-and-response and the pentatonic scale.",
      "typical_instruments": ["electric guitar", "acoustic guitar", "upright bass", "acoustic drum kit", "harmonica", "Rhodes"]
    },
    {
      "name": "Jazz",
      "tags": ["jazz", "improvisational", "swung", "complex harmony", "bebop"],
      "bpm_min": 80, "bpm_max": 200,
      "default_key": "F", "default_scale": "Major", "default_mode": "Lydian",
      "default_time_sig": "4/4",
      "description": "Sophisticated improvisational genre with complex chord voicings and swung rhythms.",
      "typical_instruments": ["grand piano", "upright bass", "brush drums", "saxophone", "trumpet", "Hammond B3"]
    },
    {
      "name": "Neo Soul",
      "tags": ["neo soul", "soulful", "warm", "groove", "RnB influenced"],
      "bpm_min": 70, "bpm_max": 100,
      "default_key": "G", "default_scale": "Minor", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Warm, organic soul music blending classic R&B with jazz harmony and hip-hop groove.",
      "typical_instruments": ["Rhodes", "Wurlitzer 200A", "electric bass", "brush drums", "acoustic guitar", "organ"]
    },
    {
      "name": "Heavy Metal",
      "tags": ["heavy metal", "distorted", "aggressive", "powerful", "riff-driven"],
      "bpm_min": 100, "bpm_max": 200,
      "default_key": "E", "default_scale": "Minor", "default_mode": "Phrygian",
      "default_time_sig": "4/4",
      "description": "Aggressive, riff-driven rock with highly distorted guitars and powerful drumming.",
      "typical_instruments": ["distorted electric guitar", "palm-muted chugging", "picked bass attack", "acoustic drum kit (heavy)", "double kick pedal"]
    },
    {
      "name": "Classical",
      "tags": ["classical", "orchestral", "dynamic", "structured", "acoustic"],
      "bpm_min": 40, "bpm_max": 200,
      "default_key": "C", "default_scale": "Major", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Composed orchestral music following formal structure, with wide dynamic range.",
      "typical_instruments": ["grand piano", "violin solo", "cello", "oboe", "flute", "French horn", "string ensemble"]
    },
    {
      "name": "Emo",
      "tags": ["emo", "emotional", "raw", "confessional", "guitar-driven"],
      "bpm_min": 100, "bpm_max": 160,
      "default_key": "D", "default_scale": "Minor", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Emotionally raw guitar-driven rock with confessional lyrics and dynamic shifts.",
      "typical_instruments": ["clean electric guitar", "distorted guitar", "electric bass", "acoustic drum kit"]
    },
    {
      "name": "Hip-Hop",
      "tags": ["hip-hop", "trap", "boom bap", "808 bass", "sampled"],
      "bpm_min": 70, "bpm_max": 100,
      "default_key": "C", "default_scale": "Minor", "default_mode": "",
      "default_time_sig": "4/4",
      "description": "Rhythm-driven genre built on sampled loops, 808 bass, and vocal flow.",
      "typical_instruments": ["808 bass", "TR-808 kit", "lo-fi keys", "sampled strings", "hi-hat rolls"]
    },
    {
      "name": "Ambient",
      "tags": ["ambient", "atmospheric", "textural", "slow-evolving", "spacious"],
      "bpm_min": 60, "bpm_max": 90,
      "default_key": "C", "default_scale": "Major", "default_mode": "Lydian",
      "default_time_sig": "4/4",
      "description": "Slow-evolving atmospheric soundscapes focusing on texture and space over rhythm.",
      "typical_instruments": ["ambient textures", "granular synthesis", "piano (sustained)", "reverb-soaked guitar", "drone pads"]
    },
    {
      "name": "Folk",
      "tags": ["folk", "acoustic", "storytelling", "fingerstyle", "organic"],
      "bpm_min": 70, "bpm_max": 130,
      "default_key": "G", "default_scale": "Major", "default_mode": "",
      "default_time_sig": "3/4",
      "description": "Acoustic, story-driven genre rooted in tradition with organic instrumentation.",
      "typical_instruments": ["dreadnought acoustic", "steel-string fingerstyle", "banjo", "fiddle", "upright bass", "hand percussion"]
    },
    {
      "name": "Funk",
      "tags": ["funk", "groove", "syncopated", "slap bass", "tight pocket"],
      "bpm_min": 90, "bpm_max": 120,
      "default_key": "E", "default_scale": "Minor", "default_mode": "Dorian",
      "default_time_sig": "4/4",
      "description": "Groove-heavy genre defined by syncopated rhythms, slap bass, and tight ensemble playing.",
      "typical_instruments": ["slap bass", "Rhodes", "clavinet", "acoustic drum kit (tight)", "rhythm guitar (muted)", "horn section"]
    }
  ]
}
```

- [ ] **Step 2: Write instruments.json**

`acetalk/data/instruments.json`:
```json
{
  "categories": {
    "Electronic/Synths": {
      "Acid/Bass Synths": [
        "TB-303 synth bass", "squelchy resonant filter", "distorted saw wave bass",
        "Moog-style ladder filter", "4-pole resonant VCF", "detuned sawtooth bass"
      ],
      "Pads/Atmosphere": [
        "layered analog pads", "lush wavetable pads", "granular textures",
        "ambient textures", "detuned oscillator pads", "supersaw chord stabs"
      ],
      "Leads": [
        "FM synth lead (Yamaha DX7)", "bitcrushed lead", "supersaw lead",
        "distorted wavetable lead", "TB-303 silver box lead"
      ],
      "FM/Digital": [
        "Yamaha DX7 textures", "glassy FM bells", "12-bit digital crunch",
        "crystal-clear 6-operator synthesis", "aliasing artifacts"
      ]
    },
    "Keys": {
      "Electric Piano": [
        "Rhodes Mark I", "Wurlitzer 200A", "barking tine sound",
        "bell-like Rhodes resonance", "stereo tremolo keys", "saturated tube Rhodes"
      ],
      "Acoustic Piano": [
        "grand piano", "upright piano", "prepared piano",
        "piano (sustained, reverb-soaked)", "close-mic grand piano"
      ],
      "Organ": [
        "Hammond B3", "Leslie speaker cabinet (fast rotation)", "Leslie (slow rotation)",
        "drawbar organ", "percussive organ attack", "church pipe organ"
      ],
      "Other Keys": [
        "clavinet", "lo-fi keys", "harpsichord"
      ]
    },
    "Bass": {
      "Electric Bass": [
        "electric bass", "slap bass", "slap and pop bass", "picked bass attack",
        "fretless bass", "flatwound strings (mellow bass)", "roundwound strings (bright bass)"
      ],
      "Synth Bass": [
        "synth bass", "808 bass", "sub bass", "wobble bass", "sidechain synth bass"
      ],
      "Upright Bass": [
        "upright bass", "pizzicato upright bass", "bowed upright bass"
      ]
    },
    "Drums/Percussion": {
      "Acoustic Drums": [
        "acoustic drum kit", "brush drums", "acoustic drum kit (heavy)",
        "acoustic drum kit (tight pocket)", "close-mic snare"
      ],
      "Electronic Drums": [
        "electronic drums", "TR-808 kit", "TR-909 kit", "LinnDrum",
        "808 hi-hat rolls", "double kick pedal", "programmed beats"
      ],
      "Percussion": [
        "tribal percussion", "congas", "bongos", "shakers",
        "hand percussion", "tambourine", "frame drum"
      ]
    },
    "Guitars": {
      "Electric Guitar": [
        "distorted electric guitar", "clean electric guitar", "humbucker sustain",
        "P-90 grit", "palm-muted chugging", "whammy bar dives", "rhythm guitar (muted)"
      ],
      "Acoustic Guitar": [
        "dreadnought acoustic", "steel-string fingerstyle", "classical nylon string guitar",
        "12-string acoustic", "banjo"
      ]
    },
    "Strings": {
      "Solo Strings": [
        "violin solo", "cello", "viola", "sul ponticello (metallic)",
        "sul tasto (soft flute-like)", "col legno", "pizzicato strings",
        "heavy vibrato strings", "double stops"
      ],
      "Ensemble Strings": [
        "string ensemble", "string quartet", "lush orchestral strings",
        "tremolo strings", "staccato strings"
      ]
    },
    "Woodwinds/Brass": {
      "Woodwinds": [
        "saxophone", "overblown saxophone", "breathy flute", "reedy oboe",
        "double-reed bassoon", "flutter-tonguing flute", "clarinet"
      ],
      "Brass": [
        "trumpet", "muted trumpet", "French horn", "trombone",
        "horn section", "flugelhorn"
      ]
    }
  },
  "modifiers": {
    "timbre": ["warm", "bright", "crisp", "muddy", "airy", "punchy", "lush", "raw", "polished", "gritty"],
    "mic": ["close-mic", "room mics", "binaural / 3D spatial", "mono centered", "ambient"],
    "mix": ["tape saturation (15 ips)", "vacuum tube distortion", "high dynamic range", "brickwall limited", "lo-fi aesthetic"]
  }
}
```

- [ ] **Step 3: Write vocals.json (seed data)**

`acetalk/data/vocals.json`:
```json
{
  "artists": [
    {
      "name": "Billie Eilish",
      "range": "Alto (A3–A5)",
      "preferred_key": "C minor",
      "style": "Pop/Indie",
      "known_for": ["bad guy", "Happier Than Ever", "Ocean Eyes"],
      "ace_step_descriptors": ["breathy female vocal", "whispery", "intimate", "soft", "close-mic vocal", "airy", "understated delivery"]
    },
    {
      "name": "Freddie Mercury",
      "range": "Tenor (A2–F5)",
      "preferred_key": "G Major",
      "style": "Rock/Opera",
      "known_for": ["Bohemian Rhapsody", "We Will Rock You", "Somebody to Love"],
      "ace_step_descriptors": ["powerful male vocal", "operatic", "belted", "wide vibrato", "dramatic", "raw energy"]
    },
    {
      "name": "Erykah Badu",
      "range": "Mezzo-Soprano (G3–C6)",
      "preferred_key": "D minor",
      "style": "Neo Soul/R&B",
      "known_for": ["On & On", "Bag Lady", "Tyrone"],
      "ace_step_descriptors": ["warm female vocal", "soulful", "melismatic", "smooth", "jazz-inflected", "intimate"]
    }
  ]
}
```

- [ ] **Step 4: Write templates.json**

`acetalk/data/templates.json`:
```json
{
  "structures": {
    "Verse-Chorus": "[Verse]\n{verse_1}\n\n[Chorus]\n{chorus}\n\n[Verse]\n{verse_2}\n\n[Chorus]\n{chorus}",
    "Verse-Chorus-Bridge": "[Verse]\n{verse_1}\n\n[Chorus]\n{chorus}\n\n[Verse]\n{verse_2}\n\n[Chorus]\n{chorus}\n\n[Bridge]\n{bridge}\n\n[Chorus]\n{chorus}",
    "Intro-Verse-Chorus-Outro": "[Intro: Atmospheric]\n\n[Verse]\n{verse_1}\n\n[Chorus: Anthemic]\n{chorus}\n\n[Verse]\n{verse_2}\n\n[Chorus: Anthemic]\n{chorus}\n\n[Outro]\n",
    "EDM Structure": "[Intro: Atmospheric]\n\n[Build]\n\n[Drop]\n{chorus}\n\n[Breakdown]\n\n[Build]\n\n[Drop]\n{chorus}\n\n[Outro]\n",
    "Minimal": "[Verse]\n{verse_1}\n\n[Chorus]\n{chorus}"
  },
  "placeholders": {
    "Love/Uplifting": {
      "verse_1": "Every morning starts with your light\nThe world feels right when you are near\nI chase the warmth of golden skies\nAnd find my home in your eyes",
      "chorus": "We rise we fall we start again\nTogether we are more than just friends\nI'd cross the stars to find your hand\nForever yours is where I stand",
      "verse_2": "The nights grow short when you are close\nI hold the moments that matter most\nYour voice the anchor in the storm\nIn your arms I am always home",
      "bridge": "Nothing can shake us now\nWe've been through everything somehow\nStronger in every way\nI'd choose you any day"
    },
    "Dark/Hypnotic": {
      "verse_1": "Beneath the surface something stirs\nA frequency the body learns\nThe beat descends the walls dissolve\nA puzzle no one needs to solve",
      "chorus": "Sink into the rhythm now\nLet the current show you how\nLose the noise and find the core\nThis is what the dark is for",
      "verse_2": "The signal hums through concrete veins\nA city breathing through the pain\nWe are the pulse we are the code\nA thousand lights along the road",
      "bridge": "Can you feel it underground\nThe silent hum without a sound\nWe are the signal we are the wave\nBeyond the borders of the sane"
    }
  }
}
```

- [ ] **Step 5: Verify data loads**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
python -c "
import json
for f in ['acetalk/data/genres.json', 'acetalk/data/instruments.json', 'acetalk/data/vocals.json', 'acetalk/data/templates.json']:
    data = json.load(open(f))
    print(f'OK: {f}')
"
```

Expected: `OK:` printed for all four files with no errors.

- [ ] **Step 6: Commit**

```bash
git add acetalk/data/
git commit -m "feat: add genres, instruments, vocals, and templates data files"
```

---

## Task 5: search.py (artist/vocal search)

**Files:**
- Create: `acetalk/core/search.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Write the failing test**

`tests/test_search.py`:
```python
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from acetalk.core.search import search_artist, _parse_artist_result


def test_parse_artist_result_returns_dict():
    text = "Billie Eilish is known for breathy, whispery vocal style. She typically sings in C minor."
    result = _parse_artist_result("Billie Eilish", text)
    assert result["name"] == "Billie Eilish"
    assert isinstance(result["ace_step_descriptors"], list)


def test_search_artist_hits_local_db_first(tmp_path):
    vocals_path = tmp_path / "vocals.json"
    vocals_path.write_text(json.dumps({
        "artists": [{
            "name": "Test Artist",
            "range": "Alto",
            "preferred_key": "Am",
            "style": "Pop",
            "known_for": ["Song A"],
            "ace_step_descriptors": ["breathy", "soft"]
        }]
    }))
    with patch("acetalk.core.search.VOCALS_PATH", str(vocals_path)):
        result = search_artist("Test Artist", source="local")
    assert result is not None
    assert result["name"] == "Test Artist"
    assert "breathy" in result["ace_step_descriptors"]


def test_search_artist_returns_none_for_unknown_local(tmp_path):
    vocals_path = tmp_path / "vocals.json"
    vocals_path.write_text(json.dumps({"artists": []}))
    with patch("acetalk.core.search.VOCALS_PATH", str(vocals_path)):
        result = search_artist("Unknown Nobody", source="local")
    assert result is None


def test_search_artist_caches_web_result(tmp_path):
    vocals_path = tmp_path / "vocals.json"
    vocals_path.write_text(json.dumps({"artists": []}))
    mock_result = {
        "name": "New Artist",
        "range": "Tenor",
        "preferred_key": "G Major",
        "style": "Rock",
        "known_for": [],
        "ace_step_descriptors": ["powerful", "raw"]
    }
    with patch("acetalk.core.search.VOCALS_PATH", str(vocals_path)), \
         patch("acetalk.core.search._web_search_artist", return_value=mock_result):
        result = search_artist("New Artist", source="web")
    assert result["name"] == "New Artist"
    saved = json.loads(vocals_path.read_text())
    assert any(a["name"] == "New Artist" for a in saved["artists"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_search.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write implementation**

`acetalk/core/search.py`:
```python
import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

VOCALS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vocals.json")
VOCALS_PATH = os.path.normpath(VOCALS_PATH)

_VOCAL_KEYWORDS = [
    "breathy", "raspy", "smooth", "nasal", "powerful", "clear",
    "whispered", "whispery", "belted", "falsetto", "spoken word", "operatic",
    "airy", "gritty", "warm", "bright", "vibrato", "melismatic",
    "intimate", "raw", "soulful", "crystal-clear", "husky", "soft",
    "close-mic vocal", "female vocal", "male vocal", "androgynous vocal",
    "jazz-inflected", "melancholic", "dramatic", "understated",
]


def _load_vocals_db() -> dict:
    try:
        with open(VOCALS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"artists": []}


def _save_vocals_db(db: dict) -> None:
    with open(VOCALS_PATH, "w") as f:
        json.dump(db, f, indent=2)


def _parse_artist_result(name: str, text: str) -> dict:
    """Extract ACE-Step vocal descriptors from search result text."""
    found = [kw for kw in _VOCAL_KEYWORDS if kw.lower() in text.lower()]
    if not found:
        found = ["vocal"]
    return {
        "name": name,
        "range": "",
        "preferred_key": "",
        "style": "",
        "known_for": [],
        "ace_step_descriptors": found,
    }


def _web_search_artist(name: str) -> dict | None:
    """Try Brave first, fall back to DDG. Returns parsed artist dict or None."""
    query = f"{name} vocalist vocal style singing technique range"
    text = ""
    source_label = ""

    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if brave_key:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
                params={"q": query, "count": 5},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("web", {}).get("results", [])
            text = " ".join(r.get("description", "") for r in results)
            source_label = "brave"
        except Exception as exc:
            logger.warning("Brave search failed: %s", exc)

    if not text:
        try:
            from duckduckgo_search import DDGS
            with DDGS(timeout=10) as ddgs:
                results = ddgs.text(query, max_results=5)
                text = " ".join(r.get("body", "") for r in results)
            source_label = "ddg"
        except Exception as exc:
            logger.warning("DDG search failed: %s", exc)

    if not text:
        return None

    result = _parse_artist_result(name, text)
    result["_source"] = source_label
    return result


def search_artist(name: str, source: str = "both") -> dict | None:
    """
    Search for artist vocal info.
    source: 'local', 'web', or 'both' (local first, then web)
    Returns artist dict or None.
    """
    db = _load_vocals_db()

    # Local lookup (case-insensitive)
    name_lower = name.strip().lower()
    for artist in db.get("artists", []):
        if artist["name"].lower() == name_lower:
            return artist

    if source == "local":
        return None

    # Web search
    result = _web_search_artist(name)
    if result:
        # Cache to local DB
        db["artists"].append(result)
        _save_vocals_db(db)

    return result
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_search.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add acetalk/core/search.py tests/test_search.py
git commit -m "feat: add search.py — Brave/DDG artist vocal search with local caching"
```

---

## Task 6: llm.py (Ollama client)

**Files:**
- Create: `acetalk/core/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write the failing test**

`tests/test_llm.py`:
```python
from unittest.mock import patch, MagicMock
from acetalk.core.llm import list_models, generate_lyrics


def test_list_models_returns_list():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"models": [{"name": "llama3"}, {"name": "mistral"}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("acetalk.core.llm.requests.get", return_value=mock_resp):
        models = list_models()
    assert "llama3" in models
    assert "mistral" in models


def test_list_models_returns_fallback_on_error():
    with patch("acetalk.core.llm.requests.get", side_effect=Exception("connection refused")):
        models = list_models()
    assert models == ["(Ollama offline)"]


def test_generate_lyrics_calls_ollama():
    chunks = [
        b'{"response":"[Intro]\\n"}',
        b'{"response":"Stars align\\n"}',
        b'{"done":true,"response":""}',
    ]
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(chunks)
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    collected = []
    with patch("acetalk.core.llm.requests.post", return_value=mock_resp):
        generate_lyrics(
            prompt="write a psytrance song",
            genre="Psytrance", key="Am", mood="dark",
            structure="Verse-Chorus",
            model="llama3",
            on_token=collected.append,
        )
    assert "[Intro]" in "".join(collected)
    assert "Stars align" in "".join(collected)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write implementation**

`acetalk/core/llm.py`:
```python
import json
import logging
from typing import Callable

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://localhost:11434"


def list_models() -> list[str]:
    """Fetch available Ollama models. Returns fallback string in list on failure."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return models if models else ["(no models found)"]
    except Exception as exc:
        logger.debug("Ollama unreachable: %s", exc)
        return ["(Ollama offline)"]


def generate_lyrics(
    prompt: str,
    genre: str,
    key: str,
    mood: str,
    structure: str,
    model: str,
    on_token: Callable[[str], None],
) -> None:
    """
    Stream lyrics from Ollama. Calls on_token(chunk) for each token received.
    on_token is called on the calling thread — caller must route to UI thread if needed.
    """
    system = (
        f"You are an expert lyricist specializing in {genre} music. "
        f"Write lyrics in the key of {key}, with a {mood} mood. "
        f"Use this song structure: {structure}. "
        f"Format sections with ACE-Step structural tags like [Intro], [Verse], [Chorus], [Bridge], [Outro]. "
        f"Use qualifier variants like [Chorus: Anthemic] or [Intro: Atmospheric] where appropriate. "
        f"Output only the lyrics — no explanations, no headings outside of brackets."
    )
    payload = {
        "model": model,
        "prompt": f"{system}\n\nTask: {prompt}",
        "stream": True,
    }
    try:
        with requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        on_token(token)
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.error("Ollama generation failed: %s", exc)
        on_token(f"\n[Error: {exc}]")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_llm.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add acetalk/core/llm.py tests/test_llm.py
git commit -m "feat: add llm.py — Ollama model list and streaming lyric generation"
```

---

## Task 7: comfyui_api.py

**Files:**
- Create: `acetalk/core/comfyui_api.py`
- Create: `tests/test_comfyui_api.py`

- [ ] **Step 1: Write the failing test**

`tests/test_comfyui_api.py`:
```python
import json
from unittest.mock import patch, MagicMock
from acetalk.core.comfyui_api import ping, queue_workflow, ComfyUIClient
from acetalk.core.state import SessionState


def test_ping_returns_true_when_online():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("acetalk.core.comfyui_api.requests.get", return_value=mock_resp):
        assert ping() is True


def test_ping_returns_false_when_offline():
    with patch("acetalk.core.comfyui_api.requests.get", side_effect=Exception("refused")):
        assert ping() is False


def test_queue_workflow_posts_to_prompt_endpoint():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"prompt_id": "abc123"}
    mock_resp.raise_for_status = MagicMock()
    state = SessionState(genre="Psytrance", bpm=140, lyrics="[Verse]\nTest")
    with patch("acetalk.core.comfyui_api.requests.post", return_value=mock_resp) as mock_post:
        result = queue_workflow(state, caption="psytrance, 140 BPM", workflow_json={"nodes": []})
    assert result == {"prompt_id": "abc123"}
    call_args = mock_post.call_args
    assert "/prompt" in call_args[0][0]


def test_client_uses_configured_url():
    client = ComfyUIClient(base_url="http://myserver:8188")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("acetalk.core.comfyui_api.requests.get", return_value=mock_resp) as mock_get:
        client.ping()
    assert "myserver:8188" in mock_get.call_args[0][0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_comfyui_api.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write implementation**

`acetalk/core/comfyui_api.py`:
```python
import json
import logging

import requests

from .state import SessionState
from .prompt_builder import build_caption, build_lyrics

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://127.0.0.1:8188"


def ping(base_url: str = DEFAULT_URL) -> bool:
    """Return True if ComfyUI is reachable."""
    try:
        requests.get(f"{base_url}/system_stats", timeout=3).raise_for_status()
        return True
    except Exception:
        return False


def queue_workflow(
    state: SessionState,
    caption: str,
    workflow_json: dict,
    base_url: str = DEFAULT_URL,
) -> dict:
    """
    POST a workflow JSON to ComfyUI's /prompt endpoint.
    Returns the response JSON (contains prompt_id).
    """
    resp = requests.post(
        f"{base_url}/prompt",
        json={"prompt": workflow_json},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


class ComfyUIClient:
    """Stateful client that holds the ComfyUI base URL from config."""

    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def ping(self) -> bool:
        return ping(self.base_url)

    def queue_workflow(self, state: SessionState, caption: str, workflow_json: dict) -> dict:
        return queue_workflow(state, caption, workflow_json, self.base_url)

    def fill_fields(self, caption: str, lyrics: str, state: SessionState) -> dict:
        """
        Attempt to fill ACE-Step node inputs in the running graph.
        Finds nodes by title from /object_info and patches via /prompt.
        Returns status dict.
        """
        try:
            resp = requests.get(f"{self.base_url}/object_info", timeout=5)
            resp.raise_for_status()
        except Exception as exc:
            return {"error": f"Cannot reach ComfyUI: {exc}"}

        # Build a minimal prompt payload targeting known ACE-Step node titles
        payload = {
            "prompt": {
                "ace_caption": {
                    "class_type": "ACEStepTextEncode",
                    "inputs": {"text": caption}
                },
                "ace_lyrics": {
                    "class_type": "ACEStepLyricsEncode",
                    "inputs": {"lyrics": lyrics}
                }
            }
        }
        try:
            post_resp = requests.post(f"{self.base_url}/prompt", json=payload, timeout=10)
            post_resp.raise_for_status()
            return post_resp.json()
        except Exception as exc:
            return {"error": str(exc)}
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_comfyui_api.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add acetalk/core/comfyui_api.py tests/test_comfyui_api.py
git commit -m "feat: add ComfyUI API client — ping, queue_workflow, fill_fields"
```

---

## Task 8: conftest.py + run all tests

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write conftest**

`tests/conftest.py`:
```python
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from acetalk.core.state import SessionState


@pytest.fixture(scope="session")
def qt_app():
    """Single QApplication for the test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_state():
    return SessionState(
        genre="Psytrance",
        bpm=140,
        key="A",
        scale="Minor",
        mode="Phrygian",
        time_sig="4/4",
        instruments=["warm TB-303 synth bass", "punchy electronic drums"],
        vocal_tags=["breathy female vocal"],
        lyrics="[Intro: Atmospheric]\nTest lyrics",
        cfg_scale=7.0,
        temperature=1.0,
    )
```

- [ ] **Step 2: Run full test suite**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
pytest tests/ -v
```

Expected: All tests PASSED (no failures).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add pytest conftest with QApplication and sample state fixtures"
```

---

## Task 9: Main window + output panel skeleton

**Files:**
- Create: `acetalk/ui/main_window.py`
- Create: `acetalk/ui/output_panel.py`
- Modify: `acetalk.py`

- [ ] **Step 1: Write output_panel.py**

`acetalk/ui/output_panel.py`:
```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QSplitter, QFrame, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json, os


class OutputPanel(QWidget):
    push_requested = pyqtSignal(str, str)   # (caption, lyrics)
    save_requested = pyqtSignal(str)         # preset name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(4)

        # Caption + Lyrics side by side
        fields = QHBoxLayout()

        cap_layout = QVBoxLayout()
        cap_layout.addWidget(QLabel("Caption:"))
        self.caption_box = QTextEdit()
        self.caption_box.setReadOnly(True)
        self.caption_box.setFixedHeight(60)
        cap_layout.addWidget(self.caption_box)
        fields.addLayout(cap_layout)

        lyr_layout = QVBoxLayout()
        lyr_layout.addWidget(QLabel("Lyrics:"))
        self.lyrics_box = QTextEdit()
        self.lyrics_box.setReadOnly(True)
        self.lyrics_box.setFixedHeight(60)
        lyr_layout.addWidget(self.lyrics_box)
        fields.addLayout(lyr_layout)

        root.addLayout(fields)

        # Action buttons
        btn_row = QHBoxLayout()

        self.btn_copy_cap = QPushButton("Copy Caption")
        self.btn_copy_lyr = QPushButton("Copy Lyrics")
        self.btn_copy_all = QPushButton("Copy All")
        self.btn_fill = QPushButton("Fill ComfyUI Fields")
        self.btn_queue = QPushButton("Queue ComfyUI Workflow")
        self.preset_name = QLineEdit()
        self.preset_name.setPlaceholderText("Preset name...")
        self.preset_name.setFixedWidth(140)
        self.btn_save = QPushButton("Save Preset")
        self.btn_load = QPushButton("Load Preset")
        self.status_label = QLabel("ComfyUI: unknown")

        for w in [self.btn_copy_cap, self.btn_copy_lyr, self.btn_copy_all,
                  self.btn_fill, self.btn_queue,
                  self.preset_name, self.btn_save, self.btn_load,
                  self.status_label]:
            btn_row.addWidget(w)
        btn_row.addStretch()

        root.addLayout(btn_row)

        # Wire copy buttons
        self.btn_copy_cap.clicked.connect(
            lambda: self._copy(self.caption_box.toPlainText()))
        self.btn_copy_lyr.clicked.connect(
            lambda: self._copy(self.lyrics_box.toPlainText()))
        self.btn_copy_all.clicked.connect(self._copy_all)
        self.btn_fill.clicked.connect(
            lambda: self.push_requested.emit(
                self.caption_box.toPlainText(),
                self.lyrics_box.toPlainText()))
        self.btn_queue.clicked.connect(
            lambda: self.push_requested.emit(
                self.caption_box.toPlainText(),
                self.lyrics_box.toPlainText()))

    def update_output(self, caption: str, lyrics: str):
        self.caption_box.setPlainText(caption)
        self.lyrics_box.setPlainText(lyrics)

    def set_comfyui_status(self, online: bool):
        if online:
            self.status_label.setText("ComfyUI: Online ✓")
            self.status_label.setStyleSheet("color: #4caf50;")
        else:
            self.status_label.setText("ComfyUI: Offline ✗")
            self.status_label.setStyleSheet("color: #f44336;")

    def _copy(self, text: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _copy_all(self):
        cap = self.caption_box.toPlainText()
        lyr = self.lyrics_box.toPlainText()
        self._copy(f"--- Caption ---\n{cap}\n\n--- Lyrics ---\n{lyr}")
```

- [ ] **Step 2: Write main_window.py with tab placeholders**

`acetalk/ui/main_window.py`:
```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QSplitter, QToolBar, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from ..core.state import SessionState
from ..core.prompt_builder import build_prompt
from ..core.comfyui_api import ComfyUIClient
from .output_panel import OutputPanel


class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.state = SessionState()
        self.comfyui = ComfyUIClient(config.get("comfyui_url", "http://127.0.0.1:8188"))

        self.setWindowTitle("AceTalk — ACE-Step 1.5 Prompt Builder")
        self.setMinimumSize(1100, 800)

        self._build_ui()
        self._start_ping_timer()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Tab widget (top)
        self.tabs = QTabWidget()
        self._add_placeholder_tabs()
        splitter.addWidget(self.tabs)

        # Output panel (bottom)
        self.output_panel = OutputPanel()
        self.output_panel.setFixedHeight(160)
        splitter.addWidget(self.output_panel)
        splitter.setCollapsible(1, False)

        root.addWidget(splitter)

        self.output_panel.push_requested.connect(self._on_push_requested)

    def _add_placeholder_tabs(self):
        for name in ["Style", "Instruments", "Vocals", "Lyrics", "Parameters"]:
            placeholder = QLabel(f"{name} tab — coming soon",
                                 alignment=Qt.AlignmentFlag.AlignCenter)
            self.tabs.addTab(placeholder, name)

    def refresh_output(self):
        caption, lyrics = build_prompt(self.state)
        self.output_panel.update_output(caption, lyrics)

    def _start_ping_timer(self):
        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self._ping_comfyui)
        self.ping_timer.start(30_000)
        self._ping_comfyui()

    def _ping_comfyui(self):
        online = self.comfyui.ping()
        self.output_panel.set_comfyui_status(online)

    def _on_push_requested(self, caption: str, lyrics: str):
        pass  # wired in Task 16
```

- [ ] **Step 3: Update acetalk.py to use MainWindow**

`acetalk.py`:
```python
import sys
import json
import os
from PyQt6.QtWidgets import QApplication
from acetalk.ui.main_window import MainWindow

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULT_CONFIG = {
    "comfyui_url": "http://127.0.0.1:8188",
    "brave_api_key": "",
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def main():
    config = load_config()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the app**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
python acetalk.py
```

Expected: Window with 5 placeholder tabs and a persistent output panel at the bottom. Output panel has Copy/Push/Save buttons. ComfyUI status label shows online or offline.

- [ ] **Step 5: Commit**

```bash
git add acetalk/ui/main_window.py acetalk/ui/output_panel.py acetalk.py
git commit -m "feat: add main window with tab scaffold and persistent output panel"
```

---

## Task 10: Style tab

**Files:**
- Create: `acetalk/tabs/style_tab.py`
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Write style_tab.py**

`acetalk/tabs/style_tab.py`:
```python
import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QComboBox, QGroupBox,
    QScrollArea, QSizePolicy, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt

GENRES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "genres.json")
GENRES_PATH = os.path.normpath(GENRES_PATH)

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
        self._build_ui()

    def _load_genres(self) -> list:
        try:
            with open(GENRES_PATH) as f:
                return json.load(f).get("genres", [])
        except Exception:
            return []

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Genre grid
        genre_group = QGroupBox("Genre")
        grid_layout = QGridLayout(genre_group)
        cols = 5
        for i, genre in enumerate(self._genres):
            btn = QPushButton(genre["name"])
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, g=genre: self._select_genre(g))
            grid_layout.addWidget(btn, i // cols, i % cols)
            genre["_btn"] = btn
        root.addWidget(genre_group)

        # Controls row
        controls = QGroupBox("Style Details")
        ctrl_layout = QHBoxLayout(controls)

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
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        self.desc_label = QLabel("Select a genre above.")
        self.desc_label.setWordWrap(True)
        desc_layout.addWidget(self.desc_label)
        root.addWidget(desc_group)

        root.addStretch()

    def _select_genre(self, genre: dict):
        # Uncheck all other genre buttons
        for g in self._genres:
            if "_btn" in g:
                g["_btn"].setChecked(g is genre)

        self.state.genre = genre["name"]
        self.bpm_spin.setValue((genre["bpm_min"] + genre["bpm_max"]) // 2)
        self.key_combo.setCurrentText(genre["default_key"])
        self.scale_combo.setCurrentText(genre["default_scale"])
        self.mode_combo.setCurrentText(genre["default_mode"])
        self.time_combo.setCurrentText(genre["default_time_sig"])
        self.desc_label.setText(genre.get("description", ""))
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
```

- [ ] **Step 2: Wire Style tab into main_window.py**

In `acetalk/ui/main_window.py`, replace `_add_placeholder_tabs` with:

```python
def _add_placeholder_tabs(self):
    from ..tabs.style_tab import StyleTab
    from PyQt6.QtWidgets import QLabel
    from PyQt6.QtCore import Qt

    self.style_tab = StyleTab(self.state)
    self.style_tab.state_changed.connect(self.refresh_output)
    self.tabs.addTab(self.style_tab, "Style")

    for name in ["Instruments", "Vocals", "Lyrics", "Parameters"]:
        placeholder = QLabel(f"{name} tab — coming soon",
                             alignment=Qt.AlignmentFlag.AlignCenter)
        self.tabs.addTab(placeholder, name)
```

- [ ] **Step 3: Run and verify**

```bash
python acetalk.py
```

Expected: Style tab shows genre grid buttons. Clicking a genre fills BPM/Key/Scale/Mode/Time controls. Output panel caption updates live as you change controls.

- [ ] **Step 4: Commit**

```bash
git add acetalk/tabs/style_tab.py acetalk/ui/main_window.py
git commit -m "feat: add Style tab — genre grid, BPM/key/scale/mode controls, live output"
```

---

## Task 11: Instruments tab

**Files:**
- Create: `acetalk/tabs/instrument_tab.py`
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Write instrument_tab.py**

`acetalk/tabs/instrument_tab.py`:
```python
import json
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QGroupBox, QScrollArea, QFlowLayout,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

INSTRUMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "instruments.json")
INSTRUMENTS_PATH = os.path.normpath(INSTRUMENTS_PATH)


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
        self._active_modifiers = []
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

        mid.addWidget(QLabel("Instruments (click to add)"))
        self.inst_list = QListWidget()
        self.inst_list.itemDoubleClicked.connect(self._add_instrument)
        mid.addWidget(self.inst_list)

        add_btn = QPushButton("Add Selected →")
        add_btn.clicked.connect(lambda: self._add_instrument(self.inst_list.currentItem()))
        mid.addWidget(add_btn)

        # Modifier chips
        mod_group = QGroupBox("Modifiers (apply to last added)")
        mod_layout = QVBoxLayout(mod_group)
        modifiers = self._data.get("modifiers", {})
        self._mod_chips = {}
        for group_name, keywords in modifiers.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{group_name.title()}:"))
            for kw in keywords:
                chip = ChipButton(kw)
                chip.toggled.connect(self._on_modifier_changed)
                row.addWidget(chip)
                self._mod_chips[kw] = chip
            row.addStretch()
            mod_layout.addLayout(row)
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

    def _on_modifier_changed(self):
        pass  # Modifiers apply on next add

    def load_from_state(self):
        self.selected_list.clear()
        for phrase in self.state.instruments:
            self.selected_list.addItem(phrase)
```

- [ ] **Step 2: Wire into main_window.py**

In `_add_placeholder_tabs`, replace the Instruments placeholder:

```python
from ..tabs.instrument_tab import InstrumentTab

self.instrument_tab = InstrumentTab(self.state)
self.instrument_tab.state_changed.connect(self.refresh_output)
self.tabs.addTab(self.instrument_tab, "Instruments")
```

- [ ] **Step 3: Run and verify**

```bash
python acetalk.py
```

Expected: Instruments tab shows category list on left. Clicking a category populates the instrument list. Double-clicking or pressing "Add Selected" moves an instrument to the Selected panel with optional modifier prefix. Caption updates live.

- [ ] **Step 4: Commit**

```bash
git add acetalk/tabs/instrument_tab.py acetalk/ui/main_window.py
git commit -m "feat: add Instruments tab — category tree, modifier chips, selected list"
```

---

## Task 12: Vocals tab

**Files:**
- Create: `acetalk/tabs/vocalist_tab.py`
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Write vocalist_tab.py**

`acetalk/tabs/vocalist_tab.py`:
```python
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QTextEdit, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, pyqtSlot


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
        self._last_descriptors = []

        # Descriptor picker
        picker_group = QGroupBox("Vocal Descriptor Picker")
        picker_layout = QVBoxLayout(picker_group)
        for group_name, keywords in VOCAL_GROUPS.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{group_name}:"))
            for kw in keywords:
                from PyQt6.QtWidgets import QPushButton
                chip = QPushButton(kw)
                chip.setCheckable(True)
                chip.setFixedHeight(28)
                chip.toggled.connect(self._on_chip_toggled)
                self._chips[kw] = chip
                row.addWidget(chip)
            row.addStretch()
            picker_layout.addLayout(row)
        root.addWidget(picker_group)

        # Selected tags
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
            f"Range: {result.get('range', '—')}  Key: {result.get('preferred_key', '—')}  Style: {result.get('style', '—')}\n"
            f"Known for: {', '.join(result.get('known_for', []))}\n"
            f"ACE-Step: {', '.join(result.get('ace_step_descriptors', []))}"
        )
        self.result_text.setPlainText(text)
        self._last_descriptors = result.get("ace_step_descriptors", [])
        self.use_btn.setEnabled(bool(self._last_descriptors))

    def _use_descriptors(self):
        # Uncheck all, then check matching
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
```

- [ ] **Step 2: Wire into main_window.py**

```python
from ..tabs.vocalist_tab import VocalistTab

self.vocalist_tab = VocalistTab(self.state)
self.vocalist_tab.state_changed.connect(self.refresh_output)
self.tabs.addTab(self.vocalist_tab, "Vocals")
```

- [ ] **Step 3: Run and verify**

```bash
python acetalk.py
```

Expected: Vocals tab shows search bar, source selector, result card, chip picker. Searching "Billie Eilish" (local) returns the seeded entry. "Use These Descriptors" pre-checks chips. Caption updates live.

- [ ] **Step 4: Commit**

```bash
git add acetalk/tabs/vocalist_tab.py acetalk/ui/main_window.py
git commit -m "feat: add Vocals tab — artist search, descriptor chips, live caption update"
```

---

## Task 13: Lyrics tab

**Files:**
- Create: `acetalk/tabs/lyrics_tab.py`
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Write lyrics_tab.py**

`acetalk/tabs/lyrics_tab.py`:
```python
import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QGroupBox, QRadioButton, QButtonGroup,
    QLineEdit, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, pyqtSlot

TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "templates.json")
TEMPLATES_PATH = os.path.normpath(TEMPLATES_PATH)

STRUCTURE_TAGS = [
    "[Intro]", "[Intro: Atmospheric]", "[Verse]", "[Chorus]", "[Chorus: Anthemic]",
    "[Bridge]", "[Bridge: Modulated]", "[Build]", "[Drop]", "[Breakdown]",
    "[Solo: Virtuosic]", "[Drum Break]", "[Guitar Solo]", "[Piano Interlude]",
    "[Outro]", "[Fade Out]", "[Silence]",
]


class _OllamaWorker(QThread):
    token_ready = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, prompt, genre, key, mood, structure, model):
        super().__init__()
        self.prompt = prompt
        self.genre = genre
        self.key = key
        self.mood = mood
        self.structure = structure
        self.model = model

    def run(self):
        from acetalk.core.llm import generate_lyrics
        generate_lyrics(
            prompt=self.prompt,
            genre=self.genre,
            key=self.key,
            mood=self.mood,
            structure=self.structure,
            model=self.model,
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

        # Mode selector
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
        oll_layout = QHBoxLayout(self.ollama_group)
        oll_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        oll_layout.addWidget(self.model_combo)
        oll_layout.addWidget(QLabel("Prompt:"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe the song...")
        oll_layout.addWidget(self.prompt_input)
        self.gen_btn = QPushButton("Generate")
        self.gen_btn.clicked.connect(self._start_generation)
        oll_layout.addWidget(self.gen_btn)
        oll_layout.addStretch()
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

        # Editor
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
        if "(offline)" in model.lower() or "no models" in model.lower():
            return
        prompt = self.prompt_input.text().strip() or f"Write a {self.state.genre} song"
        self.editor.clear()
        self.gen_btn.setEnabled(False)
        self._worker = _OllamaWorker(
            prompt=prompt,
            genre=self.state.genre or "electronic",
            key=f"{self.state.key} {self.state.scale}",
            mood="",
            structure=self.structure_combo.currentText() if self.structure_combo.count() else "Verse-Chorus",
            model=model,
        )
        self._worker.token_ready.connect(self._on_token)
        self._worker.finished.connect(lambda: self.gen_btn.setEnabled(True))
        self._worker.start()

    @pyqtSlot(str)
    def _on_token(self, token: str):
        cursor = self.editor.textCursor()
        from PyQt6.QtGui import QTextCursor
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.editor.setTextCursor(cursor)

    def _on_text_changed(self):
        self.state.lyrics = self.editor.toPlainText()
        self.state_changed.emit()
```

- [ ] **Step 2: Wire into main_window.py**

```python
from ..tabs.lyrics_tab import LyricsTab

self.lyrics_tab = LyricsTab(self.state)
self.lyrics_tab.state_changed.connect(self.refresh_output)
self.tabs.addTab(self.lyrics_tab, "Lyrics")
```

- [ ] **Step 3: Run and verify**

```bash
python acetalk.py
```

Expected: Lyrics tab shows Template/Ollama toggle. Template mode: selecting structure + theme and clicking "Apply Template" fills the editor. Tag toolbar inserts tags at cursor. Ollama mode: model dropdown populated from running Ollama; Generate streams output into editor. Lyrics field in output panel updates live.

- [ ] **Step 4: Commit**

```bash
git add acetalk/tabs/lyrics_tab.py acetalk/ui/main_window.py
git commit -m "feat: add Lyrics tab — template scaffolds, Ollama streaming, tag toolbar"
```

---

## Task 14: Parameters tab

**Files:**
- Create: `acetalk/tabs/parameters_tab.py`
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Write parameters_tab.py**

`acetalk/tabs/parameters_tab.py`:
```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QDoubleSpinBox, QSpinBox, QComboBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import pyqtSignal, Qt


def _make_float_row(label: str, min_v: float, max_v: float, default: float,
                    decimals: int, step: float, tooltip: str):
    """Return (layout, spinbox) for a float parameter row."""
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
        self.steps_spin.setRange(10, 150)
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
```

- [ ] **Step 2: Wire into main_window.py**

Replace the last Parameters placeholder:

```python
from ..tabs.parameters_tab import ParametersTab

self.parameters_tab = ParametersTab(self.state)
self.parameters_tab.state_changed.connect(self.refresh_output)
self.tabs.addTab(self.parameters_tab, "Parameters")
```

Remove the remaining placeholder loop — all 5 tabs are now real.

Updated `_add_placeholder_tabs` in full:

```python
def _add_placeholder_tabs(self):
    from ..tabs.style_tab import StyleTab
    from ..tabs.instrument_tab import InstrumentTab
    from ..tabs.vocalist_tab import VocalistTab
    from ..tabs.lyrics_tab import LyricsTab
    from ..tabs.parameters_tab import ParametersTab

    self.style_tab = StyleTab(self.state)
    self.style_tab.state_changed.connect(self.refresh_output)
    self.tabs.addTab(self.style_tab, "Style")

    self.instrument_tab = InstrumentTab(self.state)
    self.instrument_tab.state_changed.connect(self.refresh_output)
    self.tabs.addTab(self.instrument_tab, "Instruments")

    self.vocalist_tab = VocalistTab(self.state)
    self.vocalist_tab.state_changed.connect(self.refresh_output)
    self.tabs.addTab(self.vocalist_tab, "Vocals")

    self.lyrics_tab = LyricsTab(self.state)
    self.lyrics_tab.state_changed.connect(self.refresh_output)
    self.tabs.addTab(self.lyrics_tab, "Lyrics")

    self.parameters_tab = ParametersTab(self.state)
    self.parameters_tab.state_changed.connect(self.refresh_output)
    self.tabs.addTab(self.parameters_tab, "Parameters")
```

- [ ] **Step 3: Run and verify**

```bash
python acetalk.py
```

Expected: All 5 tabs functional. Parameters tab shows sliders + spinboxes for all 7 parameters. Hovering shows tooltips. Changing a slider updates the spinbox and vice versa.

- [ ] **Step 4: Commit**

```bash
git add acetalk/tabs/parameters_tab.py acetalk/ui/main_window.py
git commit -m "feat: add Parameters tab — all ACE-Step generation params with sliders and tooltips"
```

---

## Task 15: Preset save/load

**Files:**
- Modify: `acetalk/ui/output_panel.py`
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Add save/load logic to main_window.py**

Add these methods to `MainWindow`:

```python
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "presets")

def _on_save_preset(self, name: str):
    import os, json
    if not name.strip():
        return
    os.makedirs(PRESETS_DIR, exist_ok=True)
    path = os.path.join(PRESETS_DIR, f"{name.strip()}.json")
    with open(path, "w") as f:
        json.dump(self.state.to_dict(), f, indent=2)

def _on_load_preset(self):
    import os, json
    from PyQt6.QtWidgets import QFileDialog
    path, _ = QFileDialog.getOpenFileName(
        self, "Load Preset", PRESETS_DIR, "JSON Files (*.json)"
    )
    if not path:
        return
    with open(path) as f:
        data = json.load(f)
    self.state = SessionState.from_dict(data)
    # Reload all tabs from new state
    self.style_tab.state = self.state
    self.instrument_tab.state = self.state
    self.instrument_tab.load_from_state()
    self.vocalist_tab.state = self.state
    self.lyrics_tab.state = self.state
    self.lyrics_tab.editor.setPlainText(self.state.lyrics)
    self.parameters_tab.state = self.state
    self.refresh_output()
```

Wire in `_build_ui` after `output_panel` is created:

```python
self.output_panel.btn_save.clicked.connect(
    lambda: self._on_save_preset(self.output_panel.preset_name.text()))
self.output_panel.btn_load.clicked.connect(self._on_load_preset)
```

- [ ] **Step 2: Run and verify**

```bash
python acetalk.py
```

Expected: Build a prompt across tabs. Enter a preset name and click Save Preset — a `.json` file appears in `presets/`. Click Load Preset — file picker opens, selecting a preset restores all tab state.

- [ ] **Step 3: Commit**

```bash
git add acetalk/ui/main_window.py
git commit -m "feat: add preset save/load — full session state serialized to JSON"
```

---

## Task 16: Settings dialog + ComfyUI push wiring

**Files:**
- Create: `acetalk/ui/settings_dialog.py`
- Modify: `acetalk/ui/main_window.py`
- Modify: `acetalk.py`

- [ ] **Step 1: Write settings_dialog.py**

`acetalk/ui/settings_dialog.py`:
```python
import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, config: dict, config_path: str, parent=None):
        super().__init__(parent)
        self.config = config
        self.config_path = config_path
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.comfyui_url = QLineEdit(self.config.get("comfyui_url", "http://127.0.0.1:8188"))
        form.addRow("ComfyUI URL:", self.comfyui_url)

        self.brave_key = QLineEdit(self.config.get("brave_api_key", ""))
        self.brave_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Brave API Key:", self.brave_key)

        root.addLayout(form)

        # Test ComfyUI connection
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test ComfyUI")
        self.test_result = QLabel("")
        self.test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_result)
        test_row.addStretch()
        root.addLayout(test_row)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _test_connection(self):
        from acetalk.core.comfyui_api import ping
        online = ping(self.comfyui_url.text().rstrip("/"))
        if online:
            self.test_result.setText("Connected ✓")
            self.test_result.setStyleSheet("color: #4caf50;")
        else:
            self.test_result.setText("Cannot connect ✗")
            self.test_result.setStyleSheet("color: #f44336;")

    def _save_and_accept(self):
        self.config["comfyui_url"] = self.comfyui_url.text().strip()
        self.config["brave_api_key"] = self.brave_key.text().strip()
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        self.accept()
```

- [ ] **Step 2: Add settings button to main_window toolbar + wire push**

Add to `MainWindow.__init__` after `_build_ui()`:

```python
self._add_toolbar()
```

Add method:

```python
def _add_toolbar(self):
    from PyQt6.QtWidgets import QToolBar
    from PyQt6.QtGui import QAction
    tb = QToolBar("Main")
    self.addToolBar(tb)
    settings_action = QAction("⚙ Settings", self)
    settings_action.triggered.connect(self._open_settings)
    tb.addAction(settings_action)

def _open_settings(self):
    from .settings_dialog import SettingsDialog
    dlg = SettingsDialog(self.config, CONFIG_PATH, self)
    if dlg.exec():
        self.comfyui = ComfyUIClient(self.config.get("comfyui_url", "http://127.0.0.1:8188"))
        import os
        os.environ["BRAVE_API_KEY"] = self.config.get("brave_api_key", "")
        self._ping_comfyui()
```

Add `CONFIG_PATH` import at top of main_window.py:

```python
import os
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
CONFIG_PATH = os.path.normpath(CONFIG_PATH)
```

Wire push in `_on_push_requested`:

```python
def _on_push_requested(self, caption: str, lyrics: str):
    from PyQt6.QtWidgets import QMessageBox
    result = self.comfyui.fill_fields(caption, lyrics, self.state)
    if "error" in result:
        QMessageBox.warning(self, "ComfyUI Error", result["error"])
    else:
        QMessageBox.information(self, "Sent", f"Queued: {result}")
```

- [ ] **Step 3: Run and verify**

```bash
python acetalk.py
```

Expected: Toolbar shows ⚙ Settings button. Clicking opens dialog with ComfyUI URL and Brave API key fields. Test button reports connection status. Saving writes `config.json`. Push to ComfyUI buttons trigger fill_fields or queue_workflow and show result dialog.

- [ ] **Step 4: Commit**

```bash
git add acetalk/ui/settings_dialog.py acetalk/ui/main_window.py acetalk.py
git commit -m "feat: add settings dialog, ComfyUI push wiring, toolbar"
```

---

## Task 17: Final test run + smoke check

- [ ] **Step 1: Run full test suite**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 2: Run the app end-to-end**

```bash
python acetalk.py
```

Manual smoke check:
1. Click "Psytrance" in Style tab → BPM/Key/Scale/Mode auto-fill → caption updates
2. Instruments tab → click Electronic/Synths → add "TB-303 synth bass" with "warm" modifier → appears in caption
3. Vocals tab → search "Billie Eilish" (local) → "Use These Descriptors" → chips selected → tags in caption
4. Lyrics tab → Template mode → Apply Template → lyrics appear in output panel
5. Parameters tab → change cfg_scale → slider and spinbox stay in sync
6. Output panel → Copy Caption → paste into a text editor to verify
7. Save Preset "test" → `presets/test.json` created → Load it back

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "feat: AceTalk v1 complete — all tabs, ComfyUI push, presets, settings"
```
