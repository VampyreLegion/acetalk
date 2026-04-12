from acetalk.core.state import SessionState
from acetalk.core.prompt_builder import build_caption, build_lyrics, build_prompt


def test_caption_empty_state():
    s = SessionState()
    caption = build_caption(s)
    assert caption == ""


def test_caption_genre_and_bpm():
    s = SessionState(genre="Psytrance", bpm=140)
    caption = build_caption(s)
    assert "psytrance" in caption
    assert "140 BPM" in caption


def test_caption_key_and_scale():
    s = SessionState(key="A", scale="Minor")
    caption = build_caption(s)
    assert "A Minor" in caption


def test_caption_mode():
    s = SessionState(key="A", scale="Minor", mode="Phrygian")
    caption = build_caption(s)
    assert "Phrygian mode" in caption


def test_caption_instruments_and_vocals():
    s = SessionState(
        instruments=["warm TB-303 synth bass", "punchy electronic drums"],
        vocal_tags=["breathy female vocal", "whispery"]
    )
    caption = build_caption(s)
    assert "warm TB-303 synth bass" in caption
    assert "breathy female vocal" in caption


def test_caption_full():
    s = SessionState(
        genre="Psytrance", bpm=140, key="A", scale="Minor", mode="Phrygian",
        time_sig="4/4", instruments=["TB-303 bass"], vocal_tags=["breathy"]
    )
    caption = build_caption(s)
    parts = [p.strip() for p in caption.split(",")]
    assert "psytrance" in parts
    assert "140 BPM" in parts
    assert "A Minor" in parts
    assert "Phrygian mode" in parts
    assert "4/4 time" in parts
    assert "TB-303 bass" in parts
    assert "breathy" in parts


def test_build_lyrics():
    s = SessionState(lyrics="[Intro]\nHello world")
    assert build_lyrics(s) == "[Intro]\nHello world"


def test_build_prompt_returns_tuple():
    s = SessionState(genre="EDM", bpm=128, lyrics="[Chorus]\nDrop")
    caption, lyrics = build_prompt(s)
    assert "edm" in caption
    assert lyrics == "[Chorus]\nDrop"
