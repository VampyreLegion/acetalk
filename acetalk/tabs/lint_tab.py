from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QSplitter, QTabWidget, QTextBrowser,
)

from ..core.state import SessionState
from ..core.prompt_builder import build_prompt
from ..core.prompt_linter import LintResult, PromptLinter


class LintTab(QWidget):

    def __init__(self, state: SessionState, parent=None):
        super().__init__(parent)
        self.state = state
        self._linter = PromptLinter()
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([420, 420])

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 4, 0)

        self._input_tabs = QTabWidget()

        # ── Live State sub-tab ────────────────────────────────────────────────
        live_widget = QWidget()
        live_layout = QVBoxLayout(live_widget)
        live_layout.addWidget(QLabel("Current prompt (built from all tabs):"))
        self._live_display = QTextBrowser()
        live_layout.addWidget(self._live_display)
        lint_state_btn = QPushButton("Lint from State")
        lint_state_btn.clicked.connect(self._lint_from_state)
        live_layout.addWidget(lint_state_btn)
        self._input_tabs.addTab(live_widget, "Live State")

        # ── Paste sub-tab ─────────────────────────────────────────────────────
        paste_widget = QWidget()
        paste_layout = QVBoxLayout(paste_widget)
        paste_layout.addWidget(QLabel("Tags (comma-separated):"))
        self._paste_tags = QTextEdit()
        self._paste_tags.setMaximumHeight(72)
        self._paste_tags.setPlaceholderText("e.g. psytrance, 140 BPM, TB-303 bass, driving")
        paste_layout.addWidget(self._paste_tags)
        paste_layout.addWidget(QLabel("Lyrics:"))
        self._paste_lyrics = QTextEdit()
        self._paste_lyrics.setPlaceholderText("[Intro]\n...\n[Verse]\n...")
        paste_layout.addWidget(self._paste_lyrics)
        self._input_tabs.addTab(paste_widget, "Paste")

        self._input_tabs.currentChanged.connect(self._on_tab_switched)
        layout.addWidget(self._input_tabs)

        lint_btn = QPushButton("Lint Now")
        lint_btn.clicked.connect(self._lint_now)
        layout.addWidget(lint_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.addWidget(QLabel("Results:"))
        self._results = QTextBrowser()
        self._results.setHtml("<p><i>Click 'Lint Now' or 'Lint from State' to check your prompt.</i></p>")
        layout.addWidget(self._results)
        return panel

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_tab_switched(self, index: int):
        if index == 0:
            self._refresh_live_display()

    def _refresh_live_display(self):
        caption, lyrics = build_prompt(self.state)
        self._live_display.setPlainText(
            f"[Tags]\n{caption}\n\n[Lyrics]\n{lyrics}" if caption or lyrics
            else "(No prompt built yet — fill in the Easy/Style/Instrument/Lyrics tabs)"
        )

    def _lint_from_state(self):
        self._refresh_live_display()
        caption, lyrics = build_prompt(self.state)
        self._show_results(self._linter.lint(caption, lyrics))

    def _lint_now(self):
        if self._input_tabs.currentIndex() == 0:
            self._lint_from_state()
        else:
            tags = self._paste_tags.toPlainText()
            lyrics = self._paste_lyrics.toPlainText()
            self._show_results(self._linter.lint(tags, lyrics))

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _show_results(self, results: list[LintResult]):
        self._results.setHtml(self._render_results(results))

    @staticmethod
    def _render_results(results: list[LintResult]) -> str:
        if not results:
            return "<p><b>✅ All clear — no issues found.</b></p>"

        errors   = [r for r in results if r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]
        tips     = [r for r in results if r.severity == "tip"]

        style = (
            "<style>body{font-family:Arial,sans-serif;font-size:13px;}"
            "h3{margin:10px 0 4px;} p{margin:2px 0 8px;}</style>"
        )
        parts = [f"<html><head>{style}</head><body>"]

        def section(icon: str, label: str, items: list[LintResult]):
            if not items:
                return
            parts.append(f"<h3>{icon} {label}</h3>")
            for r in items:
                parts.append(
                    f"<p><b>[{r.field}]</b> {r.message}<br>"
                    f"<i style='color:#888'>→ {r.suggestion}</i></p>"
                )

        section("❌", "ERRORS (must fix)", errors)
        section("⚠", "WARNINGS (should fix)", warnings)
        section("💡", "TIPS (consider)", tips)

        parts.append("</body></html>")
        return "".join(parts)
