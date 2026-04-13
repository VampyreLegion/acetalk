import logging
import random

import requests

from .state import SessionState

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://127.0.0.1:8188"


def ping(base_url: str = DEFAULT_URL) -> bool:
    """Return True if ComfyUI is reachable."""
    try:
        requests.get(f"{base_url}/system_stats", timeout=3).raise_for_status()
        return True
    except Exception:
        return False


def queue_workflow(
    state: SessionState,
    caption: str,
    workflow_json: dict,
    base_url: str = DEFAULT_URL,
) -> dict:
    """
    POST a workflow JSON to ComfyUI's /prompt endpoint.
    Returns the response JSON (contains prompt_id).
    """
    resp = requests.post(
        f"{base_url}/prompt",
        json={"prompt": workflow_json},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


class ComfyUIClient:
    """Stateful client that holds the ComfyUI base URL from config."""

    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def ping(self) -> bool:
        return ping(self.base_url)

    def queue_workflow(self, state: SessionState, caption: str, workflow_json: dict) -> dict:
        return queue_workflow(state, caption, workflow_json, self.base_url)

    def build_encoder_inputs(self, caption: str, lyrics: str, state: SessionState) -> dict:
        """Return the exact inputs dict that would be sent to TextEncodeAceStepAudio1.5 — without sending."""
        inputs = {
            "tags": caption,
            "lyrics": lyrics,
            "bpm": state.bpm,
            "duration": float(state.duration),
            "cfg_scale": state.cfg_scale,
            "temperature": state.temperature,
            "top_p": state.top_p,
            "top_k": state.top_k,
            "min_p": state.min_p,
            "keyscale": f"{state.key} {state.scale.lower()}" if state.key and state.scale else "",
            "timesignature": state.time_sig.split("/")[0] if state.time_sig else "4",
            "language": "en",
            "generate_audio_codes": True,
        }
        return inputs

    def fill_fields(self, caption: str, lyrics: str, state: SessionState) -> dict:
        """
        Queue a workflow by loading the template at workflow_template.json,
        filling in tags/lyrics/params from state, and POSTing to /prompt.
        Returns status dict.
        """
        import os, json as _json

        template_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "workflow_template.json")
        )
        if not os.path.exists(template_path):
            return {
                "error": (
                    "No workflow template found.\n\n"
                    "To set one up:\n"
                    "1. Build your ACE-Step workflow in ComfyUI\n"
                    "2. Click Save (floppy icon) → Save (API format)\n"
                    "3. Save the file as:\n"
                    f"   {template_path}"
                )
            }

        with open(template_path) as f:
            workflow = _json.load(f)

        # Find TextEncodeAceStepAudio1.5 node and fill values
        filled = False
        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") == "TextEncodeAceStepAudio1.5":
                inputs = node.setdefault("inputs", {})
                inputs["tags"] = caption
                inputs["lyrics"] = lyrics
                inputs["bpm"] = state.bpm
                inputs["duration"] = float(state.duration)
                inputs["cfg_scale"] = state.cfg_scale
                inputs["temperature"] = state.temperature
                inputs["top_p"] = state.top_p
                inputs["top_k"] = state.top_k
                inputs["min_p"] = state.min_p
                if state.key and state.scale:
                    inputs["keyscale"] = f"{state.key} {state.scale.lower()}"
                if state.time_sig:
                    inputs["timesignature"] = state.time_sig.split("/")[0]
                filled = True

        # Also sync EmptyAceStep1.5LatentAudio seconds to match duration
        for node in workflow.values():
            if isinstance(node, dict) and node.get("class_type") == "EmptyAceStep1.5LatentAudio":
                node.setdefault("inputs", {})["seconds"] = float(state.duration)

        if not filled:
            return {"error": "Could not find a TextEncodeAceStepAudio1.5 node in workflow_template.json"}

        # Determine seed — use locked seed or generate fresh random
        if state.lock_seed and state.seed >= 0:
            new_seed = state.seed
        else:
            new_seed = random.randint(0, 2**32 - 1)
            state.seed = new_seed  # store so UI can display it

        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs", {})
            if "seed" in inputs and isinstance(inputs["seed"], (int, float)):
                inputs["seed"] = new_seed

        # Save filled workflow so it can be loaded in ComfyUI to inspect node values
        last_sent_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "last_sent.json")
        )
        try:
            with open(last_sent_path, "w") as f:
                _json.dump(workflow, f, indent=2)
        except Exception:
            pass

        try:
            resp = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow},
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as exc:
            return {"error": str(exc)}

        # Push filled workflow to ComfyUI frontend so nodes show text + progress highlights
        try:
            requests.post(
                f"{self.base_url}/acetalk/load",
                json=workflow,
                timeout=5,
            )
        except Exception:
            pass  # Non-fatal — bridge extension may not be installed

        return result
