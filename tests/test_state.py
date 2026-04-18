from acetalk.core.state import SessionState


def test_defaults():
    s = SessionState()
    assert s.genre == ""
    assert s.bpm == 120
    assert s.key == "C"
    assert s.scale == "Major"
    assert s.mode == ""
    assert s.time_sig == "4/4"
    assert s.instruments == []
    assert s.vocal_tags == []
    assert s.lyrics == ""
    assert s.cfg_scale == 2.0
    assert s.temperature == 0.85
    assert s.top_p == 0.9
    assert s.top_k == 0
    assert s.min_p == 0.0
    assert s.duration == 120
    assert s.steps == 8
    assert s.task_type == "text2music"
    assert s.stems_auto_separate is False
    assert s.stems_model == "htdemucs"


def test_round_trip():
    s = SessionState(genre="Psytrance", bpm=140, key="A", scale="Minor",
                     instruments=["TB-303 bass"], vocal_tags=["breathy"])
    d = s.to_dict()
    s2 = SessionState.from_dict(d)
    assert s2.genre == "Psytrance"
    assert s2.bpm == 140
    assert s2.instruments == ["TB-303 bass"]
    assert s2.vocal_tags == ["breathy"]


def test_from_dict_ignores_unknown_keys():
    d = {"genre": "EDM", "bpm": 128, "unknown_field": "ignored"}
    s = SessionState.from_dict(d)
    assert s.genre == "EDM"
    assert s.bpm == 128


def test_from_dict_does_not_alias_lists():
    d = {"instruments": ["TB-303 bass"]}
    s = SessionState.from_dict(d)
    d["instruments"].append("mutated")
    assert s.instruments == ["TB-303 bass"]


def test_stem_defaults():
    s = SessionState()
    assert s.stems_auto_separate is False
    assert s.stems_model == "htdemucs"


def test_stem_fields_round_trip():
    s = SessionState(stems_auto_separate=True, stems_model="htdemucs_6s")
    d = s.to_dict()
    s2 = SessionState.from_dict(d)
    assert s2.stems_auto_separate is True
    assert s2.stems_model == "htdemucs_6s"
