import shutil

import pytest

from engine.audio import SR, build_audio, integrated_lufs
from engine.render import probe_duration, render_video
from engine.schema import Scene, rescale_times

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no instalado")


def short_scene(dur=15.0):
    d = rescale_times(Scene().model_dump(), dur)
    d["gancho"]["duracion_seg"] = 0.5
    d = rescale_times(d, dur)
    return Scene.model_validate(d)


def test_audio_loudness():
    s = short_scene(15)
    x = build_audio(s)
    assert x.shape == (int(round(15 * SR)), 2)
    assert integrated_lufs(x) == pytest.approx(s.audio.lufs_objetivo, abs=1.0)
    assert abs(x).max() <= 1.0


@pytest.mark.parametrize("dur", [15.0, 16.353, 72.353])
def test_audio_length_non_integer(dur):
    s = short_scene(dur)
    assert build_audio(s).shape[0] == int(round(dur * SR))


@needs_ffmpeg
def test_smoke_render_3s(tmp_path):
    # humo: 3 s a 360×640 (el esquema exige ≥15 s, así que se renderiza una escena de 15 s
    # comprimida y se corta a 3 s con la duración de la escena modificada tras validar)
    s = short_scene(15)
    s.general.duracion_seg = 3.0
    out = tmp_path / "smoke.mp4"
    info = render_video(s, str(out), size=(360, 640), fps=24, ss=1, workers=2, preset="ultrafast")
    assert out.exists() and info["frames"] == 72
    assert probe_duration(str(out)) == pytest.approx(3.0, abs=0.05)


@needs_ffmpeg
def test_duration_matches(tmp_path):
    s = short_scene(15)
    out = tmp_path / "d.mp4"
    render_video(s, str(out), size=(360, 640), fps=15, ss=1, workers=2, preset="ultrafast")
    assert probe_duration(str(out)) == pytest.approx(15.0, abs=0.05)


def test_music_varies_by_seed_and_is_deterministic(example_dict):
    import numpy as np

    from engine.audio import music_track
    from engine.schema import Scene

    def track(seed, prog="A menor: Am-F-C-G"):
        d = {**example_dict, "general": {**example_dict["general"], "seed": seed},
             "audio": {**example_dict["audio"], "progresion": prog}}
        s = Scene.model_validate(d)
        return music_track(s, s.general.duracion_seg)

    a = track(7)
    assert np.array_equal(a, track(7))
    assert not np.allclose(a, track(8))
    assert not np.allclose(a, track(7, "F# menor: F#m-D-A-E"))
