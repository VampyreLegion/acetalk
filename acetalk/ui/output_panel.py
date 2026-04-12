from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QLineEdit
)
from PyQt6.QtCore import pyqtSignal


class OutputPanel(QWidget):
    push_requested = pyqtSignal(str, str)   # (caption, lyrics)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(4)

        # Caption + Lyrics side by side
        fields = QHBoxLayout()

        cap_layout = QVBoxLayout()
        cap_layout.addWidget(QLabel("Caption:"))
        self.caption_box = QTextEdit()
        self.caption_box.setReadOnly(True)
        self.caption_box.setFixedHeight(60)
        cap_layout.addWidget(self.caption_box)
        fields.addLayout(cap_layout)

        lyr_layout = QVBoxLayout()
        lyr_layout.addWidget(QLabel("Lyrics:"))
        self.lyrics_box = QTextEdit()
        self.lyrics_box.setReadOnly(True)
        self.lyrics_box.setFixedHeight(60)
        lyr_layout.addWidget(self.lyrics_box)
        fields.addLayout(lyr_layout)

        root.addLayout(fields)

        # Action buttons
        btn_row = QHBoxLayout()

        self.btn_copy_cap = QPushButton("Copy Caption")
        self.btn_copy_lyr = QPushButton("Copy Lyrics")
        self.btn_copy_all = QPushButton("Copy All")
        self.btn_preview = QPushButton("Preview Raw Payload")
        self.btn_tag = QPushButton("Tag Last MP3")
        self.btn_fill = QPushButton("Fill ComfyUI Fields")
        self.btn_queue = QPushButton("Queue ComfyUI Workflow")
        self.preset_name = QLineEdit()
        self.preset_name.setPlaceholderText("Preset name...")
        self.preset_name.setFixedWidth(140)
        self.btn_save = QPushButton("Save Preset")
        self.btn_load = QPushButton("Load Preset")
        self.status_label = QLabel("ComfyUI: unknown")

        for w in [self.btn_copy_cap, self.btn_copy_lyr, self.btn_copy_all,
                  self.btn_preview, self.btn_fill, self.btn_queue, self.btn_tag,
                  self.preset_name, self.btn_save, self.btn_load,
                  self.status_label]:
            btn_row.addWidget(w)
        btn_row.addStretch()

        root.addLayout(btn_row)

        # Wire copy buttons
        self.btn_copy_cap.clicked.connect(
            lambda: self._copy(self.caption_box.toPlainText()))
        self.btn_copy_lyr.clicked.connect(
            lambda: self._copy(self.lyrics_box.toPlainText()))
        self.btn_copy_all.clicked.connect(self._copy_all)
        self.btn_fill.clicked.connect(
            lambda: self.push_requested.emit(
                self.caption_box.toPlainText(),
                self.lyrics_box.toPlainText()))
        self.btn_queue.clicked.connect(
            lambda: self.push_requested.emit(
                self.caption_box.toPlainText(),
                self.lyrics_box.toPlainText()))

    def update_output(self, caption: str, lyrics: str):
        self.caption_box.setPlainText(caption)
        self.lyrics_box.setPlainText(lyrics)

    def set_comfyui_status(self, online: bool):
        if online:
            self.status_label.setText("ComfyUI: Online \u2713")
            self.status_label.setStyleSheet("color: #4caf50;")
        else:
            self.status_label.setText("ComfyUI: Offline \u2717")
            self.status_label.setStyleSheet("color: #f44336;")

    def _copy(self, text: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _copy_all(self):
        cap = self.caption_box.toPlainText()
        lyr = self.lyrics_box.toPlainText()
        self._copy(f"--- Caption ---\n{cap}\n\n--- Lyrics ---\n{lyr}")
