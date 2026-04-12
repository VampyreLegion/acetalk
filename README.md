# AceTalk — ACE-Step 1.5 Prompt Builder

A PyQt6 desktop application for crafting, assembling, and pushing ACE-Step 1.5 music generation prompts directly to a local ComfyUI instance. Instead of hand-writing text prompts, AceTalk gives you a structured interface backed by a library of ACE-Step-verified keywords, with live caption preview, a lyric generator, and one-click ComfyUI integration.

---

## What AceTalk Connects To

### ACE-Step 1.5
The model AceTalk is built around. ACE-Step 1.5 is a music generation Diffusion Transformer that takes two text inputs:

- **Caption / Tags** — a comma-separated string of style keywords, BPM, key, scale, mode, instrument descriptors, and vocal style tags. This governs the genre, feel, instrumentation, and voice of the generated track.
- **Lyrics** — structured song text with `[Section]` tags like `[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Outro]`. The model reads these to plan song structure and render audio that matches the lyrics' phrasing and energy.

AceTalk assembles both of these strings from your UI selections and writes them into ComfyUI in real time.

### ComfyUI
AceTalk connects to your running ComfyUI instance over HTTP (default `http://127.0.0.1:8188`). It can:
- **Ping** the server every 30 seconds and show a green/red status indicator
- **Fill Fields** — patch the ACE-Step caption and lyrics nodes in your currently loaded workflow
- **Queue Workflow** — send a full workflow JSON to the `/prompt` endpoint to start generation immediately

You can install ACE-Step 1.5 as a ComfyUI custom node (it is available as a standalone node pack). AceTalk works with either version.

### Ollama
For AI-assisted lyric generation. AceTalk polls `http://localhost:11434` on startup to get the list of available Ollama models. Any model you have installed will appear in the Lyrics tab's model selector. Generation is streamed token-by-token into the lyrics editor in real time.

Ollama is optional — you can write lyrics manually, use templates, or skip lyrics entirely.

### Brave Search / DuckDuckGo
Used in the Vocals tab to research singers and vocal styles. When you search for an artist, AceTalk:
1. Checks the local `acetalk/data/vocals.json` database first
2. Falls back to Brave Search API if you have a key configured
3. Falls back to DuckDuckGo (no key required) if Brave is unavailable or fails

Web search results are automatically cached in `vocals.json` so subsequent searches for the same artist are instant and offline.

---

## Installation

### Requirements
- Python 3.10+
- A running ComfyUI instance with ACE-Step 1.5 nodes loaded (for push features)
- Ollama running locally (optional, for AI lyric generation)
- Brave Search API key (optional, for vocalist web search)

### Install Python dependencies

```bash
cd AceUser
pip install PyQt6 requests duckduckgo-search pytest pytest-qt
```

Or using the requirements file:

```bash
pip install -r requirements.txt
```

### Launch

```bash
cd AceUser
python3 acetalk.py
```

---

## First-Time Setup

On first launch, open **Settings** (gear icon in the toolbar, top-left):

| Field | Description |
|---|---|
| ComfyUI URL | URL of your running ComfyUI instance. Default: `http://127.0.0.1:8188` |
| Brave API Key | Optional. Enables Brave Search for vocalist research. Leave blank to use DuckDuckGo only. |

Click **Test ComfyUI** to verify the connection. Click **OK** to save — settings are written to `config.json` in the app directory.

---

## How to Use

The app has 5 tabs and a persistent output panel at the bottom. Work left-to-right through the tabs to build a complete prompt, then use the output panel to copy or send it to ComfyUI.

---

### Tab 1 — Style

Pick a genre from the grid. Clicking a genre card auto-fills:
- **BPM** — a default BPM from the genre's typical range
- **Key** — the genre's most common root key (e.g., A Minor for Psytrance)
- **Scale** — e.g., Minor, Major, Phrygian, Dorian, Lydian
- **Mode** — e.g., Phrygian (optional; only shown when meaningful)
- **Time Signature** — almost always 4/4, but Jazz and Blues have variations

You can override any of these after selecting a genre. All edits update the live Caption preview at the bottom of the screen.

**Available genres:** Psytrance, EDM, House, Trance, Blues, Jazz, Neo Soul, Heavy Metal, Emo, Classical, Ambient, Lo-Fi, Folk, Cinematic

**How BPM, Key, and Scale get into the caption:**
Style fields are only included in the caption when:
- A genre has been selected (provides context), OR
- The value differs from the default (120 BPM / C Major / 4/4)

This prevents the caption from being cluttered with defaults when you haven't chosen a style.

---

### Tab 2 — Instruments

Browse instrument categories on the left, then click keyword chips on the right to add them to your prompt. Selected instruments appear in a list you can remove items from individually.

**Categories:**
- Electronic/Synths (TB-303 bass, supersaw lead, wavetable pads, etc.)
- Keys (grand piano, Rhodes, Hammond B3, Fender Rhodes, etc.)
- Bass (electric bass, upright bass, synth bass, etc.)
- Drums/Percussion (TR-909, TR-808, acoustic drum kit, brushed drums, congas, etc.)
- Guitars (electric guitar, acoustic guitar, nylon string, slide guitar, etc.)
- Strings (violin, cello, string ensemble, pizzicato strings, etc.)
- Woodwinds/Brass (saxophone, trumpet, French horn, oboe, clarinet, etc.)

**Modifiers:** Add timbre, microphone, and mix descriptors (e.g., "warm", "distorted", "close-mic", "reverb-heavy") to fine-tune how ACE-Step renders the sound.

All selected items are assembled into a comma-separated instrument string that flows directly into the caption.

---

### Tab 3 — Vocals

Search for a vocalist or vocal style to pull ACE-Step-compatible descriptors.

**Search sources:**
- **Local** — search only the local `vocals.json` database (fast, offline)
- **Web** — search only via Brave/DDG
- **Both** (default) — check local first, fall back to web search

When a result appears, click **Use These Descriptors** to pre-select the matching vocal chips in the picker below.

**Vocal descriptor picker groups:**
- **Tone:** breathy, raspy, smooth, nasal, powerful, clear
- **Style:** whispered, belted, falsetto, spoken word, operatic
- **Texture:** airy, gritty, warm, bright, vibrato, melismatic
- **Gender:** male, female, androgynous

Selected tags are added directly to the caption alongside your instrument string.

**Adding artists to the local database:** Any artist found via web search is automatically saved to `acetalk/data/vocals.json`. You can also hand-edit that file to add detailed entries (preferred key, range, known hits, etc.) — see the Data Files section below.

---

### Tab 4 — Lyrics

Two modes, selectable at the top of the tab:

#### Template Mode
Pick a song structure, theme, and tone to generate a placeholder lyric scaffold:
- **Structures:** Verse-Chorus, Verse-Chorus-Bridge, Verse-Pre-Chorus-Chorus, Through-Composed, Extended Club Edit
- **Themes:** Love, Loss, Journey, Rebellion, Nature, Euphoria, Dark
- The scaffold fills in the lyrics editor with correct `[Section]` tags in place

Click **Apply Template** to generate. Edit the result freely.

#### Ollama Mode
Uses your local Ollama instance to write full lyrics:
- Select a model from the dropdown (auto-populated from running Ollama)
- Type a prompt describing what you want ("dark breakup song, hopeful ending")
- Select a structure to guide the AI
- Click **Generate** — lyrics stream in token by token

The AI is automatically given your style context (genre, key, mood from the Style tab) as a system prompt prefix. The `[Section]` tags are part of the instruction so the output is ready for ACE-Step.

#### Shared — Tag Toolbar
Insert ACE-Step structural tags at the cursor with one click:

`[Intro]` `[Verse]` `[Chorus]` `[Bridge]` `[Build]` `[Drop]` `[Breakdown]` `[Solo]` `[Outro]` `[Fade Out]` `[Silence]` `[Drum Break]` `[Guitar Solo]` `[Piano Interlude]`

Qualifier variants: `[Chorus: Anthemic]` `[Intro: Atmospheric]` `[Solo: Virtuosic]` `[Bridge: Modulated]`

The lyrics editor is always editable regardless of how the text was generated. What you see in the editor is exactly what gets sent to ACE-Step.

---

### Tab 5 — Parameters

Controls for the ACE-Step sampler node. All parameters have tooltips explaining their effect.

| Parameter | Range | Default | What it controls |
|---|---|---|---|
| `cfg_scale` | 1.0–20.0 | 7.0 | Prompt adherence. Higher = closer to caption but less variety |
| `temperature` | 0.1–2.0 | 1.0 | Randomness of token sampling. Higher = more creative, less stable |
| `top_p` | 0.0–1.0 | 0.95 | Nucleus sampling threshold. Works with temperature |
| `top_k` | 0–200 | 50 | Limits sampling to top K token candidates |
| `min_p` | 0.0–1.0 | 0.05 | Minimum probability cutoff. Filters very low-probability tokens |
| `duration` | 10–300s | 30 | Length of the generated audio in seconds |
| `steps` | 10–150 | 60 | Diffusion steps. More = higher quality but slower |
| `task_type` | — | text2music | Generation mode: `text2music`, `lego`, `repaint`, `extract` |

Each float parameter has a linked slider and spinbox — adjusting either one keeps both in sync.

---

### Output Panel (always visible at the bottom)

The output panel shows the assembled caption and lyrics in real time and provides all send/copy/save actions.

#### Caption and Lyrics display
Read-only text boxes updated automatically whenever you change anything in any tab. This is exactly what will be sent to ACE-Step.

#### Action buttons

| Button | Action |
|---|---|
| Copy Caption | Copy the caption string to clipboard |
| Copy Lyrics | Copy the lyrics to clipboard |
| Copy All | Copy both with labeled headers (`--- Caption ---` / `--- Lyrics ---`) |
| Fill ComfyUI Fields | Patch the ACE-Step caption and lyrics nodes in your loaded ComfyUI workflow |
| Queue ComfyUI Workflow | Send a full generation request to `/prompt` |
| Preset name field | Type a name for your preset |
| Save Preset | Save all current state to `presets/<name>.json` |
| Load Preset | Open a file picker over the `presets/` folder to restore a saved session |

#### ComfyUI status indicator
Shows **ComfyUI: Online ✓** (green) or **ComfyUI: Offline ✗** (red). Checked automatically every 30 seconds. A red indicator means Fill/Queue buttons will return an error.

---

## Presets

Presets save your entire session state — genre, BPM, key, instruments, vocal tags, lyrics, and all parameters — to a JSON file in the `presets/` folder.

**To save:** Type a name in the preset name field and click **Save Preset**.

**To load:** Click **Load Preset**, navigate to `presets/`, and select a `.json` file. All tabs update immediately.

Preset files are plain JSON and can be copied, shared, or version-controlled.

---

## How ACE-Step Prompting Works

ACE-Step 1.5 is not a command-based engine — it is a text-conditioned generative model. The "commands" are natural language phrases and structural tags that guide its creative planning.

### Caption (tags string)
The caption is a comma-separated list of descriptors. The more specific and consistent with ACE-Step's training data, the better the results. Order matters slightly — genre and tempo come first, followed by harmonic context, then instrumentation.

Example:
```
psytrance, 145 BPM, A Minor, Phrygian mode, 4/4 time, TB-303 synth bass, layered analog pads, electronic drums, tribal percussion, close-mic vocal, female vocal, breathy, airy
```

### Lyrics (structured text)
Section tags tell ACE-Step where the song transitions. The model uses them to allocate musical energy and arrangement density.

```
[Intro: Atmospheric]
The forest breathes in silence
A frequency beneath the ground

[Build: Heavy]
Frequencies collide
The signal finds the spine

[Drop: Virtuosic]
Let it rise, let it fall
Nothing left, we have it all

[Outro]
Returning to the source
The pulse dissolves to static
```

Qualifiers like `: Anthemic`, `: Dark`, `: Modulated` give additional direction about the energy or production style of that section.

---

## Data Files

All data files live in `acetalk/data/`. They are plain JSON and can be edited directly.

### `genres.json`
Defines the genre grid. Each entry:
```json
{
  "name": "Psytrance",
  "tags": ["psytrance", "dark", "hypnotic", "driving"],
  "bpm_min": 138, "bpm_max": 148,
  "default_key": "A", "default_scale": "Minor", "default_mode": "Phrygian",
  "default_time_sig": "4/4",
  "description": "High-energy psychedelic trance...",
  "typical_instruments": ["TB-303 synth bass", "layered analog pads", ...]
}
```
Add new genres by adding entries to this array. They appear automatically in the Style tab grid.

### `instruments.json`
Defines instrument categories and keyword chips. Structure:
```json
{
  "categories": {
    "Electronic/Synths": {
      "Lead Synths": ["supersaw lead", "FM synth lead", ...],
      "Pads": ["lush wavetable pads", "detuned pads", ...]
    }
  },
  "modifiers": {
    "timbre": ["warm", "bright", "distorted", ...],
    "mic": ["close-mic", "room mic", ...],
    "mix": ["reverb-heavy", "dry", "sidechain pumping", ...]
  }
}
```
Add new categories, subcategories, or individual keywords freely. Restart the app to pick up changes.

### `vocals.json`
Local database of artist vocal profiles. Pre-seeded with a few examples. Format:
```json
{
  "artists": [
    {
      "name": "Billie Eilish",
      "range": "mezzo-soprano",
      "preferred_key": "C Minor",
      "style": "pop, dark pop, indie pop",
      "known_for": ["Bad Guy", "Happier Than Ever"],
      "ace_step_descriptors": ["breathy", "whispery", "close-mic vocal", "soft", "intimate", "female vocal"]
    }
  ]
}
```
Web search results are automatically appended here. You can enrich auto-cached entries by adding `range`, `preferred_key`, `style`, and `known_for` fields manually.

### `templates.json`
Lyric scaffold templates by structure and theme. Format:
```json
{
  "structures": {
    "Verse-Chorus": {
      "layout": ["[Intro]", "[Verse]", "[Chorus]", "[Verse]", "[Chorus]", "[Outro]"],
      "themes": {
        "Love/Uplifting": "[Intro]\n...\n[Verse]\n..."
      }
    }
  }
}
```
Add new themes or structures by extending this file.

---

## Project Structure

```
AceUser/
  acetalk.py                    # Entry point — launches QApplication + MainWindow
  config.json                   # Runtime config (ComfyUI URL, Brave key) — git-ignored
  requirements.txt

  acetalk/
    core/
      state.py                  # SessionState dataclass (shared data model)
      prompt_builder.py         # Assembles caption + lyrics strings from SessionState
      comfyui_api.py            # HTTP client: ping, fill_fields, queue_workflow
      search.py                 # Brave + DDG vocalist search, local cache
      llm.py                    # Ollama: list_models(), generate_lyrics() (streaming)

    tabs/
      style_tab.py              # Tab 1: genre grid, BPM/key/scale/mode/time controls
      instrument_tab.py         # Tab 2: category tree, keyword chips, modifier chips
      vocalist_tab.py           # Tab 3: artist search, descriptor chip picker
      lyrics_tab.py             # Tab 4: template + Ollama modes, tag toolbar, editor
      parameters_tab.py         # Tab 5: cfg_scale, temp, top_p, top_k, min_p, steps, duration

    ui/
      main_window.py            # QMainWindow: tab widget + output panel, preset wiring
      output_panel.py           # Bottom panel: caption/lyrics display + action buttons
      settings_dialog.py        # Gear-icon dialog: ComfyUI URL, Brave key, test button

    data/
      genres.json               # Genre definitions (14 genres)
      instruments.json          # Instrument keyword library (7 categories)
      vocals.json               # Local artist vocal database (auto-updated by web search)
      templates.json            # Lyric scaffold templates

  presets/                      # User-saved session presets (one JSON per preset)
  tests/                        # pytest test suite (23 tests)
    conftest.py                 # QApplication fixture + sample_state fixture
    test_state.py
    test_prompt_builder.py
    test_search.py
    test_llm.py
    test_comfyui_api.py
```

---

## Running Tests

```bash
cd AceUser
python3 -m pytest tests/ -v
```

Expected: 23 tests, all passing. Tests cover the core logic (state, prompt building, search, LLM client, ComfyUI API) but not the UI tabs directly.

---

## Extending AceTalk

### Add a genre
Edit `acetalk/data/genres.json` — add an object with `name`, `tags`, `bpm_min`, `bpm_max`, `default_key`, `default_scale`, `default_mode`, `default_time_sig`, `description`, and `typical_instruments`. Restart the app.

### Add instrument keywords
Edit `acetalk/data/instruments.json` — find the right subcategory and append to its list, or add a new subcategory. Restart the app.

### Add a vocalist to the local DB
Edit `acetalk/data/vocals.json` — add an entry to the `artists` array following the schema above. No restart needed — the file is read on each search.

### Add a lyric template
Edit `acetalk/data/templates.json` — add a theme to an existing structure, or add a new structure following the existing schema. Restart the app.

### Add a new Ollama model
Just install it with `ollama pull <model>`. AceTalk reads the model list fresh each launch.

---

## Configuration Reference

`config.json` is created on first save from the Settings dialog. Fields:

```json
{
  "comfyui_url": "http://127.0.0.1:8188",
  "brave_api_key": ""
}
```

The Brave API key is also read from the `BRAVE_API_KEY` environment variable — setting it in the environment works without going through the Settings dialog.

---

## Error Handling

| Situation | Behavior |
|---|---|
| ComfyUI unreachable | Status indicator turns red, Fill/Queue buttons return an error dialog |
| Brave Search API fails | Silent fallback to DuckDuckGo; "(ddg)" source label in result |
| DuckDuckGo also fails | Search returns nothing; no crash |
| Ollama not running | Lyrics tab model dropdown shows "(Ollama offline)" |
| LLM generation error | Error message appended inline in the lyrics editor |
| Preset name is blank | Save silently does nothing |
| Loading invalid JSON preset | Python exception — check the file for formatting errors |

---

## System This Runs On

Built and tested on an ASUS GX10 128 GB AI workstation running Linux with an NVIDIA GPU. Python 3.12, ComfyUI with ACE-Step 1.5 custom nodes.
