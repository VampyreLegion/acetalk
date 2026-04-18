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
        self.send_btn = QPushButton("Send Extract Job to ComfyUI")
        self.send_btn.setStyleSheet("background:#1a3a2a; color:#80f0a0; font-weight:bold; padding:6px 16px;")
        self.send_btn.clicked.connect(self._on_send_extract)
        layout.addWidget(self.send_btn)

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
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        return os.path.join(comfy_root, "output", "audio", "separated")

    def _find_last_mp3(self) -> str | None:
        comfy_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
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

        self.send_btn.setEnabled(False)
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
        self.send_btn.setEnabled(True)
        self.extract_status.setPlainText(
            "Extract complete.\nOutput: " + (", ".join(files) or "(check ComfyUI output/stems/)")
        )

    def _on_extract_failed(self, prompt_id: str, error: str):
        self.send_btn.setEnabled(True)
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

    def sync_from_state(self):
        """Refresh widgets from state — call after a preset load replaces self.state."""
        idx = 1 if self.state.stems_model == "htdemucs_6s" else 0
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentIndex(idx)
        self.model_combo.blockSignals(False)
        self.auto_check.blockSignals(True)
        self.auto_check.setChecked(self.state.stems_auto_separate)
        self.auto_check.blockSignals(False)

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
        self.output_path_label.setText(f"Output: {output_dir}")
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
        if self._demucs_worker:
            self._demucs_worker.deleteLater()
            self._demucs_worker = None

    def _on_demucs_failed(self, error: str):
        self.demucs_log.append(f"\nError: {error}")
        QMessageBox.warning(self, "Demucs Error", error)
        if self._demucs_worker:
            self._demucs_worker.deleteLater()
            self._demucs_worker = None
