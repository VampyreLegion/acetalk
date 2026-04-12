import sys
import pytest
from PyQt6.QtWidgets import QApplication
from acetalk.core.state import SessionState


@pytest.fixture(scope="session")
def qt_app():
    """Single QApplication for the test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_state():
    return SessionState(
        genre="Psytrance",
        bpm=140,
        key="A",
        scale="Minor",
        mode="Phrygian",
        time_sig="4/4",
        instruments=["warm TB-303 synth bass", "punchy electronic drums"],
        vocal_tags=["breathy female vocal"],
        lyrics="[Intro: Atmospheric]\nTest lyrics",
        cfg_scale=7.0,
        temperature=1.0,
    )
