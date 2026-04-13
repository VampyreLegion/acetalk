from dataclasses import dataclass, field, asdict


@dataclass
class SessionState:
    # Style tab
    genre: str = ""
    bpm: int = 120
    key: str = "C"
    scale: str = "Major"
    mode: str = ""
    time_sig: str = "4/4"

    # Instruments tab — list of fully-rendered ACE-Step phrases
    instruments: list[str] = field(default_factory=list)

    # Vocals tab
    vocal_tags: list[str] = field(default_factory=list)

    # Lyrics tab
    lyrics: str = ""

    # Metadata
    song_title: str = ""
    artist: str = ""
    album: str = ""
    year: str = ""
    genre_tags: str = ""       # comma-separated genre strings for ID3
    description: str = ""

    # Parameters tab
    cfg_scale: float = 2.0
    temperature: float = 0.85
    top_p: float = 0.9
    top_k: int = 0
    min_p: float = 0.0
    duration: int = 120
    steps: int = 8
    task_type: str = "text2music"
    seed: int = 0            # seed used for generation
    lock_seed: bool = False  # True = reuse seed for iterative refinement

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SessionState":
        known = {k: list(v) if isinstance(v, list) else v
                 for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)
