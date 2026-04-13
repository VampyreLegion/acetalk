# AceTalk — ACE-Step 1.5 Music Composition Assistant

A PyQt6 desktop application for composing, assembling, and generating music with ACE-Step 1.5 via ComfyUI. AceTalk gives you a structured interface backed by a library of 150 genres and ACE-Step-verified keywords, with live caption preview, AI lyric generation, web-based artist research, and one-click ComfyUI workflow queuing.

---

## What AceTalk Connects To

### ACE-Step 1.5
AceTalk is built around the ACE-Step 1.5 `TextEncodeAceStepAudio1.5` node, which takes two text inputs:

- **Tags (Caption)** — comma-separated style keywords: genre, BPM, key, scale, mode, instrument descriptors, vocal style tags. Governs the genre, feel, instrumentation, and voice of the generated track.
- **Lyrics** — structured song text with `[Section]` tags (`[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Outro]`). The model reads these to plan song structure and render audio that matches the lyrics.

AceTalk assembles both strings from your UI selections and writes them directly into ComfyUI.

### ComfyUI
Connects over HTTP (configurable URL, default `http://127.0.0.1:8188`). AceTalk can:
- **Ping** every 30 seconds — green/red status indicator in the output panel
- **Queue Workflow** — fill a workflow template with your session data and POST to `/prompt`
- **Auto-load workflow into the browser** — via the AceTalkBridge extension (see below)
- **Monitor generation** — WebSocket monitor notifies you when generation completes

### AceTalkBridge (ComfyUI Extension)
A companion ComfyUI custom node included in `AceTalkBridge/`. After queuing, AceTalk pushes the filled workflow to ComfyUI's frontend so:
- The `TextEncodeAceStepAudio1.5` node shows the actual tags and lyrics that were sent
- Green node progress highlights appear during generation

**Install:** copy or symlink `AceTalkBridge/` into ComfyUI's `custom_nodes/` folder, then restart ComfyUI.

```bash
cp -r AceTalkBridge/ /path/to/ComfyUI/custom_nodes/AceTalkBridge
```

### Ollama
AI lyric generation via `http://localhost:11434`. Any installed Ollama model appears in the Lyrics and Easy tab model selectors. Generation streams token-by-token. Supports `<think>...</think>` stripping for reasoning models (Qwen3, etc.). Optional — you can write lyrics manually.

### Brave Search / DuckDuckGo
Used in the Easy tab and Vocals tab to research bands and singers. Priority order:
1. Local `vocals.json` database (instant, offline)
2. Brave Search API (if key configured in Settings)
3. DuckDuckGo fallback (no key required)

---

## Installation

### Requirements
- Python 3.10+
- Running ComfyUI instance with ACE-Step 1.5 nodes loaded
- Ollama running locally (optional, for AI generation)
- Brave Search API key (optional, for web research)

### Install Python dependencies

```bash
cd AceUser
pip install -r requirements.txt
```

Or manually:

```bash
pip install PyQt6 requests websocket-client mutagen ddgs pytest pytest-qt
```

### Install AceTalkBridge into ComfyUI

```bash
cp -r AceTalkBridge/ /path/to/ComfyUI/custom_nodes/AceTalkBridge
# Restart ComfyUI
```

### Workflow Template

AceTalk needs a ComfyUI workflow saved in API format to queue jobs:

1. Build your ACE-Step workflow in ComfyUI
2. Click the floppy icon → **Save (API format)**
3. Save as `AceUser/workflow_template.json`

A complete working template for ACE-Step 1.5 XL Turbo is included.

### Launch

```bash
cd AceUser
python3 acetalk.py
```

---

## First-Time Setup

Open **Settings** (⚙ gear icon, top toolbar):

| Field | Description |
|---|---|
| ComfyUI URL | URL of your ComfyUI instance. Default: `http://127.0.0.1:8188` |
| Ollama URL | URL of your Ollama instance. Default: `http://localhost:11434` |
| Brave API Key | Optional. Enables Brave Search for artist research. |

Click **Test ComfyUI** to verify. Settings are saved to `config.json`.

---

## Tabs

### Overview
A fully editable summary of the entire song. All fields from all tabs are shown on one screen — edit anything here and it propagates back immediately. Includes:
- Style (genre, BPM, key, scale, mode, time signature)
- Instruments list
- Vocal tags
- Lyrics editor
- All generation parameters
- Song metadata (title, artist, album, year, genres, description)
- Read-only assembled caption (shows the final tags string in green)

### Easy
Enter a **band/artist** and **vocalist**, optionally a topic, mood, subject, and name override. Click **Research + Generate**:
1. Web-searches both the band and vocalist
2. Sends results to Ollama with your guidance fields
3. Receives a full ACE-Step caption + structured lyrics
4. Parses the caption to extract genre, BPM, key, instruments, vocal tags
5. Populates all tabs automatically and switches to Overview for review

Use Easy to get a complete starting point in one click.

### Style
Browse 150 genres organized into 17 parent categories (Alternative, Blues, Classical, Country, Dance, Electronic, Folk, Hip-Hop, Jazz, Latin, Metal, New Age, Pop, R&B/Soul, Reggae, Rock, World).

- **Left sidebar** — select a category
- **Right panel** — scrollable 4-column grid of genres in that category
- **Search box** — filter by genre name, category, or tags across all 150 genres

Clicking a genre auto-fills BPM, Key, Scale, Mode, and Time Signature. Description and typical instruments shown below.

### Instruments
Browse instrument categories on the left, click keyword chips to add them to your prompt. Each phrase is ACE-Step-compatible (e.g. "TB-303 synth bass", "Rhodes electric piano", "brushed drums").

### Vocals
Search for a vocalist to pull ACE-Step-compatible vocal descriptors. Results are cached locally. Select vocal quality chips (tone, style, texture, gender) to build the vocal tag string.

### Lyrics
Two modes:

**Template mode** — pick a song structure and theme to generate a structural scaffold with `[Section]` tags in place.

**Ollama mode** — AI-assisted lyric generation. Fields:
- Model selector (auto-populated from running Ollama)
- Topic / Mood
- Subject (what or who the song is about)
- Name override (force a specific character name into the lyrics)
- Song structure selector

Generation streams token-by-token. `<think>...</think>` blocks from reasoning models are stripped automatically. Use the `[Section]` tag toolbar to insert structural tags at the cursor.

### Parameters
Controls for the ACE-Step sampler. All fields have tooltips.

| Parameter | Default | Description |
|---|---|---|
| `cfg_scale` | 2.0 | Prompt adherence. ACE-Step XL Turbo default. |
| `temperature` | 0.85 | Sampling randomness. |
| `top_p` | 0.9 | Nucleus sampling cutoff. |
| `top_k` | 0 | Top-K candidates (0 = disabled). |
| `min_p` | 0.0 | Minimum probability threshold. |
| `duration` | 120s | Generated audio length in seconds. |
| `steps` | 8 | Diffusion steps. 8 is correct for the XL Turbo model. |
| `task_type` | text2music | Generation mode. |
| **Seed** | random | Seed for generation. |
| **Lock seed** | off | Reuse seed every run for iterative refinement. |

#### Seed / Iterative Refinement
- **Unlocked (default):** new random seed every run — every generation is unique
- **Locked:** same seed every run — tweak tags, lyrics, or BPM to iterate on the same musical foundation
- **New Random Seed button:** generate a fresh seed while staying locked
- After each queue, the seed used is shown in the payload dialog and updated in the Parameters tab

---

## Output Panel

Always visible at the bottom of the window.

| Control | Description |
|---|---|
| Caption box | Live assembled tags string |
| Lyrics box | Live lyrics |
| Copy Caption | Copy tags to clipboard |
| Copy Lyrics | Copy lyrics to clipboard |
| Copy All | Copy both with `--- Caption ---` / `--- Lyrics ---` headers |
| Preview Raw Payload | Show exact JSON sent to the ACE-Step node |
| Fill ComfyUI Fields | Patch the open workflow's ACE-Step node (no queue) |
| Queue ComfyUI Workflow | Send full workflow to `/prompt` and start generation |
| Tag Last MP3 | Write ID3 tags to the most recent MP3 in ComfyUI's output folder |
| Preset name + Save | Save session to `presets/<name>.json` |
| Load Preset | Restore a saved session — all tabs update immediately |
| Status indicator | ComfyUI Online/Offline, and generation Done/Error state |

### After Queuing
When you click **Queue ComfyUI Workflow**:
1. Filled workflow sent to ComfyUI `/prompt`
2. AceTalkBridge pushes the workflow to ComfyUI's browser (nodes show actual text + progress highlights)
3. A **payload dialog** shows the exact tags, lyrics, parameters, and seed used
4. Background WebSocket monitor watches for completion
5. **Completion popup** appears when ComfyUI finishes, with output filename

---

## Song Metadata + MP3 Tagging

The **Song Metadata** section in the Overview tab holds:
- Song Title, Artist, Album, Year
- Genre Tags (comma-separated, written to ID3 TCON)
- Description (written to ID3 COMM comment)

Click **Tag Last MP3** in the output panel to write these as ID3 tags to the most recently generated MP3 in ComfyUI's `output/audio/` folder.

---

## Presets

Presets save your entire session — genre, BPM, key, instruments, vocals, lyrics, all parameters, seed state, and metadata — to a JSON file in `presets/`.

- **Save:** type a name and click Save Preset
- **Load:** click Load Preset, pick a `.json` file — all tabs update immediately
- Plain JSON, shareable and version-controllable

---

## AceTalkBridge — How It Works

`AceTalkBridge/` is a minimal ComfyUI custom node that:

1. Registers `POST /acetalk/load` on ComfyUI's aiohttp server
2. When AceTalk sends the filled workflow there, broadcasts it to all connected browser clients via WebSocket (`sid=None` broadcast)
3. `web/acetalk_bridge.js` listens for the broadcast and calls `app.loadGraphData()` on the canvas

Result: every time you queue from AceTalk, ComfyUI's browser UI automatically loads the filled workflow — the `TextEncodeAceStepAudio1.5` node displays the actual tags and lyrics, and node execution highlights work correctly.

If the bridge is not installed, AceTalk still queues and generates normally.

---

## Data Files

All data in `acetalk/data/` — plain JSON, edit directly.

### `genres.json`
150 genres with parent categories. Each entry:
```json
{
  "name": "Psytrance",
  "parent": "Electronic",
  "tags": ["psytrance", "dark", "hypnotic", "driving"],
  "bpm_min": 138, "bpm_max": 148,
  "default_key": "A", "default_scale": "Minor", "default_mode": "Phrygian",
  "default_time_sig": "4/4",
  "description": "High-energy psychedelic trance...",
  "typical_instruments": ["TB-303 synth bass", "layered analog pads"]
}
```

### `instruments.json`
Instrument keyword chips organized by category and subcategory.

### `vocals.json`
Local artist vocal profiles. Auto-updated by web search. Add `range`, `preferred_key`, `style`, `known_for`, and `ace_step_descriptors` for best results.

### `templates.json`
Lyric scaffold templates by structure and theme.

---

## Project Structure

```
AceUser/
  acetalk.py                    # Entry point
  config.json                   # Runtime config — git-ignored
  config.example.json           # Template config for new installs
  workflow_template.json        # ACE-Step ComfyUI workflow (API format)
  last_sent.json                # Written after each queue — load in ComfyUI to inspect
  requirements.txt

  AceTalkBridge/                # ComfyUI custom node — copy to ComfyUI/custom_nodes/
    __init__.py                 # Server route + WebSocket broadcast
    web/
      acetalk_bridge.js         # Browser extension — loads workflow on broadcast

  acetalk/
    core/
      state.py                  # SessionState dataclass (shared data model)
      prompt_builder.py         # Assembles caption + lyrics from SessionState
      comfyui_api.py            # HTTP client: ping, fill_fields, queue, bridge call
      search.py                 # Brave + DuckDuckGo search, local vocal cache
      llm.py                    # Ollama: list_models(), generate_lyrics() (streaming)

    tabs/
      overview_tab.py           # Fully editable song overview — all fields in one place
      easy_tab.py               # Band + vocalist research → auto-generate full prompt
      style_tab.py              # 150-genre browser with category sidebar + search
      instrument_tab.py         # Instrument keyword chips by category
      vocalist_tab.py           # Artist search + vocal descriptor picker
      lyrics_tab.py             # Template + Ollama modes, section tag toolbar
      parameters_tab.py         # Sampler params + seed/lock controls

    ui/
      main_window.py            # QMainWindow: tabs, output panel, generation monitor
      output_panel.py           # Caption/lyrics display + all action buttons
      settings_dialog.py        # ComfyUI URL, Ollama URL, Brave key

    data/
      genres.json               # 150 genres in 17 parent categories
      instruments.json          # Instrument keyword library
      vocals.json               # Local artist vocal database (auto-updated)
      templates.json            # Lyric scaffold templates

  presets/                      # User-saved session presets (git-ignored)
  tests/                        # pytest test suite
```

---

## Running Tests

```bash
cd AceUser
python3 -m pytest tests/ -v
```

---

## How ACE-Step Prompting Works

### Tags string
Comma-separated descriptors. Genre and tempo first, then harmonic context, then instrumentation.

```
psytrance, 145 BPM, A Minor, Phrygian mode, 4/4 time, TB-303 synth bass,
layered analog pads, electronic drums, tribal percussion, female vocal, breathy, airy
```

### Lyrics
Section tags guide the model's structural and energy planning.

```
[Intro: Atmospheric]
The forest breathes in silence

[Build: Heavy]
Frequencies collide, the signal finds the spine

[Drop: Virtuosic]
Let it rise, let it fall

[Outro]
The pulse dissolves to static
```

Qualifiers like `: Anthemic`, `: Dark`, `: Modulated` give production direction for each section.

---

## Error Handling

| Situation | Behavior |
|---|---|
| ComfyUI unreachable | Status turns red; queue buttons show error dialog |
| AceTalkBridge not installed | Queue still works; nodes don't auto-update in browser |
| Brave Search fails | Silent fallback to DuckDuckGo |
| DuckDuckGo fails | Search returns nothing, no crash |
| Ollama offline | Model dropdown shows "(Ollama offline)" |
| Reasoning model `<think>` output | Stripped automatically |
| Same job queued twice | New random seed each time (unless seed is locked) |

---

## System

Built on Nyx — ASUS GX10 128 GB AI workstation, Linux, NVIDIA GPU. Python 3.12, ComfyUI with ACE-Step 1.5 XL Turbo (`acestep_v1.5_xl_turbo_bf16.safetensors`).
