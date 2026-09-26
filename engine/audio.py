"""Audio original y determinista: música procedural + efectos sincronizados con las etapas del JSON,
mezcla y normalización de loudness (ITU-R BS.1770 / EBU R128)."""
from __future__ import annotations

import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import signal

from engine.stages import make_stage
from engine.ui import callout_times, text_timeline

SR = 48000

CHORDS = {
    "Am": (57, "m"), "F": (53, "M"), "C": (48, "M"), "G": (55, "M"),
    "Em": (52, "m"), "D": (50, "M"), "Dm": (50, "m"), "Bb": (46, "M"),
}
PROGRESSIONS = {
    "A menor: Am-F-C-G": ["Am", "F", "C", "G"],
    "E menor: Em-C-G-D": ["Em", "C", "G", "D"],
    "D menor: Dm-Bb-F-C": ["Dm", "Bb", "F", "C"],
}


def mtof(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def chord_notes(name: str) -> list[int]:
    root, q = CHORDS[name]
    return [root, root + (3 if q == "m" else 4), root + 7]


# --- osciladores / utilidades ------------------------------------------------------
def env_exp(n: int, decay: float, attack: float = 0.002) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def tone(freq: float, dur: float, decay: float, partials=((1, 1.0),), attack=0.002) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for ratio, amp in partials:
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / (decay / max(1, ratio ** 0.5)))
    a = np.clip(t / attack, 0, 1)
    return (out * a).astype(np.float32)


def saw(freq: float, n: int, detune: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    ph = (freq * (1 + detune) * t) % 1.0
    return (2 * ph - 1).astype(np.float32)


def square(freq: float, n: int, duty: float = 0.5) -> np.ndarray:
    t = np.arange(n) / SR
    return np.where((freq * t) % 1.0 < duty, 1.0, -1.0).astype(np.float32)


def lp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def hp(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def bp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    sos = signal.butter(2, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def add(buf: np.ndarray, x: np.ndarray, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
    i = int(round(t * SR))
    if i >= buf.shape[0] or i + len(x) <= 0:
        return
    s = max(0, -i)
    x = x[s:]
    i = max(0, i)
    n = min(len(x), buf.shape[0] - i)
    l = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    r = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    buf[i:i + n, 0] += x[:n] * gain * l
    buf[i:i + n, 1] += x[:n] * gain * r


# --- instrumentos ------------------------------------------------------------------
class Kit:
    def __init__(self, seed: int):
        self.rng = np.random.default_rng(seed)
        self._c: dict = {}

    def noise(self, dur: float) -> np.ndarray:
        return self.rng.standard_normal(int(dur * SR)).astype(np.float32)

    def get(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    def marimba(self, note: int, dur: float = 0.6) -> np.ndarray:
        return self.get(("mar", note), lambda: tone(mtof(note), dur, 0.28, ((1, 1.0), (4, 0.25), (10, 0.06)), 0.001) * 0.5)

    def anvil(self) -> np.ndarray:
        def f():
            x = tone(1150, 0.5, 0.2, ((1, 1.0), (2.76, 0.6), (5.4, 0.4), (8.93, 0.25)), 0.0005)
            n = hp(self.noise(0.5), 3000) * env_exp(int(0.5 * SR), 0.01)
            return (x * 0.35 + n * 0.25).astype(np.float32)
        return self.get("anvil", f)

    def kick(self, hard: bool = False) -> np.ndarray:
        def f():
            n = int(0.45 * SR)
            t = np.arange(n) / SR
            fr = 45 + (140 if hard else 90) * np.exp(-t * 28)
            ph = 2 * np.pi * np.cumsum(fr) / SR
            x = np.sin(ph) * np.exp(-t * (6 if hard else 9))
            click = hp(self.noise(0.45), 2000) * np.exp(-t * 300) * 0.3
            return ((x + click) * (0.95 if hard else 0.6)).astype(np.float32)
        return self.get(("kick", hard), f)

    def snare(self, clap: bool = False) -> np.ndarray:
        def f():
            n = int(0.3 * SR)
            t = np.arange(n) / SR
            nz = bp(self.noise(0.3), 900, 8000) * np.exp(-t * (18 if clap else 22))
            body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * (0 if clap else 0.5)
            if clap:
                for d in (0.012, 0.024):
                    k = int(d * SR)
                    nz[k:] += nz[:-k] * 0.6
            return ((nz * 0.5 + body) * 0.55).astype(np.float32)
        return self.get(("snare", clap), f)

    def hat(self, open_: bool = False) -> np.ndarray:
        def f():
            d = 0.25 if open_ else 0.05
            n = int(d * SR)
            return (hp(self.noise(d), 7000) * env_exp(n, d / 3) * 0.3).astype(np.float32)
        return self.get(("hat", open_), f)

    def shaker(self) -> np.ndarray:
        return self.get("shaker", lambda: (bp(self.noise(0.08), 4000, 12000) * env_exp(int(0.08 * SR), 0.02, 0.01) * 0.18).astype(np.float32))

    def stab(self, notes: list[int], dur: float, chip: bool) -> np.ndarray:
        def f():
            n = int(dur * SR)
            out = np.zeros(n, np.float32)
            for nt in notes:
                if chip:
                    out += square(mtof(nt + 12), n, 0.25) * 0.18
                else:
                    for dt in (-0.006, 0.0, 0.007):
                        out += saw(mtof(nt + 12), n, dt) * 0.12
            e = env_exp(n, dur * 0.6, 0.003)
            return (lp(out, 2600 if not chip else 6000) * e).astype(np.float32)
        return self.get(("stab", tuple(notes), round(dur, 3), chip), f)

    def bass(self, note: int, dur: float, chip: bool) -> np.ndarray:
        def f():
            n = int(dur * SR)
            t = np.arange(n) / SR
            x = square(mtof(note - 12), n, 0.5) * 0.3 if chip else (np.sin(2 * np.pi * mtof(note - 12) * t) * 0.6 + lp(saw(mtof(note - 12), n), 400) * 0.25)
            return (x * np.minimum(1, np.minimum(t / 0.005, (dur - t) / 0.02 + 0.0))).astype(np.float32)
        return self.get(("bass", note, round(dur, 3), chip), f)

    def lead(self, note: int, dur: float, chip: bool) -> np.ndarray:
        def f():
            n = int(dur * SR)
            x = square(mtof(note + 12), n, 0.5) * 0.12 if chip else lp(saw(mtof(note + 12), n) + saw(mtof(note + 12), n, 0.004), 3500) * 0.08
            return (x * env_exp(n, dur * 0.8, 0.004)).astype(np.float32)
        return self.get(("lead", note, round(dur, 3), chip), f)


# --- música -------------------------------------------------------------------------
def music_track(scene, dur: float) -> np.ndarray:
    a = scene.audio
    kit = Kit(scene.general.seed + 101)
    buf = np.zeros((int(dur * SR), 2), np.float32)
    beat = 60.0 / a.bpm
    bar = beat * 4
    prog = PROGRESSIONS[a.progresion]
    ft = scene.flash_time
    preg = scene.first_stage("pregunta")
    build_start = preg.inicio_seg if preg else (ft - 3 if ft else dur)
    drop = ft if ft is not None else build_start
    if not a.drop_sincronizado and ft is not None:
        drop = math.ceil((build_start) / bar) * bar
    anchor = drop  # la rejilla rítmica se alinea para que el drop caiga en un tiempo fuerte
    first = -math.ceil(anchor / beat)
    rng = np.random.default_rng(scene.general.seed + 7)
    patt = [0, 2, 1, 2, 0, 2, 1, 3]  # arpegio de marimba (índices de acorde)
    motif = [0, 2, 3, 2, 1, 2, 3, 4]
    k = first
    while True:
        tb = anchor + k * beat
        if tb >= dur:
            break
        bi = k % 4  # tiempo dentro del compás
        bar_i = (k // 4) % len(prog)
        notes = chord_notes(prog[bar_i])
        if tb >= -beat:
            if tb < build_start:  # sección de obra: yunque + marimba
                add(buf, kit.kick(False), tb, 0.55)
                if bi in (1, 3):
                    add(buf, kit.anvil(), tb, 0.45, 0.2)
                for h in range(2):
                    idx = patt[(bi * 2 + h) % 8]
                    oct_ = 12 if idx == 3 else 0
                    add(buf, kit.marimba(notes[idx % 3] + 12 + oct_), tb + h * beat / 2, 0.5, -0.25 + 0.5 * h)
                    add(buf, kit.shaker(), tb + h * beat / 2 + beat / 4, 0.8, 0.4)
                if bi == 0:
                    add(buf, kit.marimba(notes[0] - 12, 1.0), tb, 0.7)
                if bi == 2 and (k // 4) % 2 == 1:
                    m = motif[(k // 4) % 8]
                    add(buf, kit.marimba(notes[m % 3] + 24), tb + beat * 0.5, 0.25, 0.3)
            elif tb < drop:  # subida: solo marimba filtrada y redoble
                prog_k = (tb - build_start) / max(0.1, drop - build_start)
                add(buf, kit.marimba(notes[0] + 12), tb, 0.3)
                rolls = 1 if prog_k < 0.5 else (2 if prog_k < 0.8 else 4)
                for r in range(rolls):
                    add(buf, kit.snare(False), tb + r * beat / rolls, 0.2 + 0.4 * prog_k)
            else:  # drop
                chip = a.estilo_drop == "chiptune"
                add(buf, kit.kick(True), tb, 0.9)
                if bi in (1, 3):
                    add(buf, kit.snare(clap=not chip), tb, 0.7)
                add(buf, kit.hat(False), tb + beat / 2, 0.8, 0.3)
                add(buf, kit.hat(bi == 3), tb + beat * 0.75, 0.4, -0.3)
                add(buf, kit.bass(notes[0], beat * 0.45, chip), tb + beat / 2, 0.8)
                if bi == 0:
                    add(buf, kit.stab(notes, bar * 0.9, chip), tb, 0.6)
                arp = [0, 1, 2, 1] if chip else [2, 1, 0, 1]
                steps = 4 if chip else 2
                for s_ in range(steps):
                    n = notes[arp[(bi * steps + s_) % 4]] + (12 if chip else 0)
                    add(buf, kit.lead(n, beat / steps * 0.9, chip), tb + s_ * beat / steps, 0.5, 0.15)
        k += 1
    # riser de noise antes del drop
    if drop > build_start:
        n = int((drop - build_start) * SR)
        if n > SR // 10:
            nz = kit.noise(drop - build_start)
            tt = np.linspace(0, 1, n, dtype=np.float32)
            # filtrado por bloques con frecuencia de corte creciente
            out = np.zeros(n, np.float32)
            blocks = 16
            for b in range(blocks):
                s, e = b * n // blocks, (b + 1) * n // blocks
                fc = 400 + 9000 * (b / blocks) ** 2
                out[s:e] = bp(nz[s:e], max(100, fc * 0.5), fc * 1.5)
            add(buf, out * tt ** 2 * 0.35, build_start, 1.0)
    # fundido final
    fade = int(min(1.5, dur * 0.1) * SR)
    buf[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
    _ = rng
    return buf


def load_music_file(path: str, dur: float) -> np.ndarray:
    """Decodifica un archivo con ffmpeg a 48 kHz estéreo, lo recorta/repite y hace fundido."""
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg no está instalado")
    raw = subprocess.run([ff, "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    n = int(dur * SR)
    if len(x) == 0:
        return np.zeros((n, 2), np.float32)
    reps = int(math.ceil(n / len(x)))
    x = np.tile(x, (reps, 1))[:n]
    fade = int(1.5 * SR)
    x[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
    return x


# --- efectos ---------------------------------------------------------------------------
class SFX:
    def __init__(self, seed: int):
        self.k = Kit(seed + 303)

    def make(self, name: str, dur: float = 0.0) -> np.ndarray:
        k = self.k
        if name == "martillo":
            return k.get(name, lambda: (tone(1300, 0.18, 0.03, ((1, 1), (2.3, 0.5)), 0.0005) * 0.5 + bp(k.noise(0.18), 800, 5000) * env_exp(int(0.18 * SR), 0.015) * 0.6))
        if name == "metal":
            return k.get(name, lambda: tone(2300, 0.4, 0.12, ((1, 1), (2.7, 0.5), (4.1, 0.3)), 0.0005) * 0.35)
        if name == "escotilla":
            return k.get(name, lambda: tone(310, 0.9, 0.3, ((1, 1), (2.4, 0.7), (3.9, 0.4), (6.2, 0.2)), 0.0005) * 0.6 + lp(k.noise(0.9), 1200) * env_exp(int(0.9 * SR), 0.05) * 0.5)
        if name == "golpe_tierra":
            def f():
                n = int(0.4 * SR)
                t = np.arange(n) / SR
                return (np.sin(2 * np.pi * np.cumsum(50 + 60 * np.exp(-t * 20)) / SR) * np.exp(-t * 10) * 0.7 + lp(k.noise(0.4), 500) * np.exp(-t * 14) * 0.6).astype(np.float32)
            return k.get(name, f)
        if name in ("tierra", "grava"):
            def f():
                d = 0.6
                n = int(d * SR)
                t = np.arange(n) / SR
                e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7
                base = lp(k.noise(d), 900 if name == "tierra" else 3000) * e * 0.7
                if name == "grava":
                    clicks = (k.rng.random(n) > 0.997).astype(np.float32) * k.rng.standard_normal(n).astype(np.float32)
                    base += bp(clicks, 2000, 9000) * 2.0
                return base.astype(np.float32)
            return k.get(name, f)
        if name == "madera":
            return k.get(name, lambda: tone(420, 0.25, 0.04, ((1, 1), (2.1, 0.4), (3.3, 0.2)), 0.0005) * 0.6)
        if name in ("brocha", "pasto", "rastrillo"):
            lo, hi, d = {"brocha": (1500, 6000, 0.25), "pasto": (600, 3000, 0.4), "rastrillo": (1000, 5000, 0.3)}[name]
            return k.get(name, lambda: (bp(k.noise(d), lo, hi) * np.sin(np.pi * np.linspace(0, 1, int(d * SR))) ** 2 * 0.35).astype(np.float32))
        if name == "whoosh":
            def f():
                d = 0.6
                n = int(d * SR)
                x = k.noise(d)
                out = np.zeros(n, np.float32)
                for b in range(8):
                    s, e = b * n // 8, (b + 1) * n // 8
                    fc = 500 + 5000 * (b / 8)
                    out[s:e] = bp(x[s:e], fc * 0.6, fc * 1.5)
                return (out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.6).astype(np.float32)
            return k.get(name, f)
        if name == "pop":
            def f():
                n = int(0.12 * SR)
                t = np.arange(n) / SR
                return (np.sin(2 * np.pi * np.cumsum(500 + 900 * t / 0.12) / SR) * np.exp(-t * 35) * 0.35).astype(np.float32)
            return k.get(name, f)
        if name == "ding":
            return k.get(name, lambda: tone(1568, 0.6, 0.25, ((1, 1), (2, 0.3), (3, 0.1))) * 0.3)
        if name == "tada":
            def f():
                out = np.zeros(int(1.2 * SR), np.float32)
                for i, nt in enumerate((72, 76, 79, 84)):
                    x = tone(mtof(nt), 0.9, 0.35, ((1, 1), (2, 0.3), (3, 0.15)))
                    s = int(i * 0.07 * SR)
                    out[s:s + len(x)] += x * 0.25
                return out
            return k.get(name, f)
        if name == "impacto":
            def f():
                n = int(1.8 * SR)
                t = np.arange(n) / SR
                sub = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-t * 6)) / SR) * np.exp(-t * 2.2)
                crash = hp(k.noise(1.8), 3000) * np.exp(-t * 3) * 0.4
                return ((sub * 0.9 + crash) * 0.8).astype(np.float32)
            return k.get(name, f)
        if name == "motor":
            n = max(1, int(dur * SR))
            t = np.arange(n) / SR
            rpm = 38 + 6 * np.sin(2 * np.pi * 0.7 * t)
            x = lp(np.sign(np.sin(2 * np.pi * np.cumsum(rpm) / SR)).astype(np.float32), 300) * 0.25 + lp(k.noise(dur), 200) * 0.3
            e = np.minimum(1, np.minimum(t / 0.3, (dur - t) / 0.3 + 1e-3))
            return (x * e).astype(np.float32)
        if name == "vertido":
            n = max(1, int(dur * SR))
            t = np.arange(n) / SR
            x = lp(k.noise(dur), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 2.2 * t) ** 2) * 0.35
            e = np.minimum(1, np.minimum(t / 0.2, (dur - t) / 0.3 + 1e-3))
            return (x * e).astype(np.float32)
        return np.zeros(1, np.float32)


def sfx_events(scene) -> list:
    """Eventos de todas las etapas + los de la interfaz (pops de texto, callouts, flash)."""
    from engine.stages.base import SfxEvent

    ev = []
    for e in scene.etapas:
        ev += make_stage(e).sfx_events(e.inicio_seg, e.fin_seg)
    for it in text_timeline(scene):
        ev.append(SfxEvent(it.t0, "whoosh" if it.anim == "deslizar" else "pop", 0.5 if it.kind != "subtitulo" else 0.3))
    for t in callout_times(scene):
        ev.append(SfxEvent(t, "ding", 0.6))
    if scene.flash_time is not None:
        ev.append(SfxEvent(scene.flash_time, "impacto", 1.0))
    return ev


def sfx_track(scene, dur: float) -> np.ndarray:
    buf = np.zeros((int(dur * SR), 2), np.float32)
    sfx = SFX(scene.general.seed)
    rng = np.random.default_rng(scene.general.seed + 55)
    for ev in sorted(sfx_events(scene), key=lambda e: (e.t, e.name)):
        if ev.t >= dur:
            continue
        x = sfx.make(ev.name, min(ev.dur, dur - ev.t))
        add(buf, x, ev.t, ev.gain, float(rng.uniform(-0.3, 0.3)))
    return buf


# --- loudness (BS.1770) ------------------------------------------------------------
def k_weight(x: np.ndarray) -> np.ndarray:
    # coeficientes estándar a 48 kHz
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    y = signal.lfilter(b1, a1, x, axis=0)
    return signal.lfilter(b2, a2, y, axis=0)


def integrated_lufs(x: np.ndarray) -> float:
    y = k_weight(x.astype(np.float64))
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(y) < blk:
        ms = np.mean(np.sum(y ** 2, axis=1))
        return -0.691 + 10 * math.log10(max(ms, 1e-12))
    p = np.sum(y ** 2, axis=1)
    cs = np.concatenate([[0], np.cumsum(p)])
    starts = np.arange(0, len(p) - blk + 1, hop)
    z = (cs[starts + blk] - cs[starts]) / blk
    lk = -0.691 + 10 * np.log10(np.maximum(z, 1e-12))
    z = z[lk > -70]
    if len(z) == 0:
        return -70.0
    rel = -0.691 + 10 * math.log10(np.mean(z)) - 10
    lk = -0.691 + 10 * np.log10(z)
    z2 = z[lk > rel]
    return -0.691 + 10 * math.log10(np.mean(z2 if len(z2) else z))


def limiter(x: np.ndarray, ceiling: float = 0.89) -> np.ndarray:
    """Limitador suave: ganancia con ataque instantáneo y liberación de 80 ms."""
    peak = np.max(np.abs(x), axis=1)
    need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    # suaviza la ganancia (mínimo en ventana + liberación exponencial)
    win = int(0.005 * SR)
    from scipy.ndimage import minimum_filter1d

    g = minimum_filter1d(need, size=win * 2 + 1)
    rel = math.exp(-1 / (0.08 * SR))
    g = signal.lfilter([1 - rel], [1, -rel], g - 1) + 1
    g = np.minimum(g, minimum_filter1d(need, size=win * 2 + 1))
    return (x * g[:, None]).astype(np.float32)


def normalize(x: np.ndarray, target: float) -> np.ndarray:
    for _ in range(3):
        cur = integrated_lufs(x)
        if cur <= -69:
            return x
        x = x * (10 ** ((target - cur) / 20))
        x = limiter(x, 0.89)  # ≈ -1 dBFS
        if abs(integrated_lufs(x) - target) < 0.3:
            break
    return np.clip(x, -1, 1).astype(np.float32)


def build_audio(scene, project_dir: Optional[str] = None) -> np.ndarray:
    a = scene.audio
    dur = scene.general.duracion_seg
    mix = np.zeros((int(round(dur * SR)), 2), np.float32)
    if a.musica:
        if a.musica_propia:
            p = Path(a.musica_propia)
            if not p.is_absolute() and project_dir:
                p = Path(project_dir) / "uploads" / a.musica_propia
            mus = load_music_file(str(p), dur)
        else:
            mus = music_track(scene, dur)
        mix[: len(mus)] += mus[: len(mix)] * a.volumen_musica
    mix += sfx_track(scene, dur)[: len(mix)] * a.volumen_sfx * 0.9
    return normalize(mix, a.lufs_objetivo)


def write_wav(path: str, x: np.ndarray) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
