"""Cámara: define el recorte del mundo (a 2×) que se reescala al tamaño de salida."""
from __future__ import annotations

import math

from engine.world import Layout, ease, lerp, seg


def camera(scene, L: Layout, t: float) -> tuple[float, float, float]:
    """Devuelve (cx, cy, zoom) en px de mundo."""
    base = (L.W / 2, L.H / 2, 1.0)
    room = ((L.ix0 + L.ix1) / 2, (L.roof_bot_y + L.floor_y) / 2 - L.m(0.25))
    cx, cy, z = base
    g = scene.gancho
    hook_end = scene.etapas[0].inicio_seg
    if g.zoom_out and t < hook_end:
        k = ease(t / max(0.01, hook_end))
        z = lerp(g.zoom_intensidad, 1.0, k)
        cx = lerp(L.cx, base[0], k)
        cy = lerp(L.ground_y - L.m(0.4), base[1], k)
    zr = scene.revelacion.zoom_camara
    preg = scene.first_stage("pregunta")
    rev = scene.first_stage("revelacion")
    cie = scene.first_stage("cierre")
    ft = scene.flash_time
    if preg and t >= preg.inicio_seg:
        k = ease(seg(t, preg.inicio_seg, preg.fin_seg))
        zp = max(1.0, zr * 0.82)
        z = lerp(1.0, zp, k)
        cx = lerp(base[0], room[0], k)
        cy = lerp(base[1], room[1], k)
    if rev and ft is not None and t >= ft:
        age = t - ft
        drift = seg(t, ft, rev.fin_seg) * 0.05
        punch = 0.1 * math.exp(-age * 5)
        z = zr * (1 + drift) + punch
        cx, cy = room
        if age < 0.45:
            amp = L.m(0.08) * (1 - age / 0.45)
            cx += math.sin(age * 90) * amp
            cy += math.cos(age * 77) * amp
    if cie and rev and t >= cie.inicio_seg:
        k = ease(seg(t, cie.inicio_seg, cie.fin_seg))
        z0 = zr * 1.05
        z = lerp(z0, max(1.0, zr * 0.85), k)
        cx, cy = room
    return cx, cy, max(1.0, z)


def crop_box(L: Layout, cam) -> tuple[float, float, float, float]:
    cx, cy, z = cam
    w, h = L.W / z, L.H / z
    x0 = min(max(0.0, cx - w / 2), L.W - w)
    y0 = min(max(0.0, cy - h / 2), L.H - h)
    return x0, y0, x0 + w, y0 + h


def world_to_screen(box, out_w: int, out_h: int, x: float, y: float) -> tuple[float, float]:
    x0, y0, x1, y1 = box
    return (x - x0) * out_w / (x1 - x0), (y - y0) * out_h / (y1 - y0)
