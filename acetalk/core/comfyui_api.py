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


class ComfyUIClient:
    """Stateful client that holds the ComfyUI base URL from config."""

    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def ping(self) -> bool:
        return ping(self.base_url)

    def build_encoder_inputs(self, caption: str, lyrics: str, state: SessionState) -> dict:
        """Return the exact inputs dict for TextEncodeAceStepAudio1.5 — without sending."""
        return {
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

    def build_workflow(self, caption: str, lyrics: str, state: SessionState) -> dict:
        """
        Load the workflow template, fill all node inputs from state, and assign
        a seed — but do NOT send anything. Returns {"workflow": {...}} on success
        or {"error": "..."} on failure.
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

        # Fill TextEncodeAceStepAudio1.5 node
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

        if not filled:
            return {"error": "Could not find a TextEncodeAceStepAudio1.5 node in workflow_template.json"}

        # Sync EmptyAceStep1.5LatentAudio seconds to match duration
        for node in workflow.values():
            if isinstance(node, dict) and node.get("class_type") == "EmptyAceStep1.5LatentAudio":
                node.setdefault("inputs", {})["seconds"] = float(state.duration)

        # Sync KSampler steps from state
        for node in workflow.values():
            if isinstance(node, dict) and node.get("class_type") == "KSampler":
                node.setdefault("inputs", {})["steps"] = state.steps

        # Determine seed — use locked seed or generate fresh random
        # Keep within int32 range (ComfyUI nodes use int32 internally)
        MAX_SEED = 2**31 - 1
        if state.lock_seed:
            new_seed = max(0, min(state.seed, MAX_SEED))
        else:
            new_seed = random.randint(0, MAX_SEED)
            state.seed = new_seed  # store so UI can display it

        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs", {})
            if "seed" in inputs and isinstance(inputs["seed"], (int, float)):
                inputs["seed"] = new_seed

        return {"workflow": workflow}

    def send_workflow(self, workflow: dict) -> dict:
        """
        POST a pre-built workflow to ComfyUI's /prompt endpoint and push it to
        the browser frontend via AceTalkBridge. Returns the /prompt response
        (contains prompt_id) or {"error": "..."}.
        """
        import os, json as _json

        # Save for manual inspection
        last_sent_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "last_sent.json")
        )
        try:
            with open(last_sent_path, "w") as f:
                _json.dump(workflow, f, indent=2)
        except Exception:
            pass

        # Queue the job
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

        # Push to ComfyUI frontend (AceTalkBridge) — non-fatal if not installed
        try:
            requests.post(
                f"{self.base_url}/acetalk/load",
                json=workflow,
                timeout=5,
            )
        except Exception:
            pass

        return result

    def _default_input_dir(self) -> str:
        """Resolve ComfyUI's input/ folder relative to this file's location."""
        import os
        comfy_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        return os.path.join(comfy_root, "input")

    def _default_extract_template_path(self) -> str:
        import os
        return os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "workflow_extract_template.json")
        )

    def copy_to_comfyui_input(self, src_path: str, input_dir: str = None) -> str:
        """
        Copy src_path into ComfyUI's input directory.
        Returns the bare filename (what LoadAudio expects).
        """
        import shutil, os
        dest_dir = input_dir or self._default_input_dir()
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(src_path)
        dest = os.path.join(dest_dir, filename)
        shutil.copy2(src_path, dest)
        return filename

    def build_extract_workflow(
        self,
        input_filename: str,
        state: "SessionState",
        template_path: str = None,
    ) -> dict:
        """
        Load workflow_extract_template.json, patch the LoadAudio filename and
        KSampler steps/seed, return {"workflow": {...}} or {"error": "..."}.
        """
        import os, json as _json, random

        path = template_path or self._default_extract_template_path()
        if not os.path.exists(path):
            return {
                "error": (
                    "No extract workflow template found.\n\n"
                    "Build the ACE-Step extract workflow in ComfyUI, export as API format, "
                    f"and save to:\n  {path}"
                )
            }

        with open(path) as f:
            workflow = _json.load(f)

        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            ct = node.get("class_type", "")
            inputs = node.setdefault("inputs", {})
            if ct == "LoadAudio":
                inputs["filename"] = input_filename
            if ct == "KSampler":
                inputs["steps"] = state.steps
                MAX_SEED = 2**31 - 1
                if state.lock_seed:
                    inputs["seed"] = max(0, min(state.seed, MAX_SEED))
                else:
                    new_seed = random.randint(0, MAX_SEED)
                    state.seed = new_seed
                    inputs["seed"] = new_seed

        return {"workflow": workflow}
