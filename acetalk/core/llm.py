import json
import logging
from typing import Callable

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://localhost:11434"


def list_models() -> list[str]:
    """Fetch available Ollama models. Returns fallback string in list on failure."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return models if models else ["(no models found)"]
    except Exception as exc:
        logger.debug("Ollama unreachable: %s", exc)
        return ["(Ollama offline)"]


def generate_lyrics(
    prompt: str,
    genre: str,
    key: str,
    mood: str,
    structure: str,
    model: str,
    on_token: Callable[[str], None],
    subject: str = "",
    name_override: str = "",
) -> None:
    """
    Stream lyrics from Ollama. Calls on_token(chunk) for each token received.
    on_token is called on the calling thread — caller must route to UI thread if needed.
    """
    mood_str = f"with a {mood} mood" if mood else "with an appropriate mood"
    subject_str = f" The song is about: {subject}." if subject else ""
    name_str = (
        f" IMPORTANT: In the lyrics, refer to '{subject or 'the subject'}' as '{name_override}' — "
        f"never use any other name."
    ) if name_override else ""

    system = (
        f"You are an expert lyricist specializing in {genre} music. "
        f"Write lyrics in the key of {key}, {mood_str}. "
        f"Use this song structure: {structure}.{subject_str}{name_str} "
        f"Format sections with ACE-Step structural tags like [Intro], [Verse], [Chorus], [Bridge], [Outro]. "
        f"Use qualifier variants like [Chorus: Anthemic] or [Intro: Atmospheric] where appropriate. "
        f"Output ONLY the lyrics — no explanations, no reasoning, no headings outside of brackets. "
        f"Do not include any text before the first section tag."
    )
    payload = {
        "model": model,
        "prompt": f"{system}\n\nTask: {prompt}",
        "stream": True,
    }
    try:
        with requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        on_token(token)
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.error("Ollama generation failed: %s", exc)
        on_token(f"\n[Error: {exc}]")
