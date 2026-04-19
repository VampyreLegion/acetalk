import json
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QSplitter, QToolBar, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from ..core.state import SessionState
from ..core.prompt_builder import build_prompt
from ..core.comfyui_api import ComfyUIClient
from .output_panel import OutputPanel

class _GenerationMonitor(QThread):
    """Watches ComfyUI WebSocket for a specific prompt_id completing."""
    finished = pyqtSignal(str, list)   # (prompt_id, list of output filenames)
    failed   = pyqtSignal(str, str)    # (prompt_id, error message)

    def __init__(self, base_url: str, prompt_id: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.prompt_id = prompt_id

    def run(self):
        import uuid, json as _json
        try:
            import websocket  # websocket-client
        except ImportError:
            self.failed.emit(self.prompt_id, "websocket-client not installed")
            return

        client_id = str(uuid.uuid4())
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws?clientId={client_id}"

        outputs = []
        try:
            ws = websocket.create_connection(ws_url, timeout=300)
            while True:
                raw = ws.recv()
                try:
                    msg = _json.loads(raw)
                except Exception:
                    continue
                mtype = msg.get("type", "")
                data  = msg.get("data", {})

                if mtype == "executed" and data.get("prompt_id") == self.prompt_id:
                    # Collect any audio/video output filenames
                    node_output = data.get("output", {})
                    for key in ("audio", "images", "video"):
                        items = node_output.get(key, [])
                        for item in items:
                            fname = item.get("filename", "")
                            if fname:
                                outputs.append(fname)
                    ws.close()
                    self.finished.emit(self.prompt_id, outputs)
                    return

                if mtype == "execution_error" and data.get("prompt_id") == self.prompt_id:
                    ws.close()
                    self.failed.emit(self.prompt_id, data.get("exception_message", "Unknown error"))
                    return
        except Exception as exc:
            self.failed.emit(self.prompt_id, str(exc))


CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
)
PRESETS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "presets")
)


class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.state = SessionState()
        self.comfyui = ComfyUIClient(config.get("comfyui_url", "http://127.0.0.1:8188"))

        self.setWindowTitle("Master composers Legion and Nyx working on music composition.")
        self.setMinimumSize(1100, 800)

        self._build_ui()
        self._add_toolbar()
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
        self._add_tabs()
        splitter.addWidget(self.tabs)

        # Output panel (bottom — always visible)
        self.output_panel = OutputPanel()
        self.output_panel.setFixedHeight(160)
        splitter.addWidget(self.output_panel)
        splitter.setCollapsible(1, False)

        root.addWidget(splitter)

        self.output_panel.push_requested.connect(self._on_push_requested)
        self.output_panel.btn_preview.clicked.connect(self._on_preview_payload)
        self.output_panel.btn_tag.clicked.connect(self._on_tag_mp3)
        self.output_panel.btn_save.clicked.connect(
            lambda: self._on_save_preset(self.output_panel.preset_name.text()))
        self.output_panel.btn_load.clicked.connect(self._on_load_preset)

    def _add_tabs(self):
        from ..tabs.overview_tab import OverviewTab
        from ..tabs.easy_tab import EasyTab
        from ..tabs.style_tab import StyleTab
        from ..tabs.instrument_tab import InstrumentTab
        from ..tabs.vocalist_tab import VocalistTab
        from ..tabs.lyrics_tab import LyricsTab
        from ..tabs.parameters_tab import ParametersTab

        self.overview_tab = OverviewTab(self.state)
        self.tabs.addTab(self.overview_tab, "Overview")

        self.easy_tab = EasyTab(self.state, self.config)
        self.easy_tab.state_changed.connect(self.refresh_output)
        self.easy_tab.go_to_overview.connect(self._on_easy_tab_applied)
        self.tabs.addTab(self.easy_tab, "Easy")

        self.style_tab = StyleTab(self.state)
        self.style_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.style_tab, "Style")

        self.instrument_tab = InstrumentTab(self.state)
        self.instrument_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.instrument_tab, "Instruments")

        self.vocalist_tab = VocalistTab(self.state)
        self.vocalist_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.vocalist_tab, "Vocals")

        self.lyrics_tab = LyricsTab(self.state, config=self.config)
        self.lyrics_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.lyrics_tab, "Lyrics")

        self.parameters_tab = ParametersTab(self.state)
        self.parameters_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.parameters_tab, "Parameters")

        from ..tabs.stems_tab import StemsTab
        self.stems_tab = StemsTab(self.state, self.config, self.comfyui)
        self.stems_tab.state_changed.connect(self.refresh_output)
        self.tabs.addTab(self.stems_tab, "Stems")

        from ..tabs.guide_tab import GuideTab
        self.guide_tab = GuideTab()
        self.tabs.addTab(self.guide_tab, "Guide")

        from ..tabs.lint_tab import LintTab
        self.lint_tab = LintTab(self.state)
        self.tabs.addTab(self.lint_tab, "Lint")

    def _add_toolbar(self):
        tb = QToolBar("Main")
        self.addToolBar(tb)
        settings_action = QAction("\u2699 Settings", self)
        settings_action.triggered.connect(self._open_settings)
        tb.addAction(settings_action)

    def _on_easy_tab_applied(self):
        """Called when Easy tab sends its generated result to session.
        Refreshes all editing tabs so they reflect the new state, then switches to Overview."""
        self.style_tab.load_from_state()
        self.instrument_tab.load_from_state()
        self.vocalist_tab.load_from_state()
        self.lyrics_tab.load_from_state()
        self.parameters_tab.load_from_state()
        self.overview_tab.refresh()
        self.refresh_output()
        self.tabs.setCurrentWidget(self.overview_tab)

    def refresh_output(self):
        caption, lyrics = build_prompt(self.state)
        self.output_panel.update_output(caption, lyrics)
        self.overview_tab.refresh()

    def _start_ping_timer(self):
        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self._ping_comfyui)
        self.ping_timer.start(30_000)
        self._ping_comfyui()

    def _ping_comfyui(self):
        online = self.comfyui.ping()
        self.output_panel.set_comfyui_status(online)

    def _on_preview_payload(self):
        import json as _json
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
        caption, lyrics = build_prompt(self.state)
        inputs = self.comfyui.build_encoder_inputs(caption, lyrics, self.state)

        dlg = QDialog(self)
        dlg.setWindowTitle("Raw Payload — TextEncodeAceStepAudio1.5")
        dlg.setMinimumSize(700, 580)
        layout = QVBoxLayout(dlg)

        lbl = QLabel("Exact inputs sent to the ACE-Step 1.5 Text Encoder node:")
        lbl.setStyleSheet("color: #a0a0d0; font-size: 10px;")
        layout.addWidget(lbl)

        # Show tags and lyrics separately for readability
        tags_lbl = QLabel("TAGS  (caption →  tags field):")
        tags_lbl.setStyleSheet("color: #80c080; font-size: 10px; font-weight: bold;")
        layout.addWidget(tags_lbl)
        tags_box = QTextEdit()
        tags_box.setReadOnly(True)
        tags_box.setPlainText(inputs["tags"])
        tags_box.setFixedHeight(70)
        tags_box.setStyleSheet("background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c;")
        layout.addWidget(tags_box)

        lyrics_lbl = QLabel("LYRICS  (lyrics field):")
        lyrics_lbl.setStyleSheet("color: #80c0ff; font-size: 10px; font-weight: bold;")
        layout.addWidget(lyrics_lbl)
        lyrics_box = QTextEdit()
        lyrics_box.setReadOnly(True)
        lyrics_box.setPlainText(inputs["lyrics"])
        lyrics_box.setMinimumHeight(180)
        lyrics_box.setStyleSheet("background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c;")
        layout.addWidget(lyrics_box)

        params_lbl = QLabel("PARAMETERS:")
        params_lbl.setStyleSheet("color: #c0a0ff; font-size: 10px; font-weight: bold;")
        layout.addWidget(params_lbl)
        params = {k: v for k, v in inputs.items() if k not in ("tags", "lyrics")}
        params_box = QTextEdit()
        params_box.setReadOnly(True)
        params_box.setPlainText(_json.dumps(params, indent=2))
        params_box.setFixedHeight(140)
        params_box.setStyleSheet("background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c; font-family: monospace;")
        layout.addWidget(params_box)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def _on_tag_mp3(self):
        import glob as _glob
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, COMM, ID3NoHeaderError
        from mutagen.id3 import Encoding

        # Find most recent MP3 in ComfyUI output folder
        output_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "output", "audio")
        )
        pattern = os.path.join(output_dir, "*.mp3")
        files = sorted(_glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if not files:
            QMessageBox.warning(self, "Tag MP3", f"No MP3 files found in:\n{output_dir}")
            return

        path = files[0]
        s = self.state
        try:
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            if s.song_title:
                tags["TIT2"] = TIT2(encoding=Encoding.UTF8, text=s.song_title)
            if s.artist:
                tags["TPE1"] = TPE1(encoding=Encoding.UTF8, text=s.artist)
            if s.album:
                tags["TALB"] = TALB(encoding=Encoding.UTF8, text=s.album)
            if s.year:
                tags["TDRC"] = TDRC(encoding=Encoding.UTF8, text=s.year)
            if s.genre_tags:
                tags["TCON"] = TCON(encoding=Encoding.UTF8, text=s.genre_tags)
            comment = s.description or f"Generated by AceTalk — {s.genre} {s.bpm} BPM {s.key} {s.scale}"
            tags["COMM"] = COMM(encoding=Encoding.UTF8, lang="eng", desc="", text=comment)
            tags.save(path)
            QMessageBox.information(
                self, "Tagged",
                f"ID3 tags written to:\n{os.path.basename(path)}\n\n"
                f"Title:   {s.song_title or '—'}\n"
                f"Artist:  {s.artist or '—'}\n"
                f"Album:   {s.album or '—'}\n"
                f"Year:    {s.year or '—'}\n"
                f"Genre:   {s.genre_tags or '—'}"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Tag MP3 Error", str(exc))

    def _on_push_requested(self, caption: str, lyrics: str):
        song_name = self.output_panel.preset_name.text().strip() or self.state.genre or "Untitled"

        # Build workflow first — no network calls yet
        build_result = self.comfyui.build_workflow(caption, lyrics, self.state)
        if "error" in build_result:
            QMessageBox.warning(self, "ComfyUI Error", build_result["error"])
            return

        workflow = build_result["workflow"]

        # Update seed display before showing dialog
        self.parameters_tab.update_seed(self.state.seed)

        # Show preview — user can cancel here before anything is sent
        confirmed = self._show_payload_preview(caption, lyrics, song_name)
        if not confirmed:
            return

        # User confirmed — now actually send
        result = self.comfyui.send_workflow(workflow)
        if "error" in result:
            QMessageBox.warning(self, "ComfyUI Error", result["error"])
            return

        prompt_id = result.get("prompt_id", "")
        short_id  = prompt_id[:8] if prompt_id else "—"
        self.output_panel.set_generation_status(f"Queued: {song_name}")

        QMessageBox.information(
            self, "Sent to Nyx",
            f"'{song_name}' queued successfully.\n\nJob ID: {short_id}"
        )

        if prompt_id:
            self._start_generation_monitor(prompt_id, song_name)

    def _show_payload_preview(self, caption: str, lyrics: str, song_name: str) -> bool:
        """Show a review dialog before sending. Returns True if user confirms, False if cancelled."""
        import json as _json
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
        inputs = self.comfyui.build_encoder_inputs(caption, lyrics, self.state)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Review before sending — {song_name}")
        dlg.setMinimumSize(700, 560)
        layout = QVBoxLayout(dlg)

        lock_str = f"  |  Seed: {self.state.seed} {'(locked)' if self.state.lock_seed else '(random)'}"
        header = QLabel(f"Review what will be sent to Nyx.{lock_str}")
        header.setStyleSheet("color: #a0a0d0; font-size: 11px; padding: 4px 0;")
        layout.addWidget(header)

        tags_lbl = QLabel("TAGS  (instruments + style):")
        tags_lbl.setStyleSheet("color: #80c080; font-size: 10px; font-weight: bold;")
        layout.addWidget(tags_lbl)
        tags_box = QTextEdit()
        tags_box.setReadOnly(True)
        tags_box.setPlainText(inputs["tags"])
        tags_box.setFixedHeight(80)
        tags_box.setStyleSheet("background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c;")
        layout.addWidget(tags_box)

        lyrics_lbl = QLabel("LYRICS:")
        lyrics_lbl.setStyleSheet("color: #80c0ff; font-size: 10px; font-weight: bold;")
        layout.addWidget(lyrics_lbl)
        lyrics_box = QTextEdit()
        lyrics_box.setReadOnly(True)
        lyrics_box.setPlainText(inputs["lyrics"])
        lyrics_box.setMinimumHeight(180)
        lyrics_box.setStyleSheet("background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c;")
        layout.addWidget(lyrics_box)

        params_lbl = QLabel("PARAMETERS:")
        params_lbl.setStyleSheet("color: #c0a0ff; font-size: 10px; font-weight: bold;")
        layout.addWidget(params_lbl)
        params = {k: v for k, v in inputs.items() if k not in ("tags", "lyrics")}
        params_box = QTextEdit()
        params_box.setReadOnly(True)
        params_box.setPlainText(_json.dumps(params, indent=2))
        params_box.setFixedHeight(110)
        params_box.setStyleSheet("background:#1a1a2a; color:#e0e0f0; font-size:11px; border:1px solid #3a3a5c; font-family: monospace;")
        layout.addWidget(params_box)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background:#3a2a2a; color:#f08080; padding: 6px 20px;")
        cancel_btn.clicked.connect(dlg.reject)
        send_btn = QPushButton("Send to Nyx")
        send_btn.setDefault(True)
        send_btn.setStyleSheet("background:#1a3a2a; color:#80f0a0; font-weight:bold; padding: 6px 20px;")
        send_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(send_btn)
        layout.addLayout(btn_row)

        return dlg.exec() == QDialog.DialogCode.Accepted

    def _start_generation_monitor(self, prompt_id: str, song_name: str):
        monitor = _GenerationMonitor(self.comfyui.base_url, prompt_id, self)
        monitor.finished.connect(lambda pid, files: self._on_generation_done(pid, files, song_name))
        monitor.failed.connect(lambda pid, err: self._on_generation_failed(pid, err, song_name))
        monitor.start()
        # Keep reference so it isn't garbage-collected
        if not hasattr(self, "_monitors"):
            self._monitors = []
        self._monitors.append(monitor)

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
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
            audio_dir = os.path.join(comfy_root, "output", "audio")
            pattern = os.path.join(audio_dir, "*.mp3")
            mp3s = sorted(_glob.glob(pattern), key=os.path.getmtime, reverse=True)
            if mp3s:
                self.tabs.setCurrentWidget(self.stems_tab)
                self.stems_tab.run_demucs(mp3s[0])

    def _on_generation_failed(self, prompt_id: str, error: str, song_name: str):
        self.output_panel.set_generation_status(f"Error: {song_name}")
        QMessageBox.warning(self, f"Generation Error — {song_name}", error)
        if hasattr(self, "_monitors"):
            self._monitors = [m for m in self._monitors if m.isRunning()]

    def _on_save_preset(self, name: str):
        if not name.strip():
            return
        os.makedirs(PRESETS_DIR, exist_ok=True)
        path = os.path.join(PRESETS_DIR, f"{name.strip()}.json")
        with open(path, "w") as f:
            json.dump(self.state.to_dict(), f, indent=2)

    def _on_load_preset(self):
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
        self.overview_tab.state = self.state
        self.style_tab.state = self.state
        self.instrument_tab.state = self.state
        self.instrument_tab.load_from_state()
        self.vocalist_tab.state = self.state
        self.lyrics_tab.state = self.state
        self.lyrics_tab.editor.setPlainText(self.state.lyrics)
        self.parameters_tab.state = self.state
        self.stems_tab.state = self.state
        self.stems_tab.sync_from_state()
        self.refresh_output()

    def _open_settings(self):
        from .settings_dialog import SettingsDialog
        import os
        dlg = SettingsDialog(self.config, CONFIG_PATH, self)
        if dlg.exec():
            self.comfyui = ComfyUIClient(self.config.get("comfyui_url", "http://127.0.0.1:8188"))
            os.environ["BRAVE_API_KEY"] = self.config.get("brave_api_key", "")
            self._ping_comfyui()
