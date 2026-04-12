from unittest.mock import patch, MagicMock
from acetalk.core.llm import list_models, generate_lyrics


def test_list_models_returns_list():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"models": [{"name": "llama3"}, {"name": "mistral"}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("acetalk.core.llm.requests.get", return_value=mock_resp):
        models = list_models()
    assert "llama3" in models
    assert "mistral" in models


def test_list_models_returns_fallback_on_error():
    with patch("acetalk.core.llm.requests.get", side_effect=Exception("connection refused")):
        models = list_models()
    assert models == ["(Ollama offline)"]


def test_generate_lyrics_calls_ollama():
    chunks = [
        b'{"response":"[Intro]\\n"}',
        b'{"response":"Stars align\\n"}',
        b'{"done":true,"response":""}',
    ]
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(chunks)
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    collected = []
    with patch("acetalk.core.llm.requests.post", return_value=mock_resp):
        generate_lyrics(
            prompt="write a psytrance song",
            genre="Psytrance", key="Am", mood="dark",
            structure="Verse-Chorus",
            model="llama3",
            on_token=collected.append,
        )
    assert "[Intro]" in "".join(collected)
    assert "Stars align" in "".join(collected)
