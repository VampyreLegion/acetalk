import json
import os
from unittest.mock import patch
from acetalk.core.search import search_artist, _parse_artist_result


def test_parse_artist_result_returns_dict():
    text = "Billie Eilish is known for breathy, whispery vocal style. She typically sings in C minor."
    result = _parse_artist_result("Billie Eilish", text)
    assert result["name"] == "Billie Eilish"
    assert isinstance(result["ace_step_descriptors"], list)


def test_search_artist_hits_local_db_first(tmp_path):
    vocals_path = tmp_path / "vocals.json"
    vocals_path.write_text(json.dumps({
        "artists": [{
            "name": "Test Artist",
            "range": "Alto",
            "preferred_key": "Am",
            "style": "Pop",
            "known_for": ["Song A"],
            "ace_step_descriptors": ["breathy", "soft"]
        }]
    }))
    with patch("acetalk.core.search.VOCALS_PATH", str(vocals_path)):
        result = search_artist("Test Artist", source="local")
    assert result is not None
    assert result["name"] == "Test Artist"
    assert "breathy" in result["ace_step_descriptors"]


def test_search_artist_returns_none_for_unknown_local(tmp_path):
    vocals_path = tmp_path / "vocals.json"
    vocals_path.write_text(json.dumps({"artists": []}))
    with patch("acetalk.core.search.VOCALS_PATH", str(vocals_path)):
        result = search_artist("Unknown Nobody", source="local")
    assert result is None


def test_search_artist_caches_web_result(tmp_path):
    vocals_path = tmp_path / "vocals.json"
    vocals_path.write_text(json.dumps({"artists": []}))
    mock_result = {
        "name": "New Artist",
        "range": "Tenor",
        "preferred_key": "G Major",
        "style": "Rock",
        "known_for": [],
        "ace_step_descriptors": ["powerful", "raw"]
    }
    with patch("acetalk.core.search.VOCALS_PATH", str(vocals_path)), \
         patch("acetalk.core.search._web_search_artist", return_value=mock_result):
        result = search_artist("New Artist", source="web")
    assert result["name"] == "New Artist"
    saved = json.loads(vocals_path.read_text())
    assert any(a["name"] == "New Artist" for a in saved["artists"])
