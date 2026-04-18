import os as _os
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
        if not stem_dir.exists():
            self.log_line.emit(f"[warn] stem directory not found: {stem_dir}")
            return []
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
                bufsize=1,
                env={**_os.environ, "PYTHONUNBUFFERED": "1"},
            )
            for line in iter(proc.stdout.readline, ""):
                stripped = line.rstrip()
                if stripped:
                    self.log_line.emit(stripped)
            proc.stdout.close()
            proc.wait()
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        if proc.returncode != 0:
            self.failed.emit(f"demucs exited with code {proc.returncode}")
            return

        stems = self._collect_stems()
        self.finished.emit(stems)
