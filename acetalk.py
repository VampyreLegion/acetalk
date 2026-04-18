import sys
import json
import os

from PyQt6.QtWidgets import QApplication
from acetalk.ui.main_window import MainWindow

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULT_CONFIG = {
    "comfyui_url": "http://127.0.0.1:8188",
    "brave_api_key": "",
    "stems_output_path": "",
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
