from unittest.mock import patch, MagicMock
from acetalk.core.comfyui_api import ping, queue_workflow, ComfyUIClient
from acetalk.core.state import SessionState


def test_ping_returns_true_when_online():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("acetalk.core.comfyui_api.requests.get", return_value=mock_resp):
        assert ping() is True


def test_ping_returns_false_when_offline():
    with patch("acetalk.core.comfyui_api.requests.get", side_effect=Exception("refused")):
        assert ping() is False


def test_queue_workflow_posts_to_prompt_endpoint():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"prompt_id": "abc123"}
    mock_resp.raise_for_status = MagicMock()
    state = SessionState(genre="Psytrance", bpm=140, lyrics="[Verse]\nTest")
    with patch("acetalk.core.comfyui_api.requests.post", return_value=mock_resp) as mock_post:
        result = queue_workflow(state, caption="psytrance, 140 BPM", workflow_json={"nodes": []})
    assert result == {"prompt_id": "abc123"}
    call_args = mock_post.call_args
    assert "/prompt" in call_args[0][0]


def test_client_uses_configured_url():
    client = ComfyUIClient(base_url="http://myserver:8188")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("acetalk.core.comfyui_api.requests.get", return_value=mock_resp) as mock_get:
        client.ping()
    assert "myserver:8188" in mock_get.call_args[0][0]
