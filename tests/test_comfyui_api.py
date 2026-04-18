from unittest.mock import patch, MagicMock
from acetalk.core.comfyui_api import ping, ComfyUIClient
try:
    from acetalk.core.comfyui_api import queue_workflow
except ImportError:
    queue_workflow = None
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


import os
import json
import shutil
import tempfile


def test_copy_to_comfyui_input_copies_file(tmp_path):
    src = tmp_path / "song.mp3"
    src.write_bytes(b"fake mp3 data")
    dest_dir = tmp_path / "input"
    dest_dir.mkdir()

    client = ComfyUIClient()
    result = client.copy_to_comfyui_input(str(src), input_dir=str(dest_dir))

    assert result == "song.mp3"
    assert (dest_dir / "song.mp3").exists()


def test_build_extract_workflow_patches_filename(tmp_path):
    # Write a minimal extract template
    template = {
        "1": {
            "class_type": "LoadAudio",
            "inputs": {"filename": "placeholder.mp3", "start_time": 0, "end_time": 0}
        },
        "2": {
            "class_type": "KSampler",
            "inputs": {"seed": 0, "steps": 8}
        },
    }
    template_path = tmp_path / "workflow_extract_template.json"
    template_path.write_text(json.dumps(template))

    client = ComfyUIClient()
    result = client.build_extract_workflow(
        input_filename="mysong.mp3",
        state=SessionState(steps=12, seed=42, lock_seed=True),
        template_path=str(template_path),
    )

    assert "workflow" in result
    wf = result["workflow"]
    assert wf["1"]["inputs"]["filename"] == "mysong.mp3"
    assert wf["2"]["inputs"]["steps"] == 12


def test_build_extract_workflow_returns_error_when_no_template(tmp_path):
    client = ComfyUIClient()
    result = client.build_extract_workflow(
        input_filename="song.mp3",
        state=SessionState(),
        template_path=str(tmp_path / "missing.json"),
    )
    assert "error" in result
