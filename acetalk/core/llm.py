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
        f"Format every section with ACE-Step structural tags. "
        f"Available tags — use whichever fit the genre and energy: "
        f"Structure: [Intro] [Verse] [Pre-Chorus] [Chorus] [Bridge] [Outro] "
        f"Energy/Production: [Build] [Drop] [Breakdown] [Fade Out] [Silence] "
        f"Performance: [Guitar Solo] [Piano Interlude] [Drum Break] [Solo] [Instrumental] "
        f"Qualifiers: append ': descriptor' to any tag for mood/energy, e.g. "
        f"[Intro: Atmospheric] [Chorus: Anthemic] [Build: Heavy] [Drop: Euphoric] "
        f"[Verse: Intimate] [Bridge: Haunting] [Outro: Fading] [Solo: Virtuosic] [Breakdown: Sparse]. "
        f"Choose tags that match the genre — EDM needs [Build] and [Drop], rock needs [Guitar Solo], etc. "
        f"Every section MUST start with a tag on its own line. "
        f"Output ONLY the lyrics — no explanations, no reasoning, no text before the first section tag."
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
