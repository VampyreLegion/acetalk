import json

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
