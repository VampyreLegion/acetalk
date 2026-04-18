import sys
from unittest.mock import patch, MagicMock, call
from acetalk.core.demucs_worker import DemucsWorker


def test_worker_builds_correct_4stem_command():
    worker = DemucsWorker(
        input_path="/output/audio/song.mp3",
        model="htdemucs",
        output_dir="/output/separated",
    )
    cmd = worker._build_command()
    assert sys.executable in cmd
    assert "-m" in cmd
    assert "demucs" in cmd
    assert "--mp3" in cmd
    assert "-n" in cmd
    assert "htdemucs" in cmd
    assert "-o" in cmd
    assert "/output/separated" in cmd
    assert "/output/audio/song.mp3" in cmd


def test_worker_builds_correct_6stem_command():
    worker = DemucsWorker(
        input_path="/output/audio/song.mp3",
        model="htdemucs_6s",
        output_dir="/output/separated",
    )
    cmd = worker._build_command()
    assert "htdemucs_6s" in cmd


def test_worker_resolves_stem_paths(tmp_path):
    model = "htdemucs"
    track = "song"
    stem_dir = tmp_path / model / track
    stem_dir.mkdir(parents=True)
    (stem_dir / "vocals.mp3").write_text("")
    (stem_dir / "drums.mp3").write_text("")
    (stem_dir / "bass.mp3").write_text("")
    (stem_dir / "other.mp3").write_text("")

    worker = DemucsWorker(
        input_path=f"/some/path/{track}.mp3",
        model=model,
        output_dir=str(tmp_path),
    )
    stems = worker._collect_stems()
    assert len(stems) == 4
    assert all(s.endswith(".mp3") for s in stems)
