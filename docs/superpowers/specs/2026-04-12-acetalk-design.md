# AceTalk — ACE Step 1.5 Prompt Builder
**Design Spec | 2026-04-12 (updated)**

## Overview

A PyQt6 desktop application for crafting, assembling, and pushing ACE Step 1.5 music generation prompts directly to a local ComfyUI instance. The app replaces manual text editing with a structured, data-driven interface backed by a library of ACE Step-verified keywords.

**Output modes (all three):**
- Copy caption/lyrics/both to clipboard
- Push to ComfyUI via REST API — fill fields in a running workflow, or queue a full workflow JSON
- Save/load named presets (full session state as JSON)

---

## Architecture

**Package structure:**
```
AceUser/
  acetalk.py                # Entry point, QMainWindow, tab setup, SessionState
  config.json               # User settings (URLs, API keys, last model)
  acetalk/
    tabs/
      style_tab.py          # Genre/style picker
      instrument_tab.py     # Instrument keyword builder
      vocalist_tab.py       # Web search + voice keyword extractor
      lyrics_tab.py         # Lyric generator (templates + Ollama)
      parameters_tab.py     # cfg_scale, temperature, task type, etc.
    core/
      prompt_builder.py     # Assembles all tab state into caption + lyrics strings
      comfyui_api.py        # HTTP client for ComfyUI /prompt endpoint
      search.py             # Brave Search API with DDG fallback
      llm.py                # Ollama client (model list + streaming generation)
      state.py              # SessionState dataclass
    data/
      genres.json           # Genre definitions
      instruments.json      # Instrument keyword library
      vocals.json           # Local artist/vocal style database (web results cached here)
      templates.json        # Lyric templates by genre, structure, theme, tone
  presets/                  # User-saved prompt presets (one JSON per preset)
```

**UI framework:** PyQt6, Fusion dark palette (no third-party theme dependency).

**Entry point:** `acetalk.py` launches `QMainWindow` with:
- A `QTabWidget` containing **5 tabs** (Style, Instruments, Vocals, Lyrics, Parameters)
- A **persistent output panel** docked at the bottom — always visible regardless of active tab

A `SessionState` dataclass instance is created at startup and passed to all tabs.

---

## SessionState

Shared dataclass held by the main window. Each tab reads/writes its own slice:

```python
@dataclass
class SessionState:
    # Tab 1
    caption_base: str = ""
    bpm: int = 120
    key: str = "C Major"
    scale: str = "Major"
    time_signature: str = "4/4"
    energy: int = 5  # 1-10 slider

    # Tab 2
    instrument_string: str = ""

    # Tab 3
    vocal_keywords: str = ""

    # Tab 4
    lyrics: str = ""

    # Tab 5
    cfg_scale: float = 7.0
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 50
    min_p: float = 0.0
    duration: int = 60
    variance: float = 0.5
    task_type: str = "text2music"
    repaint_start: float = 0.0
    repaint_end: float = 0.0
```

Final caption assembled in `output_tab.py`:
```
{caption_base}, {instrument_string}, {vocal_keywords}
```

---

## Tab Specifications

### Tab 1 — Style
- Scrollable grid of genre cards: EDM, Psytrance, Trance, House, Blues, Jazz, Neo Soul, Heavy Metal, Emo, Classical, Ambient, Lo-Fi, Folk, Cinematic, Funk (15 genres minimum)
- Each card loaded from `data/styles.json` — fields: name, description, bpm_range, key_suggestions, scale, time_signature, energy_default, example_caption, example_lyrics
- Clicking a card populates editable fields: BPM spinbox, key dropdown, scale/mode dropdown, time signature dropdown, energy slider (1–10)
- Live **Caption Preview** text box at bottom assembles the ACE Step caption string in real time
- Writes to: `state.caption_base`, `state.bpm`, `state.key`, `state.scale`, `state.time_signature`, `state.energy`

### Tab 2 — Instruments
- Left panel: category tree (Synths, Drums, Bass, Keys, Strings, Guitars, Woodwinds, Vocals, Production/FX)
- Right panel: keyword chips for selected category; click chip to toggle add/remove
- Live **Instrument String** preview shows assembled comma-separated keyword string
- Free-text override field for custom ACE Step descriptors
- Writes to: `state.instrument_string`

### Tab 3 — Vocals

- Search bar with source toggle: Local DB / Web / Both
- Web search uses Brave API with DDG fallback (same pipeline as NyxBioInfusor)
- Results card shows: artist name, vocal range, preferred key, genre, known hits, ACE-Step descriptor list
- `[Use These Descriptors]` button pre-selects matching chips in the picker below
- Web results not in `vocals.json` are cached there automatically
- **Vocal descriptor picker** (chip groups):
  - Tone: breathy, raspy, smooth, nasal, powerful, clear
  - Style: whispered, belted, falsetto, spoken word, operatic
  - Texture: airy, gritty, warm, bright, vibrato, melismatic
  - Gender: male, female, androgynous
- Selected vocal tags render directly into the caption
- Shows "(DDG fallback)" label when Brave is unavailable
- Writes to: `state.vocal_keywords`

### Tab 4 — Lyrics

Two modes toggled at the top of the tab:

**Template Mode:**
- Template structure dropdown (e.g. Verse-Chorus-Verse-Chorus-Bridge-Outro)
- Theme dropdown (Love, Loss, Journey, Rebellion, Nature, Euphoria, etc.)
- Tone dropdown (Uplifting, Dark, Melancholic, Aggressive, Dreamy, etc.)
- Generates a placeholder lyric scaffold with correct `[Section]` tags from `templates.json`

**Ollama Mode:**
- Model selector dropdown — auto-populated from running Ollama instance via `ollama list`
- Free-text prompt input for generation guidance
- Structure dropdown (same options as templates)
- Style context auto-injected from Style tab (genre, key, mood) as system prompt prefix
- `[Generate]` button streams Ollama output into the lyrics editor

**Shared (both modes):**
- Full-text lyrics editor (always editable regardless of source)
- Toolbar buttons to insert ACE-Step structure tags: `[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Build]`, `[Drop]`, `[Breakdown]`, `[Solo]`, `[Outro]`, `[Fade Out]`, `[Silence]`, `[Drum Break]`, `[Guitar Solo]`, `[Piano Interlude]`
- Qualifier variants available: `[Chorus: Anthemic]`, `[Intro: Atmospheric]`, `[Solo: Virtuosic]`, `[Bridge: Modulated]`
- Writes to: `state.lyrics`

### Tab 5 — Parameters
- Sliders + spinboxes for: `cfg_scale` (1.0–20.0), `temperature` (0.1–2.0), `top_p` (0.0–1.0), `top_k` (1–100), `min_p` (0.0–1.0)
- `duration` spinbox (seconds, 10–600)
- `variance` slider (0.1–0.7) — for repaint/lego tasks
- Task type selector: `text2music`, `repaint`, `lego`, `extract`
- Repaint start/end fields — visible only when `repaint` task type selected
- Tooltip on each parameter explaining what it controls in ACE Step context
- Writes to: all `state` parameter fields

### Persistent Output Panel (bottom, always visible)

- **Caption field** (read-only, live-updating): assembled genre tags + instrument phrases + vocal descriptors
- **Lyrics field** (read-only, live-updating): structured lyrics with `[Section]` tags
- **Action buttons:**
  - `[Copy Caption]` — copies caption to clipboard
  - `[Copy Lyrics]` — copies lyrics to clipboard
  - `[Copy All]` — copies both with labeled sections
  - `[Push to ComfyUI ▼]` — dropdown:
    - **Fill Fields**: finds ACE-Step nodes in running workflow via `/object_info`, patches caption + lyrics + parameters
    - **Queue Workflow**: sends complete workflow JSON to `/prompt` endpoint
  - `[Save Preset]` — saves full `SessionState` to `presets/<name>.json`
  - `[Load Preset]` — file picker over `presets/` directory
- ComfyUI status indicator: green "Online" / red "Offline" (ping every 30s via `QTimer`)

---

## Core Services

### `core/comfyui_api.py`
- `ping()` — GET `/system_stats`, returns bool
- `push_prompt(state: SessionState) -> dict` — loads base workflow JSON, injects caption + lyrics + parameters, POST to `/prompt`
- Base workflow JSON path configurable in `config.json` — user points this at their saved ACE Step ComfyUI workflow JSON
- Injection targets node titles in the workflow by name: `"ACE_caption"` node for the caption string, `"ACE_lyrics"` node for lyrics, and the sampler node for numeric parameters (cfg_scale, steps, etc.). Node title names are also configurable in `config.json` so the user can match their own workflow
- Connection ping runs on app start and every 30 seconds via `QTimer`

### `core/search.py`
- `search_vocalist(name: str) -> dict` — tries Brave API first, falls back to DDG
- Returns: `{bio, key_range, style, vocal_keywords: list[str]}`
- Brave API key read from `config.json`

### `core/llm.py`
- `list_models() -> list[str]` — polls `ollama list` + appends Claude models if key present
- `generate(prompt: str, model: str, stream_callback)` — routes to Ollama or Claude API based on model name prefix
- Streaming output delivered via callback to update lyrics text area in real time

### `core/state.py`
- `SessionState` dataclass
- `to_dict()` / `from_dict()` for preset save/load

---

## Settings Dialog
- Gear icon top-right of main window
- Fields: ComfyUI URL, Brave API key, Claude API key
- Saved to `config.json` on close
- ComfyUI connection tested inline with a "Test" button

---

## Error Handling

| Scenario | Behavior |
|---|---|
| ComfyUI unreachable | Status bar red, Send button disabled, retries every 30s |
| Brave search fails | Silent DDG fallback, "(DDG fallback)" label shown |
| Ollama not running | Dropdown shows "Ollama offline", Claude shown if key present |
| LLM generation error | Inline error in lyrics text area, no crash |
| Missing Brave key | Vocalist search disabled, tooltip explains how to fix |
| Invalid ComfyUI workflow | Raw API error shown in QMessageBox dialog |

---

## Data Files

### `data/styles.json` schema
```json
{
  "genres": [
    {
      "name": "Psytrance",
      "description": "High-energy psychedelic trance...",
      "bpm_range": [138, 150],
      "key_suggestions": ["A Minor", "D Minor", "F Minor"],
      "scale": "Phrygian",
      "time_signature": "4/4",
      "energy_default": 9,
      "example_caption": "High-energy Psytrance, 145 bpm, rolling triplet bassline...",
      "example_lyrics": "[Intro: Atmospheric]\n[Build: Heavy]\n[Drop: Virtuosic]..."
    }
  ]
}
```

### `data/instruments.json` schema
```json
{
  "categories": {
    "Synths": {
      "Acid/Bass": ["TB-303 silver box", "squelchy resonant filter", "distorted saw wave"],
      "Pads": ["lush wavetable pads", "granular textures", "detuned oscillators"]
    }
  }
}
```

---

## Dependencies
```
PyQt6
requests
anthropic       # Claude API
ollama          # Ollama Python client
```

Install: `pip install PyQt6 requests anthropic ollama`

---

## Out of Scope
- Audio playback within the app
- ComfyUI workflow editor
- Multi-user or cloud sync
- MIDI export
