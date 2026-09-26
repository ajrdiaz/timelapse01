"""Gradación: ciclo día/noche, cielo, viñeta y flash."""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops

from engine.world import ease, seg

NIGHT_TINT = (46, 58, 110)


def construction_span(scene) -> tuple[float, float]:
    s0 = scene.etapas[0].inicio_seg
    end = next((e.inicio_seg for e in scene.etapas if e.tipo in ("terminado", "pregunta", "revelacion", "cierre")),
               scene.etapas[-1].fin_seg)
    return s0, max(s0 + 0.1, end)


def day_phase(scene, t: float) -> float | None:
    """Fase dentro del día (0..1) o None si no hay ciclo en ese momento."""
    dn = scene.escenario.dia_noche
    if not dn.activo or dn.ciclos <= 0:
        return None
    s0, s1 = construction_span(scene)
    if t < s0 or t >= s1:
        return None
    return ((t - s0) / (s1 - s0) * dn.ciclos) % 1.0


def night_factor(scene, t: float) -> float:
    f = day_phase(scene, t)
    if f is None:
        return 0.0
    return ease(seg(f, 0.6, 0.72)) * (1 - ease(seg(f, 0.88, 0.99)))


def sunset_factor(scene, t: float) -> float:
    f = day_phase(scene, t)
    if f is None:
        return 0.0
    return math.exp(-((f - 0.62) / 0.06) ** 2) + math.exp(-((f - 0.95) / 0.03) ** 2) * 0.6


def sky_image(A, scene, t: float, w: int, h: int, box_frac) -> Image.Image:
    """Cielo a resolución de salida, recortado según la cámara (box_frac en 0..1)."""
    fx0, fy0, fx1, fy1 = box_frac

    def crop(img):
        return img.crop((int(fx0 * img.width), int(fy0 * img.height), int(fx1 * img.width), int(fy1 * img.height))).resize((w, h), Image.BILINEAR)

    sky = crop(A.sky("dia", w, h))
    s = min(1.0, sunset_factor(scene, t))
    n = night_factor(scene, t) * scene.escenario.dia_noche.intensidad / 0.65
    n = min(1.0, n)
    if s > 0.01:
        sky = Image.blend(sky, crop(A.sky("atardecer", w, h)), s * 0.85)
    if n > 0.01:
        sky = Image.blend(sky, crop(A.sky("noche", w, h)), n)
    sky = sky.convert("RGBA")
    # sol / luna
    f = day_phase(scene, t)
    sz = int(w * 0.16)
    def place(sprite, px, py):
        sx = int((px - fx0) / (fx1 - fx0) * w - sz / 2)
        sy = int((py - fy0) / (fy1 - fy0) * h - sz / 2)
        sky.alpha_composite(sprite, (sx, sy)) if -sz < sx < w and -sz < sy < h else None
    if f is None or f < 0.7:
        k = 0.35 if f is None else f / 0.7
        place(A.sprite("sol", sz), 0.12 + 0.76 * k, 0.3 - 0.2 * math.sin(math.pi * k))
    if f is not None and 0.66 < f < 0.97:
        k = (f - 0.66) / 0.31
        place(A.sprite("luna", sz), 0.15 + 0.7 * k, 0.28 - 0.15 * math.sin(math.pi * k))
    # nubes
    if scene.escenario.nubes:
        for i in range(4):
            cw = int(w * (0.35 + 0.1 * (i % 2)))
            cl = A.sprite(f"nube{i % 3}", cw)
            speed = 0.012 + 0.006 * i
            px = ((0.2 + i * 0.29 + t * speed) % 1.4) - 0.2
            py = 0.08 + 0.07 * i
            sx = int((px - fx0) / (fx1 - fx0) * w - cw / 2)
            sy = int((py - fy0) / (fy1 - fy0) * h)
            if -cw < sx < w and -cl.height < sy < h:
                if n > 0.01:
                    cl = cl.copy()
                    cl.putalpha(cl.getchannel("A").point(lambda v, k=1 - 0.6 * n: int(v * k)))
                sky.alpha_composite(cl, (sx, sy))
    return sky


def apply_night(img: Image.Image, n: float) -> Image.Image:
    """Oscurece y tiñe de azul con Image.blend (conserva el alfa)."""
    if n <= 0.01:
        return img
    rgb = img.convert("RGB")
    dark = ImageChops.multiply(rgb, Image.new("RGB", rgb.size, NIGHT_TINT))
    out = Image.blend(rgb, dark, min(1.0, n))
    if img.mode == "RGBA":
        out = out.convert("RGBA")
        out.putalpha(img.getchannel("A"))
    return out


@lru_cache(maxsize=4)
def vignette_mask(w: int, h: int, amount: float) -> Image.Image:
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (xs - w / 2) / (w / 2)
    dy = (ys - h / 2) / (h / 2)
    r = np.sqrt(dx * dx * 0.9 + dy * dy * 0.7)
    v = np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6 * amount
    return Image.fromarray((v * 255).astype(np.uint8), "L")


def apply_vignette(img: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return img
    black = Image.new("RGB", img.size, (0, 0, 0))
    return Image.composite(black, img, vignette_mask(img.width, img.height, round(amount, 3)))


def flash_amount(scene, t: float) -> float:
    ft = scene.flash_time
    if ft is None:
        return 0.0
    if ft - 0.08 <= t < ft:
        return (t - (ft - 0.08)) / 0.08
    if t >= ft:
        return math.exp(-(t - ft) * 4.5)
    return 0.0


def apply_flash(img: Image.Image, a: float) -> Image.Image:
    if a <= 0.01:
        return img
    return Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), min(1.0, a))
