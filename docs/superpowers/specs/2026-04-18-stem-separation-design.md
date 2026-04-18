# AceTalk — Stem Separation Feature Design

**Date:** 2026-04-18  
**Status:** Approved

---

## Overview

Add a selectable stem output separation option to AceTalk with two complementary modes:

1. **ACE-Step native extract** — submit an existing audio file to ComfyUI using a new `workflow_extract_template.json` with `task_type=extract`. Outputs stems directly from the ACE-Step model.
2. **Demucs post-processing** — run `python -m demucs` as a subprocess on any MP3 (manually or automatically after generation completes).

Both modes are surfaced in a new **Stems tab** in the main tab widget.

---

## Architecture

### New files

| File | Purpose |
|------|---------|
| `acetalk/tabs/stems_tab.py` | New Stems tab — two group boxes (ACE-Step Extract + Demucs) |
| `acetalk/core/demucs_worker.py` | QThread that runs demucs subprocess, streams logs, emits signals |
| `workflow_extract_template.json` | ComfyUI workflow for ACE-Step extract mode |

### Modified files

| File | Change |
|------|--------|
| `acetalk/core/state.py` | Add `stems_auto_separate`, `stems_model` fields |
| `acetalk/core/comfyui_api.py` | Add `build_extract_workflow(input_path, state)` method; add `copy_to_comfyui_input(path)` helper |
| `acetalk/ui/main_window.py` | Add Stems tab; hook `_on_generation_done` to trigger demucs if auto-separate enabled |
| `acetalk/ui/settings_dialog.py` | Add "Stem Output Path" field |
| `acetalk.py` / `config.json` default | Add `stems_output_path: ""` to DEFAULT_CONFIG |

---

## SessionState Additions

```python
stems_auto_separate: bool = False   # trigger demucs after generation
stems_model: str = "htdemucs"       # "htdemucs" (4-stem) or "htdemucs_6s" (6-stem)
```

Both fields are serialised into presets via the existing `to_dict()` / `from_dict()` mechanism.

---

## Stems Tab UI

### ACE-Step Extract group
- `QLineEdit` + "Browse" `QPushButton` — picks input audio file path
- Small read-only `QTextEdit` — extraction status / what will be sent
- `QPushButton` "Send Extract Job to ComfyUI" — calls `build_extract_workflow`, then `send_workflow`, then starts `_GenerationMonitor` (reused from MainWindow)

### Demucs group
- `QComboBox` — "4-stem (htdemucs)" / "6-stem (htdemucs_6s)" — updates `state.stems_model`
- `QLabel` — shows resolved output path (from config `stems_output_path`, defaults to ComfyUI `output/audio/`)
- `QPushButton` "Separate Last MP3" — finds most recent MP3 (same logic as `_on_tag_mp3`), starts `DemucsWorker`
- `QCheckBox` "Auto-separate after generation" — updates `state.stems_auto_separate`
- Scrolling read-only `QTextEdit` — live log from demucs subprocess

---

## DemucsWorker

`QThread` in `acetalk/core/demucs_worker.py`.

```python
class DemucsWorker(QThread):
    log_line  = pyqtSignal(str)        # each stdout/stderr line
    finished  = pyqtSignal(list)       # list of output stem file paths
    failed    = pyqtSignal(str)        # error message
```

Runs: `python -m demucs --mp3 --two-stems=... -n <model> -o <output_path> <input_file>`  
Uses `QProcess` to stream output line-by-line into the log box.  
On exit code 0: scans output directory for new stems, emits `finished`.  
On non-zero exit: emits `failed` with last stderr lines.

---

## ComfyUIClient Additions

### `copy_to_comfyui_input(src_path: str) -> str`
Copies the selected audio file into ComfyUI's `input/` folder (required by `LoadAudio` node). Returns the filename (not full path) for use in the workflow.

### `build_extract_workflow(input_filename: str, state: SessionState) -> dict`
Loads `workflow_extract_template.json`, patches:
- `LoadAudio` → `filename` = `input_filename`
- `KSampler` → `steps` = `state.steps`, `seed`
- Returns `{"workflow": {...}}` or `{"error": "..."}` — same contract as `build_workflow`

---

## workflow_extract_template.json — Node Graph

| Node ID | Class | Key inputs |
|---------|-------|-----------|
| `1` | `LoadAudio` | `filename` (patched at send time) |
| `2` | `VAEEncodeAudio` | audio from node 1, vae from node VAELoader |
| `3` | `TextEncodeAceStepAudio1.5` | `tags=""`, `lyrics=""`, `task_type` implicitly `extract` via model behaviour |
| `4` | `KSampler` | steps, seed, model, positive/negative from encoder |
| `5` | `VAEDecodeAudio` | samples from KSampler, vae |
| `6` | `SaveAudioMP3` | `filename_prefix="stems/stem"` |
| `100` | `UNETLoader` | ACE-Step model |
| `101` | `DualCLIPLoader` | qwen clips |
| `102` | `VAELoader` | ace vae |

> **Note:** The exact node wiring needs validation in ComfyUI before the template is committed. The code path is fully wired — only the JSON changes if the graph needs adjustment.

---

## Auto-Separate Hook

In `MainWindow._on_generation_done()`, after showing the completion dialog:

```python
if self.state.stems_auto_separate and files:
    mp3_path = self._resolve_output_path(files[0])
    self.stems_tab.run_demucs(mp3_path)
```

`stems_tab.run_demucs(path)` starts `DemucsWorker` and switches focus to the Stems tab so the user can see progress.

---

## Config / Settings

`config.json` default: `"stems_output_path": ""`  
Empty string → demucs outputs to a `separated/` subfolder inside the ComfyUI `output/audio/` directory (demucs default behaviour when `-o` is set to that path).

`SettingsDialog` gets a new "Stem Output Path" row: `QLineEdit` + "Browse" button, same pattern as any future path config.

---

## Out of Scope

- Real-time stem preview / playback inside AceTalk
- Choosing which individual stems to keep/discard
- Demucs fine-tuned or custom models
- ACE-Step repaint or lego modes (separate future feature)
