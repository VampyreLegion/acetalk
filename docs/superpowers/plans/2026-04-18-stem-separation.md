# Stem Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Stems tab to AceTalk with ACE-Step native extract mode and demucs post-processing (manual + auto-separate after generation).

**Architecture:** A new `StemsTab` widget houses two independent group boxes — ACE-Step Extract (submits a second ComfyUI workflow) and Demucs (runs `python -m demucs` in a `QThread`). Auto-separate hooks into the existing `_on_generation_done` signal in `MainWindow`. All new state fields persist in presets via the existing `SessionState` round-trip.

**Tech Stack:** PyQt6, demucs (pip install), subprocess.Popen for streaming output, existing ComfyUI WebSocket monitor.

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `acetalk/core/state.py` | Add `stems_auto_separate`, `stems_model` fields |
| Modify | `acetalk.py` | Add `stems_output_path` to `DEFAULT_CONFIG` |
| Modify | `acetalk/ui/settings_dialog.py` | Add Stem Output Path field |
| Create | `acetalk/core/demucs_worker.py` | `QThread` running demucs subprocess |
| Modify | `acetalk/core/comfyui_api.py` | Add `copy_to_comfyui_input`, `build_extract_workflow` |
| Create | `workflow_extract_template.json` | ComfyUI node graph for ACE-Step extract mode |
| Create | `acetalk/tabs/stems_tab.py` | New Stems tab UI |
| Modify | `acetalk/ui/main_window.py` | Add Stems tab; hook auto-separate into `_on_generation_done` |
| Modify | `requirements.txt` | Add `demucs` |
| Modify | `tests/test_state.py` | Tests for new state fields |
| Create | `tests/test_demucs_worker.py` | Tests for DemucsWorker command construction |
| Modify | `tests/test_comfyui_api.py` | Tests for new ComfyUIClient methods |

---

## Task 1: SessionState — Add Stem Fields

**Files:**
- Modify: `acetalk/core/state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_state.py`:

```python
def test_stem_defaults():
    s = SessionState()
    assert s.stems_auto_separate is False
    assert s.stems_model == "htdemucs"


def test_stem_fields_round_trip():
    s = SessionState(stems_auto_separate=True, stems_model="htdemucs_6s")
    d = s.to_dict()
    s2 = SessionState.from_dict(d)
    assert s2.stems_auto_separate is True
    assert s2.stems_model == "htdemucs_6s"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
python -m pytest tests/test_state.py::test_stem_defaults tests/test_state.py::test_stem_fields_round_trip -v
```

Expected: FAIL — `TypeError: SessionState.__init__() got an unexpected keyword argument 'stems_auto_separate'`

- [ ] **Step 3: Add fields to SessionState**

In `acetalk/core/state.py`, add after the `lock_seed` field:

```python
    # Stem separation
    stems_auto_separate: bool = False   # run demucs automatically after generation
    stems_model: str = "htdemucs"       # "htdemucs" (4-stem) or "htdemucs_6s" (6-stem)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_state.py::test_stem_defaults tests/test_state.py::test_stem_fields_round_trip -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
python -m pytest tests/ -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add acetalk/core/state.py tests/test_state.py
git commit -m "feat(state): add stems_auto_separate and stems_model fields"
```

---

## Task 2: Config — stems_output_path + Settings Dialog

**Files:**
- Modify: `acetalk.py`
- Modify: `acetalk/ui/settings_dialog.py`

- [ ] **Step 1: Add `stems_output_path` to DEFAULT_CONFIG in `acetalk.py`**

Replace the existing `DEFAULT_CONFIG` block:

```python
DEFAULT_CONFIG = {
    "comfyui_url": "http://127.0.0.1:8188",
    "brave_api_key": "",
    "stems_output_path": "",
}
```

- [ ] **Step 2: Add Stem Output Path field to SettingsDialog**

In `acetalk/ui/settings_dialog.py`, replace the entire file content:

```python
import json
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QDialogButtonBox,
    QFileDialog,
)


class SettingsDialog(QDialog):
    def __init__(self, config: dict, config_path: str, parent=None):
        super().__init__(parent)
        self.config = config
        self.config_path = config_path
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
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

        # Stem output path row
        stem_row = QHBoxLayout()
        self.stems_path = QLineEdit(self.config.get("stems_output_path", ""))
        self.stems_path.setPlaceholderText("Leave blank for ComfyUI output/audio/separated/")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_stems_path)
        stem_row.addWidget(self.stems_path)
        stem_row.addWidget(browse_btn)
        form.addRow("Stem Output Path:", stem_row)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test ComfyUI")
        self.test_result = QLabel("")
        self.test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_result)
        test_row.addStretch()
        root.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_stems_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Stem Output Folder")
        if path:
            self.stems_path.setText(path)

    def _test_connection(self):
        from acetalk.core.comfyui_api import ping
        online = ping(self.comfyui_url.text().rstrip("/"))
        if online:
            self.test_result.setText("Connected \u2713")
            self.test_result.setStyleSheet("color: #4caf50;")
        else:
            self.test_result.setText("Cannot connect \u2717")
            self.test_result.setStyleSheet("color: #f44336;")

    def _save_and_accept(self):
        self.config["comfyui_url"] = self.comfyui_url.text().strip()
        self.config["brave_api_key"] = self.brave_key.text().strip()
        self.config["stems_output_path"] = self.stems_path.text().strip()
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        self.accept()
```

- [ ] **Step 3: Run existing tests to verify no regression**

```bash
python -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add acetalk.py acetalk/ui/settings_dialog.py
git commit -m "feat(config): add stems_output_path to config and settings dialog"
```

---

## Task 3: DemucsWorker

**Files:**
- Create: `acetalk/core/demucs_worker.py`
- Create: `tests/test_demucs_worker.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_demucs_worker.py`:

```python
import sys
from unittest.mock import patch, MagicMock, call
from acetalk.core.demucs_worker import DemucsWorker


def test_worker_builds_correct_4stem_command():
    worker = DemucsWorker(
        input_path="/output/audio/song.mp3",
        model="htdemucs",
        output_dir="/output/separated",
    )
    cmd = worker._build_command()
    assert sys.executable in cmd
    assert "-m" in cmd
    assert "demucs" in cmd
    assert "--mp3" in cmd
    assert "-n" in cmd
    assert "htdemucs" in cmd
    assert "-o" in cmd
    assert "/output/separated" in cmd
    assert "/output/audio/song.mp3" in cmd


def test_worker_builds_correct_6stem_command():
    worker = DemucsWorker(
        input_path="/output/audio/song.mp3",
        model="htdemucs_6s",
        output_dir="/output/separated",
    )
    cmd = worker._build_command()
    assert "htdemucs_6s" in cmd


def test_worker_resolves_stem_paths(tmp_path):
    model = "htdemucs"
    track = "song"
    stem_dir = tmp_path / model / track
    stem_dir.mkdir(parents=True)
    (stem_dir / "vocals.mp3").write_text("")
    (stem_dir / "drums.mp3").write_text("")
    (stem_dir / "bass.mp3").write_text("")
    (stem_dir / "other.mp3").write_text("")

    worker = DemucsWorker(
        input_path=f"/some/path/{track}.mp3",
        model=model,
        output_dir=str(tmp_path),
    )
    stems = worker._collect_stems()
    assert len(stems) == 4
    assert all(s.endswith(".mp3") for s in stems)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_demucs_worker.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'acetalk.core.demucs_worker'`

- [ ] **Step 3: Create `acetalk/core/demucs_worker.py`**

```python
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class DemucsWorker(QThread):
    log_line = pyqtSignal(str)    # each stdout/stderr line
    finished = pyqtSignal(list)   # list of output stem file paths
    failed   = pyqtSignal(str)    # error message

    def __init__(self, input_path: str, model: str, output_dir: str, parent=None):
        super().__init__(parent)
        self.input_path = input_path
        self.model = model
        self.output_dir = output_dir

    def _build_command(self) -> list:
        return [
            sys.executable, "-m", "demucs",
            "--mp3",
            "-n", self.model,
            "-o", self.output_dir,
            self.input_path,
        ]

    def _collect_stems(self) -> list:
        track_name = Path(self.input_path).stem
        stem_dir = Path(self.output_dir) / self.model / track_name
        stems = sorted(str(p) for p in stem_dir.glob("*.mp3"))
        if not stems:
            stems = sorted(str(p) for p in stem_dir.glob("*.wav"))
        return stems

    def run(self):
        cmd = self._build_command()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in iter(proc.stdout.readline, ""):
                stripped = line.rstrip()
                if stripped:
                    self.log_line.emit(stripped)
            proc.wait()
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        if proc.returncode != 0:
            self.failed.emit(f"demucs exited with code {proc.returncode}")
            return

        stems = self._collect_stems()
        self.finished.emit(stems)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_demucs_worker.py -v
```

Expected: all 3 pass.

- [ ] **Step 5: Add demucs to requirements.txt**

Append to `requirements.txt`:

```
demucs
```

- [ ] **Step 6: Install demucs**

```bash
pip install demucs
```

Expected: installs without error. Verify: `python -m demucs --help` shows usage.

- [ ] **Step 7: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add acetalk/core/demucs_worker.py tests/test_demucs_worker.py requirements.txt
git commit -m "feat(demucs): add DemucsWorker QThread for subprocess stem separation"
```

---

## Task 4: ComfyUIClient — Extract Workflow Support

**Files:**
- Modify: `acetalk/core/comfyui_api.py`
- Create: `workflow_extract_template.json`
- Modify: `tests/test_comfyui_api.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_comfyui_api.py`:

```python
import os
import json
import shutil
import tempfile


def test_copy_to_comfyui_input_copies_file(tmp_path):
    src = tmp_path / "song.mp3"
    src.write_bytes(b"fake mp3 data")
    dest_dir = tmp_path / "input"
    dest_dir.mkdir()

    client = ComfyUIClient()
    result = client.copy_to_comfyui_input(str(src), input_dir=str(dest_dir))

    assert result == "song.mp3"
    assert (dest_dir / "song.mp3").exists()


def test_build_extract_workflow_patches_filename(tmp_path):
    # Write a minimal extract template
    template = {
        "1": {
            "class_type": "LoadAudio",
            "inputs": {"filename": "placeholder.mp3", "start_time": 0, "end_time": 0}
        },
        "2": {
            "class_type": "KSampler",
            "inputs": {"seed": 0, "steps": 8}
        },
    }
    template_path = tmp_path / "workflow_extract_template.json"
    template_path.write_text(json.dumps(template))

    client = ComfyUIClient()
    result = client.build_extract_workflow(
        input_filename="mysong.mp3",
        state=SessionState(steps=12, seed=42, lock_seed=True),
        template_path=str(template_path),
    )

    assert "workflow" in result
    wf = result["workflow"]
    assert wf["1"]["inputs"]["filename"] == "mysong.mp3"
    assert wf["2"]["inputs"]["steps"] == 12


def test_build_extract_workflow_returns_error_when_no_template(tmp_path):
    client = ComfyUIClient()
    result = client.build_extract_workflow(
        input_filename="song.mp3",
        state=SessionState(),
        template_path=str(tmp_path / "missing.json"),
    )
    assert "error" in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_comfyui_api.py::test_copy_to_comfyui_input_copies_file tests/test_comfyui_api.py::test_build_extract_workflow_patches_filename tests/test_comfyui_api.py::test_build_extract_workflow_returns_error_when_no_template -v
```

Expected: FAIL — `AttributeError: 'ComfyUIClient' object has no attribute 'copy_to_comfyui_input'`

- [ ] **Step 3: Add methods to ComfyUIClient in `acetalk/core/comfyui_api.py`**

Add the following two methods inside the `ComfyUIClient` class, after `send_workflow`:

```python
    def _default_input_dir(self) -> str:
        """Resolve ComfyUI's input/ folder relative to this file's location."""
        import os
        comfy_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        return os.path.join(comfy_root, "input")

    def _default_extract_template_path(self) -> str:
        import os
        return os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "workflow_extract_template.json")
        )

    def copy_to_comfyui_input(self, src_path: str, input_dir: str = None) -> str:
        """
        Copy src_path into ComfyUI's input directory.
        Returns the bare filename (what LoadAudio expects).
        """
        import shutil, os
        dest_dir = input_dir or self._default_input_dir()
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(src_path)
        dest = os.path.join(dest_dir, filename)
        shutil.copy2(src_path, dest)
        return filename

    def build_extract_workflow(
        self,
        input_filename: str,
        state: "SessionState",
        template_path: str = None,
    ) -> dict:
        """
        Load workflow_extract_template.json, patch the LoadAudio filename and
        KSampler steps/seed, return {"workflow": {...}} or {"error": "..."}.
        """
        import os, json as _json, random

        path = template_path or self._default_extract_template_path()
        if not os.path.exists(path):
            return {
                "error": (
                    "No extract workflow template found.\n\n"
                    "Build the ACE-Step extract workflow in ComfyUI, export as API format, "
                    f"and save to:\n  {path}"
                )
            }

        with open(path) as f:
            workflow = _json.load(f)

        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            ct = node.get("class_type", "")
            inputs = node.setdefault("inputs", {})
            if ct == "LoadAudio":
                inputs["filename"] = input_filename
            if ct == "KSampler":
                inputs["steps"] = state.steps
                MAX_SEED = 2**31 - 1
                if state.lock_seed:
                    inputs["seed"] = max(0, min(state.seed, MAX_SEED))
                else:
                    new_seed = random.randint(0, MAX_SEED)
                    state.seed = new_seed
                    inputs["seed"] = new_seed

        return {"workflow": workflow}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_comfyui_api.py::test_copy_to_comfyui_input_copies_file tests/test_comfyui_api.py::test_build_extract_workflow_patches_filename tests/test_comfyui_api.py::test_build_extract_workflow_returns_error_when_no_template -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Create `workflow_extract_template.json`**

This template implements ACE-Step extract mode. Create the file at the root of AceUser (alongside `workflow_template.json`):

```json
{
  "1": {
    "inputs": {
      "filename": "placeholder.mp3",
      "start_time": 0.0,
      "end_time": 0.0
    },
    "class_type": "LoadAudio",
    "_meta": { "title": "Load Audio (Input)" }
  },
  "2": {
    "inputs": {
      "vae": ["102", 0],
      "audio": ["1", 0]
    },
    "class_type": "VAEEncodeAudio",
    "_meta": { "title": "VAE Encode Audio" }
  },
  "3": {
    "inputs": {
      "tags": "",
      "lyrics": "",
      "seed": 31,
      "bpm": 120,
      "duration": 60.0,
      "timesignature": "4",
      "language": "en",
      "keyscale": "C major",
      "generate_audio_codes": true,
      "cfg_scale": 2,
      "temperature": 0.85,
      "top_p": 0.9,
      "top_k": 0,
      "min_p": 0,
      "clip": ["101", 0]
    },
    "class_type": "TextEncodeAceStepAudio1.5",
    "_meta": { "title": "Text Encode (Extract)" }
  },
  "4": {
    "inputs": {
      "seed": 31,
      "steps": 8,
      "cfg": 1,
      "sampler_name": "euler",
      "scheduler": "simple",
      "denoise": 1,
      "model": ["100", 0],
      "positive": ["3", 0],
      "negative": ["3", 0],
      "latent_image": ["2", 0]
    },
    "class_type": "KSampler",
    "_meta": { "title": "KSampler" }
  },
  "5": {
    "inputs": {
      "samples": ["4", 0],
      "vae": ["102", 0]
    },
    "class_type": "VAEDecodeAudio",
    "_meta": { "title": "VAE Decode Audio" }
  },
  "6": {
    "inputs": {
      "filename_prefix": "stems/stem",
      "quality": "V0",
      "audioUI": "",
      "audio": ["5", 0]
    },
    "class_type": "SaveAudioMP3",
    "_meta": { "title": "Save Stem (MP3)" }
  },
  "100": {
    "inputs": {
      "unet_name": "acestep_v1.5_xl_turbo_bf16.safetensors",
      "weight_dtype": "default"
    },
    "class_type": "UNETLoader",
    "_meta": { "title": "Load Diffusion Model" }
  },
  "101": {
    "inputs": {
      "clip_name1": "qwen_0.6b_ace15.safetensors",
      "clip_name2": "qwen_4b_ace15.safetensors",
      "type": "ace",
      "device": "default"
    },
    "class_type": "DualCLIPLoader",
    "_meta": { "title": "DualCLIPLoader" }
  },
  "102": {
    "inputs": {
      "vae_name": "ace_1.5_vae.safetensors"
    },
    "class_type": "VAELoader",
    "_meta": { "title": "Load VAE" }
  }
}
```

> **Important:** Open this workflow in ComfyUI to validate the node graph actually works for extract mode before shipping. If ACE-Step extract requires different nodes (e.g. a dedicated `ACEStepExtract` node), update the JSON — the Python code that patches it does not need to change.

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add acetalk/core/comfyui_api.py workflow_extract_template.json tests/test_comfyui_api.py
git commit -m "feat(comfyui): add copy_to_comfyui_input and build_extract_workflow; add extract template"
```

---

## Task 5: StemsTab UI

**Files:**
- Create: `acetalk/tabs/stems_tab.py`

No unit tests for pure Qt widget construction — tested via integration (Task 6). The tab is thin UI; logic lives in `DemucsWorker` and `ComfyUIClient` (already tested).

- [ ] **Step 1: Create `acetalk/tabs/stems_tab.py`**

```python
import os
import glob

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QGroupBox, QTextEdit,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from ..core.state import SessionState
from ..core.comfyui_api import ComfyUIClient
from ..core.demucs_worker import DemucsWorker


class StemsTab(QWidget):
    state_changed = pyqtSignal()

    def __init__(self, state: SessionState, config: dict, comfyui: ComfyUIClient, parent=None):
        super().__init__(parent)
        self.state = state
        self.config = config
        self.comfyui = comfyui
        self._demucs_worker = None
        self._generation_monitor = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(self._build_extract_group())
        root.addWidget(self._build_demucs_group())
        root.addStretch()

    def _build_extract_group(self) -> QGroupBox:
        group = QGroupBox("ACE-Step Native Extract")
        layout = QVBoxLayout(group)

        # File picker row
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Input audio:"))
        self.extract_path = QLineEdit()
        self.extract_path.setPlaceholderText("Select an MP3 or WAV file…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_extract_file)
        file_row.addWidget(self.extract_path)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Status / info
        self.extract_status = QTextEdit()
        self.extract_status.setReadOnly(True)
        self.extract_status.setFixedHeight(50)
        self.extract_status.setPlaceholderText(
            "Select a file, then click Send to run ACE-Step extraction via ComfyUI."
        )
        self.extract_status.setStyleSheet(
            "background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c;"
        )
        layout.addWidget(self.extract_status)

        # Send button
        send_btn = QPushButton("Send Extract Job to ComfyUI")
        send_btn.setStyleSheet("background:#1a3a2a; color:#80f0a0; font-weight:bold; padding:6px 16px;")
        send_btn.clicked.connect(self._on_send_extract)
        layout.addWidget(send_btn)

        return group

    def _build_demucs_group(self) -> QGroupBox:
        group = QGroupBox("Demucs Stem Separation")
        layout = QVBoxLayout(group)

        # Model picker + output path row
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["4-stem (htdemucs)", "6-stem (htdemucs_6s)"])
        # Set from state
        idx = 1 if self.state.stems_model == "htdemucs_6s" else 0
        self.model_combo.setCurrentIndex(idx)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        ctrl_row.addWidget(self.model_combo)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Output path display
        out_path = self._resolve_output_dir()
        self.output_path_label = QLabel(f"Output: {out_path}")
        self.output_path_label.setStyleSheet("color: #a0a0d0; font-size: 10px;")
        layout.addWidget(self.output_path_label)

        # Action row
        action_row = QHBoxLayout()
        separate_btn = QPushButton("Separate Last MP3")
        separate_btn.clicked.connect(self._on_separate_last)
        self.auto_check = QCheckBox("Auto-separate after generation")
        self.auto_check.setChecked(self.state.stems_auto_separate)
        self.auto_check.stateChanged.connect(self._on_auto_changed)
        action_row.addWidget(separate_btn)
        action_row.addWidget(self.auto_check)
        action_row.addStretch()
        layout.addLayout(action_row)

        # Log output
        self.demucs_log = QTextEdit()
        self.demucs_log.setReadOnly(True)
        self.demucs_log.setMinimumHeight(120)
        self.demucs_log.setStyleSheet(
            "background:#0d0d1a; color:#c0e0c0; font-family:monospace; font-size:11px; "
            "border:1px solid #3a3a5c;"
        )
        layout.addWidget(self.demucs_log)

        return group

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_output_dir(self) -> str:
        configured = self.config.get("stems_output_path", "").strip()
        if configured:
            return configured
        comfy_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        )
        return os.path.join(comfy_root, "output", "audio", "separated")

    def _find_last_mp3(self) -> str | None:
        comfy_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        )
        audio_dir = os.path.join(comfy_root, "output", "audio")
        pattern = os.path.join(audio_dir, "*.mp3")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        return files[0] if files else None

    # ------------------------------------------------------------------
    # Slots — ACE-Step extract
    # ------------------------------------------------------------------

    def _browse_extract_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.flac)"
        )
        if path:
            self.extract_path.setText(path)

    def _on_send_extract(self):
        from ..ui.main_window import _GenerationMonitor
        src = self.extract_path.text().strip()
        if not src or not os.path.exists(src):
            QMessageBox.warning(self, "No file", "Select a valid audio file first.")
            return

        self.extract_status.setPlainText("Copying file to ComfyUI input folder…")
        try:
            filename = self.comfyui.copy_to_comfyui_input(src)
        except Exception as exc:
            QMessageBox.warning(self, "Copy Error", str(exc))
            return

        result = self.comfyui.build_extract_workflow(filename, self.state)
        if "error" in result:
            QMessageBox.warning(self, "Extract Workflow Error", result["error"])
            return

        sent = self.comfyui.send_workflow(result["workflow"])
        if "error" in sent:
            QMessageBox.warning(self, "ComfyUI Error", sent["error"])
            return

        prompt_id = sent.get("prompt_id", "")
        self.extract_status.setPlainText(
            f"Queued — job ID: {prompt_id[:8] if prompt_id else '—'}\n"
            "Watching for completion…"
        )

        if prompt_id:
            monitor = _GenerationMonitor(self.comfyui.base_url, prompt_id, self)
            monitor.finished.connect(self._on_extract_done)
            monitor.failed.connect(self._on_extract_failed)
            monitor.start()
            self._generation_monitor = monitor

    def _on_extract_done(self, prompt_id: str, files: list):
        self.extract_status.setPlainText(
            "Extract complete.\nOutput: " + (", ".join(files) or "(check ComfyUI output/stems/)")
        )

    def _on_extract_failed(self, prompt_id: str, error: str):
        self.extract_status.setPlainText(f"Extract failed: {error}")

    # ------------------------------------------------------------------
    # Slots — Demucs
    # ------------------------------------------------------------------

    def _on_model_changed(self, idx: int):
        self.state.stems_model = "htdemucs_6s" if idx == 1 else "htdemucs"
        self.state_changed.emit()

    def _on_auto_changed(self):
        self.state.stems_auto_separate = self.auto_check.isChecked()
        self.state_changed.emit()

    def _on_separate_last(self):
        path = self._find_last_mp3()
        if not path:
            QMessageBox.warning(self, "No MP3", "No MP3 found in ComfyUI output/audio/.")
            return
        self.run_demucs(path)

    def run_demucs(self, input_path: str):
        """Public — called by MainWindow auto-separate hook."""
        if self._demucs_worker and self._demucs_worker.isRunning():
            return  # already running

        output_dir = self._resolve_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        self.demucs_log.clear()
        self.demucs_log.append(f"Running demucs on: {os.path.basename(input_path)}")
        self.demucs_log.append(f"Model: {self.state.stems_model}  Output: {output_dir}\n")

        self._demucs_worker = DemucsWorker(
            input_path=input_path,
            model=self.state.stems_model,
            output_dir=output_dir,
            parent=self,
        )
        self._demucs_worker.log_line.connect(self.demucs_log.append)
        self._demucs_worker.finished.connect(self._on_demucs_done)
        self._demucs_worker.failed.connect(self._on_demucs_failed)
        self._demucs_worker.start()

    def _on_demucs_done(self, stems: list):
        self.demucs_log.append("\nDone! Stems:")
        for s in stems:
            self.demucs_log.append(f"  {s}")
        if not stems:
            self.demucs_log.append("  (check output directory)")

    def _on_demucs_failed(self, error: str):
        self.demucs_log.append(f"\nError: {error}")
        QMessageBox.warning(self, "Demucs Error", error)
```

- [ ] **Step 2: Run existing tests to verify no import errors**

```bash
python -m pytest tests/ -v
```

Expected: all pass (StemsTab has no unit tests — integration verified in Task 6).

- [ ] **Step 3: Commit**

```bash
git add acetalk/tabs/stems_tab.py
git commit -m "feat(ui): add StemsTab with ACE-Step extract and Demucs sections"
```

---

## Task 6: Wire StemsTab into MainWindow + Auto-Separate Hook

**Files:**
- Modify: `acetalk/ui/main_window.py`

- [ ] **Step 1: Add Stems tab in `_add_tabs`**

In `acetalk/ui/main_window.py`, in the `_add_tabs` method, add after the `parameters_tab` block (before the closing of the method):

```python
        from ..tabs.stems_tab import StemsTab
        self.stems_tab = StemsTab(self.state, self.config, self.comfyui)
        self.stems_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.stems_tab, "Stems")
```

- [ ] **Step 2: Hook auto-separate into `_on_generation_done`**

Replace the existing `_on_generation_done` method:

```python
    def _on_generation_done(self, prompt_id: str, files: list, song_name: str):
        file_list = "\n".join(files) if files else "(check ComfyUI output folder)"
        self.output_panel.set_generation_status(f"Done: {song_name}")
        QMessageBox.information(
            self, f"Generation Complete — {song_name}",
            f"Nyx finished generating '{song_name}'.\n\nOutput file(s):\n{file_list}"
        )
        if hasattr(self, "_monitors"):
            self._monitors = [m for m in self._monitors if m.isRunning()]

        if self.state.stems_auto_separate and files:
            import os, glob as _glob
            comfy_root = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
            )
            audio_dir = os.path.join(comfy_root, "output", "audio")
            pattern = os.path.join(audio_dir, "*.mp3")
            mp3s = sorted(_glob.glob(pattern), key=os.path.getmtime, reverse=True)
            if mp3s:
                self.tabs.setCurrentWidget(self.stems_tab)
                self.stems_tab.run_demucs(mp3s[0])
```

- [ ] **Step 3: Update `_on_load_preset` to pass state ref to stems_tab**

In `_on_load_preset`, after `self.parameters_tab.state = self.state`, add:

```python
        self.stems_tab.state = self.state
```

- [ ] **Step 4: Launch AceTalk and verify the Stems tab appears**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
DISPLAY=:1 python3 acetalk.py &
```

Verify:
- "Stems" tab appears after "Parameters"
- ACE-Step Extract group: file picker and Browse button visible
- Demucs group: 4-stem/6-stem dropdown, "Separate Last MP3" button, auto-separate checkbox, log area visible
- Switching model updates `state.stems_model` (check via Overview tab or preset save)
- Toggling auto-separate checkbox persists in a saved preset

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add acetalk/ui/main_window.py
git commit -m "feat(main): wire StemsTab into MainWindow; auto-separate hook in _on_generation_done"
```

---

## Task 7: Validate Extract Workflow in ComfyUI

This task is manual — code is done, but the `workflow_extract_template.json` node graph needs validation before it can be trusted.

- [ ] **Step 1: Open the extract template in ComfyUI**

In a browser, go to `http://127.0.0.1:8188`. Use the Load button to load `workflow_extract_template.json` from the AceUser directory.

- [ ] **Step 2: Verify the graph loads without errors**

All nodes should appear connected. If any node is red or missing, the class_type is wrong for your ComfyUI install.

- [ ] **Step 3: Run a test extraction**

Place an MP3 in ComfyUI's `input/` folder. Set it as the LoadAudio source. Queue the workflow. Check if it produces output in `output/stems/`.

- [ ] **Step 4: Fix the template if needed**

If extraction fails or the graph is wrong, adjust `workflow_extract_template.json` to match what ACE-Step actually supports. Common fixes:
- ACE-Step extract may require a specific node (e.g. `ACEStepExtract`) instead of using `TextEncodeAceStepAudio1.5` with blank tags
- The `VAEEncodeAudio` node name may differ — check available nodes in ComfyUI's node browser

- [ ] **Step 5: Test via AceTalk**

Use the Stems tab → ACE-Step Extract → Browse to pick an MP3 → Send Extract Job to ComfyUI. Confirm the job queues and completes.

- [ ] **Step 6: Commit any template fixes**

```bash
git add workflow_extract_template.json
git commit -m "fix(extract): correct workflow_extract_template node graph after ComfyUI validation"
```

---

## Task 8: End-to-End Smoke Test

- [ ] **Step 1: Test demucs manually**

```bash
cd /home/legion/legionprojects/ComfyUI/AceUser
python3 -c "
from acetalk.core.demucs_worker import DemucsWorker
import glob, os
comfy_root = '/home/legion/legionprojects/ComfyUI'
mp3s = sorted(glob.glob(os.path.join(comfy_root, 'output/audio/*.mp3')), key=os.path.getmtime, reverse=True)
print('Most recent MP3:', mp3s[0] if mp3s else 'none found')
"
```

If an MP3 is found, run demucs on it:

```bash
python -m demucs --mp3 -n htdemucs -o /tmp/stems_test <path_to_mp3>
ls /tmp/stems_test/htdemucs/
```

Expected: subdirectory named after the track containing `vocals.mp3`, `drums.mp3`, `bass.mp3`, `other.mp3`.

- [ ] **Step 2: Test "Separate Last MP3" button in AceTalk**

Launch AceTalk, go to Stems tab, click "Separate Last MP3". Watch the log area fill with demucs output. Verify stems appear in the output directory shown in the label.

- [ ] **Step 3: Test auto-separate**

Check "Auto-separate after generation". Generate a short track (30s). After generation completes and the dialog is dismissed, verify:
- AceTalk switches to the Stems tab automatically
- Demucs log starts running
- Stems appear in the output directory

- [ ] **Step 4: Test preset round-trip**

Set stems_model to 6-stem, check auto-separate, save a preset. Load it. Verify both settings are restored.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: stem separation feature complete"
```
