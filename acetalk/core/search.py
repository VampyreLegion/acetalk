import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

VOCALS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "vocals.json")
)

_VOCAL_KEYWORDS = [
    "breathy", "raspy", "smooth", "nasal", "powerful", "clear",
    "whispered", "whispery", "belted", "falsetto", "spoken word", "operatic",
    "airy", "gritty", "warm", "bright", "vibrato", "melismatic",
    "intimate", "raw", "soulful", "crystal-clear", "husky", "soft",
    "close-mic vocal", "female vocal", "male vocal", "androgynous vocal",
    "jazz-inflected", "melancholic", "dramatic", "understated",
]


def _load_vocals_db() -> dict:
    try:
        with open(VOCALS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"artists": []}


def _save_vocals_db(db: dict) -> None:
    with open(VOCALS_PATH, "w") as f:
        json.dump(db, f, indent=2)


def _parse_artist_result(name: str, text: str) -> dict:
    """Extract ACE-Step vocal descriptors from search result text."""
    found = [kw for kw in _VOCAL_KEYWORDS if kw.lower() in text.lower()]
    if not found:
        found = ["vocal"]
    return {
        "name": name,
        "range": "",
        "preferred_key": "",
        "style": "",
        "known_for": [],
        "ace_step_descriptors": found,
    }


def _web_search_artist(name: str) -> dict | None:
    """Try Brave first, fall back to DDG. Returns parsed artist dict or None."""
    query = f"{name} vocalist vocal style singing technique range"
    text = ""
    source_label = ""

    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if brave_key:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
                params={"q": query, "count": 5},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("web", {}).get("results", [])
            text = " ".join(r.get("description", "") for r in results)
            source_label = "brave"
        except Exception as exc:
            logger.warning("Brave search failed: %s", exc)

    if not text:
        try:
            from duckduckgo_search import DDGS
            with DDGS(timeout=10) as ddgs:
                results = ddgs.text(query, max_results=5)
                text = " ".join(r.get("body", "") for r in results)
            source_label = "ddg"
        except Exception as exc:
            logger.warning("DDG search failed: %s", exc)

    if not text:
        return None

    result = _parse_artist_result(name, text)
    result["_source"] = source_label
    return result


def search_artist(name: str, source: str = "both") -> dict | None:
    """
    Search for artist vocal info.
    source: 'local', 'web', or 'both' (local first, then web)
    Returns artist dict or None.
    """
    db = _load_vocals_db()

    # Local lookup (case-insensitive)
    name_lower = name.strip().lower()
    for artist in db.get("artists", []):
        if artist["name"].lower() == name_lower:
            return artist

    if source == "local":
        return None

    # Web search
    result = _web_search_artist(name)
    if result:
        db["artists"].append(result)
        _save_vocals_db(db)

    return result
