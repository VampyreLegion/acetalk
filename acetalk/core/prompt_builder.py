from .state import SessionState

# Default instance used to detect "unchanged from default" values
_DEFAULTS = SessionState()


def build_caption(state: SessionState) -> str:
    """Assemble the ACE-Step caption/tags string from current session state.

    Style fields (BPM, key, scale, time_sig) are included when:
    - A genre is selected (context is established), OR
    - The field was explicitly changed from its default value.
    Mode and instruments/vocals are always included when non-empty.
    """
    parts = []

    if state.genre:
        parts.append(state.genre.lower())

    # BPM: include if genre set OR explicitly changed from default (120)
    if state.bpm and (state.genre or state.bpm != _DEFAULTS.bpm):
        parts.append(f"{state.bpm} BPM")

    # Key/Scale: include if genre set OR either value changed from defaults ("C"/"Major")
    if state.key and (state.genre or state.key != _DEFAULTS.key or state.scale != _DEFAULTS.scale):
        key_str = state.key
        if state.scale:
            key_str += f" {state.scale}"
        parts.append(key_str)

    # Mode: always include when non-empty (default is "")
    if state.mode:
        parts.append(f"{state.mode} mode")

    # Time sig: include if genre set OR changed from default ("4/4")
    if state.time_sig and (state.genre or state.time_sig != _DEFAULTS.time_sig):
        parts.append(f"{state.time_sig} time")

    parts.extend(state.instruments)
    parts.extend(state.vocal_tags)

    return ", ".join(parts)


def build_lyrics(state: SessionState) -> str:
    """Return the lyrics string from state."""
    return state.lyrics


def build_prompt(state: SessionState) -> tuple[str, str]:
    """Return (caption, lyrics) tuple."""
    return build_caption(state), build_lyrics(state)
