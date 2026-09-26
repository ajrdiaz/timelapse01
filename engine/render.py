"""Render del video: pool multiproceso → pipe a ffmpeg (libx264, yuv420p, +faststart) + audio.

CLI:  python -m engine.render examples/bunker_gamer.json [-o salida.mp4] [--draft] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

from engine.schema import Scene

DRAFT = {"size": (540, 960), "fps": 15, "ss": 1}
AUDIO_KBPS = 192


class RenderCancelled(Exception):
    pass


class RenderError(Exception):
    pass


def ffmpeg_bin() -> str:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RenderError("ffmpeg no está instalado o no está en el PATH (ver README).")
    return ff


# --- trabajador --------------------------------------------------------------------
_R = None


def _init(scene_dict: dict, size, ss: int, fonts_dir: Optional[str]):
    global _R
    from engine.frame import FrameRenderer

    _R = FrameRenderer(Scene.model_validate(scene_dict), size=tuple(size), ss=ss, fonts_dir=fonts_dir)


def _frame(args) -> bytes:
    t = args
    return _R.render(t, preview=False).tobytes()


def default_workers() -> int:
    env = os.environ.get("TF_WORKERS")
    if env:
        return max(1, int(env))
    return max(1, (os.cpu_count() or 2) - 1)


def video_bitrate_cap(max_mb: float, dur: float) -> int:
    """kbps máximos de video para no superar max_mb (con 4 % de margen para el contenedor)."""
    total_kbits = max_mb * 1024 * 1024 * 8 / 1000 * 0.96
    return max(300, int(total_kbits / dur - AUDIO_KBPS))


def render_video(scene: Scene, out_path: str, *, size=None, fps: Optional[int] = None, ss: int = 2,
                 workers: Optional[int] = None, progress: Optional[Callable[[float, str], None]] = None,
                 cancel=None, project_dir: Optional[str] = None, fonts_dir: Optional[str] = None,
                 preset: Optional[str] = None) -> dict:
    from engine.audio import build_audio, write_wav

    ff = ffmpeg_bin()
    size = tuple(size or scene.general.size)
    fps = fps or scene.general.fps
    dur = scene.general.duracion_seg
    n = int(round(dur * fps))
    exp = scene.exportacion
    workers = workers or default_workers()
    prog = progress or (lambda f, m: None)
    cancelled = (lambda: cancel.is_set()) if cancel is not None else (lambda: False)
    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    tmpdir = tempfile.mkdtemp(prefix="tf_render_")
    wav = os.path.join(tmpdir, "audio.wav")
    tmp_out = os.path.join(tmpdir, "video.mp4")
    prog(0.0, "Generando audio…")
    write_wav(wav, build_audio(scene, project_dir))
    if cancelled():
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise RenderCancelled()

    cap = video_bitrate_cap(exp.max_mb, dur)
    cmd = [ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
           "-r", str(fps), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", preset or exp.preset, "-crf", str(exp.crf),
           "-maxrate", f"{cap}k", "-bufsize", f"{cap * 2}k", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-t", f"{dur:.3f}", "-movflags", "+faststart", tmp_out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(workers, initializer=_init, initargs=(scene.model_dump(), size, ss, fonts_dir))
    done = 0
    try:
        chunk = max(1, min(12, n // (workers * 4) or 1))
        times = [i / fps for i in range(n)]
        for buf in pool.imap(_frame, times, chunksize=chunk):
            if cancelled():
                raise RenderCancelled()
            try:
                proc.stdin.write(buf)
            except BrokenPipeError:
                raise RenderError("ffmpeg terminó inesperadamente: " + proc.stderr.read().decode(errors="replace")[-800:])
            done += 1
            if done % 3 == 0 or done == n:
                el = time.time() - t_start
                eta = el / done * (n - done)
                prog(0.03 + 0.92 * done / n, f"Fotograma {done}/{n} · faltan ~{int(eta)} s")
        pool.close()
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise RenderError("ffmpeg falló: " + proc.stderr.read().decode(errors="replace")[-800:])
    except BaseException:
        pool.terminate()
        try:
            proc.kill()
        except Exception:
            pass
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    finally:
        pool.join()

    # límite de tamaño: si aún se pasa, reencodar con bitrate fijo
    size_mb = os.path.getsize(tmp_out) / 1024 / 1024
    if size_mb > exp.max_mb:
        prog(0.96, "Ajustando al tamaño máximo…")
        kb = int(video_bitrate_cap(exp.max_mb, dur) * 0.85)
        tmp2 = os.path.join(tmpdir, "video2.mp4")
        subprocess.run([ff, "-y", "-v", "error", "-i", tmp_out, "-c:v", "libx264", "-preset", preset or exp.preset,
                        "-b:v", f"{kb}k", "-maxrate", f"{kb}k", "-bufsize", f"{kb}k", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-movflags", "+faststart", tmp2], check=True)
        tmp_out = tmp2
        size_mb = os.path.getsize(tmp_out) / 1024 / 1024
    shutil.move(tmp_out, out_path)
    shutil.rmtree(tmpdir, ignore_errors=True)
    el = time.time() - t_start
    prog(1.0, "Listo")
    return {"path": out_path, "frames": n, "fps": fps, "size": list(size), "seconds": round(el, 2),
            "per_frame_core": round(el * workers / max(1, n), 3), "mb": round(size_mb, 2), "workers": workers}


def cover_time(scene: Scene) -> float:
    t = scene.exportacion.portada.tiempo_seg
    if t >= 0:
        return min(t, scene.general.duracion_seg - 0.01)
    ft = scene.flash_time
    return min(scene.general.duracion_seg - 0.01, (ft + 1.2) if ft is not None else scene.general.duracion_seg * 0.8)


def render_cover(scene: Scene, out_png: str, fonts_dir: Optional[str] = None, size=None) -> str:
    """Portada: fotograma elegido + texto del gancho grande."""
    from PIL import Image, ImageDraw

    from engine.frame import FrameRenderer
    from engine.ui import resolve_font, text_sprite
    from engine.world import hex_rgb

    fr = FrameRenderer(scene, size=size, ss=2, fonts_dir=fonts_dir)
    img = fr.render(cover_time(scene), preview=False).convert("RGBA")
    w, h = img.size
    u = w / 1080
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle((0, int(h * 0.3), w, int(h * 0.62)), fill=(0, 0, 0, 110))
    img.alpha_composite(shade)
    fp = resolve_font(scene.tipografia.fuente, fonts_dir)
    lines = [ln for ln in scene.gancho.lineas if ln.texto.strip()]
    y = h * 0.46 - len(lines) * 75 * u
    for ln in lines:
        spr = text_sprite(ln.texto, fp, int(135 * u), hex_rgb(ln.color), int(10 * u), int(1000 * u), None)
        img.alpha_composite(spr, (int((w - spr.width) / 2), int(y)))
        y += spr.height + 10 * u
    img.convert("RGB").save(out_png)
    return out_png


def probe_duration(path: str) -> float:
    fp = shutil.which("ffprobe")
    if not fp:
        raise RenderError("ffprobe no está instalado")
    out = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Renderiza un JSON de escena de TimelapseForge a MP4")
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--draft", action="store_true", help="borrador 540×960, 15 fps, sin supermuestreo")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--cover", action="store_true", help="generar también la portada PNG")
    a = ap.parse_args(argv)
    scene = Scene.model_validate_json(Path(a.scene).read_text(encoding="utf-8"))
    out = a.out or str(Path("output") / (Path(a.scene).stem + ("_borrador" if a.draft else "") + ".mp4"))
    kw = dict(size=DRAFT["size"], fps=DRAFT["fps"], ss=DRAFT["ss"], preset="veryfast") if a.draft else {}
    last = [0.0]

    def pr(f, msg):
        if f - last[0] >= 0.05 or f >= 1:
            last[0] = f
            print(f"[{f * 100:5.1f}%] {msg}", flush=True)

    info = render_video(scene, out, workers=a.workers, progress=pr, **kw)
    print(json.dumps(info, ensure_ascii=False))
    if a.cover:
        print("portada:", render_cover(scene, str(Path(out).with_suffix(".png"))))


if __name__ == "__main__":
    main()
