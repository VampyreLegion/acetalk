from __future__ import annotations
import re
import pathlib

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextBrowser, QLabel


_GUIDE_HTML_PATH = pathlib.Path(__file__).parent.parent.parent / "Aceuser.html"

_CHAPTER_TABS = [
    ("summary", "Summary"),
    ("ch1", "1. Philosophy"),
    ("ch2", "2. Tags"),
    ("ch3", "3. Lyrics"),
    ("ch4", "4. DAW"),
    ("ch5", "5. Hidden Syntax"),
    ("ch6", "6. Operations"),
    ("ch7", "7. Examples"),
    ("ch8", "8. Troubleshooting"),
]

_QT_STYLE = """
<style>
body { font-family: Arial, sans-serif; font-size: 13px; color: #e2e4ed;
       background: #0b0c10; padding: 12px; }
h2 { color: #7c65d9; border-left: 4px solid #7c65d9; padding-left: 8px; }
h3 { color: #00d4b6; }
p, li { color: #e2e4ed; margin-bottom: 6px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th { background: #1a1c26; color: #00d4b6; padding: 6px; border: 1px solid #2d3041; }
td { padding: 6px; border: 1px solid #2d3041; color: #e2e4ed; }
code { background: #151720; color: #a6e3a1; padding: 2px 4px;
       border-radius: 3px; font-family: monospace; }
pre { background: #151720; color: #cdd6f4; padding: 10px;
      border-radius: 6px; border: 1px solid #2d3041; }
</style>
"""


def _parse_chapters(html_path: pathlib.Path) -> dict[str, str]:
    raw = html_path.read_text(encoding="utf-8")
    chunks = re.split(r'(?=<h2\s)', raw)
    chapters: dict[str, str] = {}
    for chunk in chunks:
        id_match = re.search(r'<h2[^>]*id="([^"]+)"', chunk)
        if id_match:
            section_id = id_match.group(1)
            chapters[section_id] = (
                f"<html><head>{_QT_STYLE}</head><body>{chunk}</body></html>"
            )
    return chapters


class GuideTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        if not _GUIDE_HTML_PATH.exists():
            label = QLabel(f"Guide file not found: {_GUIDE_HTML_PATH}")
            root.addWidget(label)
            return

        chapters = _parse_chapters(_GUIDE_HTML_PATH)
        inner_tabs = QTabWidget()

        for section_id, tab_label in _CHAPTER_TABS:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(False)
            html = chapters.get(section_id, "<p>Section not found.</p>")
            browser.setHtml(html)
            inner_tabs.addTab(browser, tab_label)

        root.addWidget(inner_tabs)
