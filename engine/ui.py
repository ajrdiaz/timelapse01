"""Capa de interfaz: textos con animación pop, contador, barra, callouts, CTA y degradado superior.

Todas las medidas están en px de referencia 1080×1920 y se escalan al tamaño de salida.
`text_timeline()` es la única fuente de verdad de qué texto aparece y cuándo (el audio la usa
para sincronizar los "pops")."""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine.world import hex_rgb

ROOT = Path(__file__).resolve().parent.parent
FONTS = {
    "anton": ROOT / "assets" / "fonts" / "Anton-Regular.woff",
    "dejavu": ROOT / "assets" / "fonts" / "DejaVuSans-Bold.ttf",
}
CONSTRUCTION_EXCLUDE = ("pregunta", "revelacion", "cierre")
TITLE_COLOR = (255, 255, 255)
SUB_COLOR = (255, 212, 0)


def resolve_font(name: str, fonts_dir: Optional[str] = None) -> str:
    key = (name or "").strip().lower()
    if key in FONTS:
        return str(FONTS[key])
    for base in filter(None, [fonts_dir, str(ROOT / "assets" / "fonts")]):
        p = Path(base) / name
        if p.is_file():
            return str(p)
    return str(FONTS["anton"])


@lru_cache(maxsize=64)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(6, int(size)))


@lru_cache(maxsize=256)
def text_sprite(text: str, path: str, size: int, color: tuple, stroke: int, max_w: int,
                box: Optional[tuple] = None) -> Image.Image:
    """Texto con contorno (o dentro de una píldora de color) como sprite RGBA."""
    f = font(path, size)
    bb = f.getbbox(text, stroke_width=stroke)
    tw = bb[2] - bb[0]
    if tw > max_w and len(text) > 0:
        size = int(size * max_w / tw)
        f = font(path, size)
        bb = f.getbbox(text, stroke_width=stroke)
    pad = int(size * 0.35) if box else 2
    w = bb[2] - bb[0] + 2 * pad
    h = bb[3] - bb[1] + 2 * pad
    img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if box:
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=int(h * 0.3), fill=box + (255,))
        d.text((pad - bb[0], pad - bb[1]), text, font=f, fill=color)
    else:
        d.text((pad - bb[0], pad - bb[1]), text, font=f, fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0))
    return img


def ease_out_back(x: float) -> float:
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


@dataclass
class TextItem:
    t0: float
    t1: float
    text: str
    size: int
    color: tuple
    y: float  # centro vertical en px de referencia
    anim: str = "pop"  # pop | deslizar | shake
    box: Optional[tuple] = None
    kind: str = "texto"
    x: float = 540.0


def text_timeline(scene) -> list[TextItem]:
    tip = scene.tipografia
    sz = tip.tamanos
    top = tip.margen_superior
    items: list[TextItem] = []
    dur = scene.general.duracion_seg
    # gancho
    hook_end = scene.etapas[0].inicio_seg
    for i, ln in enumerate(scene.gancho.lineas):
        if ln.texto.strip():
            items.append(TextItem(0.15 + i * 0.35, hook_end, ln.texto, int(sz.titulo * 1.15), hex_rgb(ln.color),
                                  560 + i * sz.titulo * 1.3, kind="gancho"))
    # títulos de etapas
    counter_h = (sz.contador * 1.15 + 50) if scene.contador.mostrar else 0
    ty = top + counter_h + sz.titulo * 0.6
    for e in scene.etapas:
        if e.tipo in CONSTRUCTION_EXCLUDE:
            continue
        if e.titulo.strip():
            items.append(TextItem(e.inicio_seg, e.fin_seg, e.titulo, sz.titulo, TITLE_COLOR, ty, kind="titulo"))
        if e.subtitulo.strip():
            items.append(TextItem(e.inicio_seg + 0.3, e.fin_seg, e.subtitulo, sz.subtitulo, SUB_COLOR,
                                  ty + sz.titulo * 0.62 + sz.subtitulo * 0.75, kind="subtitulo"))
    r = scene.revelacion
    preg = scene.first_stage("pregunta")
    rev = scene.first_stage("revelacion")
    ft = scene.flash_time
    big = int(sz.titulo * 1.1)
    if preg:
        end = ft if ft is not None else preg.fin_seg
        if r.texto_pregunta.strip():
            items.append(TextItem(preg.inicio_seg + 0.1, end, r.texto_pregunta, big, (255, 255, 255), top + 140, kind="pregunta"))
        if r.texto_falsa_expectativa.strip():
            items.append(TextItem(preg.inicio_seg + preg.duracion_seg * 0.5, end, r.texto_falsa_expectativa,
                                  int(sz.subtitulo * 1.1), SUB_COLOR, top + 140 + big * 0.9, anim="shake", kind="falsa"))
    if rev and ft is not None:
        if r.remate_1.strip():
            items.append(TextItem(ft, rev.fin_seg, r.remate_1, int(sz.titulo * 1.7), (255, 45, 70), top + 150, kind="remate"))
        if r.remate_2.strip():
            items.append(TextItem(ft + 0.7, rev.fin_seg, r.remate_2, big, (255, 255, 255), top + 150 + sz.titulo * 1.35, kind="remate"))
    cie = scene.first_stage("cierre")
    if cie and scene.cta.texto_cierre.strip():
        items.append(TextItem(cie.inicio_seg + 0.1, dur + 1, scene.cta.texto_cierre, big, (255, 255, 255), top + 150, kind="cierre"))
    c = scene.cta.final
    if c.texto.strip():
        y = {"arriba": top + 380, "centro": 960, "abajo": 1330}[c.posicion]
        items.append(TextItem(c.aparicion_seg, dur + 1, c.texto, int(sz.subtitulo * 1.15), hex_rgb(c.color_texto), y,
                              anim=c.animacion, box=hex_rgb(c.color_fondo), kind="cta"))
    ci = scene.cta.intermedio
    if ci.activo and ci.texto.strip():
        items.append(TextItem(ci.aparicion_seg, ci.aparicion_seg + ci.duracion_seg, ci.texto, int(sz.subtitulo * 1.05),
                              hex_rgb(ci.color_texto), 1250, anim="deslizar", box=hex_rgb(ci.color_fondo), kind="cta_intermedio"))
    return items


def callout_times(scene) -> list[float]:
    rev = scene.first_stage("revelacion")
    if rev is None:
        return []
    return [rev.inicio_seg + c.aparicion_seg for c in scene.revelacion.callouts]


class UI:
    def __init__(self, scene, out_w: int, out_h: int, fonts_dir: Optional[str] = None):
        self.s = scene
        self.w, self.h = out_w, out_h
        self.u = out_w / 1080.0
        self.font_path = resolve_font(scene.tipografia.fuente, fonts_dir)
        self.items = text_timeline(scene)
        self._grad = None

    def S(self, v: float) -> int:
        return int(round(v * self.u))

    def gradient(self) -> Image.Image:
        if self._grad is None:
            h = int(self.h * 0.32)
            a = (np.linspace(1, 0, h, dtype=np.float32) ** 1.4 * 170).astype(np.uint8)
            alpha = Image.fromarray(np.repeat(a[:, None], self.w, axis=1), "L")
            g = Image.new("RGBA", (self.w, h), (0, 0, 0, 255))
            g.putalpha(alpha)
            self._grad = g
        return self._grad

    def sprite(self, text, size, color, box=None, max_w=960):
        stroke = 0 if box else self.S(self.s.tipografia.contorno)
        return text_sprite(text, self.font_path, self.S(size), tuple(color), stroke, self.S(max_w), box)

    def paste_center(self, img: Image.Image, spr: Image.Image, cx: float, cy: float, scale: float = 1.0, alpha: float = 1.0):
        if scale <= 0.02 or alpha <= 0.02:
            return
        if abs(scale - 1) > 0.01:
            spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
        if alpha < 0.99:
            spr = spr.copy()
            spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
        x = int(cx - spr.width / 2)
        y = int(cy - spr.height / 2)
        _paste_clipped(img, spr, x, y)

    def draw_item(self, img, it: TextItem, t: float):
        age = t - it.t0
        if age < 0 or t >= it.t1:
            return
        spr = self.sprite(it.text, it.size, it.color, it.box)
        cx, cy = self.S(it.x), self.S(it.y)
        scale, alpha = 1.0, 1.0
        if it.anim == "pop" or it.anim == "shake":
            scale = 0.3 + 0.7 * ease_out_back(age / 0.28)
            alpha = min(1.0, age / 0.08)
            if it.anim == "shake" and age < 0.6:
                cx += math.sin(age * 60) * self.S(10) * (1 - age / 0.6)
        elif it.anim == "deslizar":
            k = ease_out_back(age / 0.4)
            cx = -spr.width / 2 + (cx + spr.width / 2) * k
        if it.box and age > 0.5:
            scale *= 1 + 0.03 * math.sin((age - 0.5) * 6)
        fade = min(1.0, (it.t1 - t) / 0.12) if it.kind not in ("cta", "cierre") else 1.0
        self.paste_center(img, spr, cx, cy, scale, alpha * fade)

    def counter(self, img, t: float):
        s = self.s
        c = s.contador
        idx, tl = s.stage_at(t)
        if idx < 0:
            return
        e = s.etapas[idx]
        if e.tipo in CONSTRUCTION_EXCLUDE:
            return
        day = int(round(e.dia_inicio + (e.dia_fin - e.dia_inicio) * tl))
        top = s.tipografia.margen_superior
        if c.mostrar:
            spr = self.sprite(f"{c.prefijo} {day}".strip(), s.tipografia.tamanos.contador, (255, 255, 255))
            self.paste_center(img, spr, self.w / 2, self.S(top + s.tipografia.tamanos.contador * 0.5))
        if c.barra:
            by = self.S(top + (s.tipografia.tamanos.contador * 1.15 if c.mostrar else 0))
            bw, bh = self.S(620), self.S(20)
            x0 = (self.w - bw) // 2
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((x0 - 3, by - 3, x0 + bw + 3, by + bh + 3), radius=bh, fill=(0, 0, 0, 200))
            frac = min(1.0, (e.dia_inicio + (e.dia_fin - e.dia_inicio) * tl) / c.dias_totales)
            if frac > 0:
                d.rounded_rectangle((x0, by, x0 + max(bh, int(bw * frac)), by + bh), radius=bh // 2, fill=hex_rgb(c.color_barra) + (255,))

    def callouts(self, img, t: float, anchors: list[tuple[float, float]], room_screen):
        s = self.s
        rev = s.first_stage("revelacion")
        if rev is None or s.flash_time is None or t < s.flash_time:
            return
        acc = hex_rgb(s.revelacion.color_acento)
        d = ImageDraw.Draw(img)
        rx0, ry0, rx1, ry1 = room_screen
        for i, (c, (ax, ay)) in enumerate(zip(s.revelacion.callouts, anchors)):
            t0 = rev.inicio_seg + c.aparicion_seg
            age = t - t0
            if age < 0:
                continue
            spr = self.sprite(c.texto, s.tipografia.tamanos.callout, (255, 255, 255), box=acc, max_w=520)
            above = i % 2 == 0
            ly = (ry0 - self.S(70) - (i // 2 % 2) * self.S(95)) if above else (ry1 + self.S(80) + (i // 2 % 2) * self.S(95))
            ly = max(self.S(560), min(self.h - self.S(420), ly))
            lx = max(spr.width / 2 + self.S(30), min(self.w - self.S(150) - spr.width / 2, ax))
            k = min(1.0, age / 0.25)
            if k > 0.2:
                ex = lx + (ax - lx) * k
                ey = ly + (ay - ly) * k
                d.line((lx, ly, ex, ey), fill=(255, 255, 255, 255), width=max(2, self.S(6)))
                r = self.S(12)
                d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=acc + (255,), outline=(255, 255, 255, 255), width=max(1, self.S(4)))
            scale = 0.3 + 0.7 * ease_out_back(age / 0.28)
            self.paste_center(img, spr, lx, ly, scale, min(1.0, age / 0.08))

    def safe_zones(self, img):
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        red = (255, 40, 60, 70)
        d.rectangle((0, 0, self.w, self.S(120)), fill=red)
        d.rectangle((self.w - self.S(140), self.S(620), self.w, self.h - self.S(380)), fill=red)
        d.rectangle((0, self.h - self.S(380), self.w, self.h), fill=red)
        f = font(str(FONTS["dejavu"]), self.S(26))
        d.text((self.S(20), self.h - self.S(360)), "ZONA TAPADA POR TIKTOK (solo vista previa)", font=f, fill=(255, 255, 255, 200))
        img.alpha_composite(ov)

    def draw(self, img: Image.Image, t: float, anchors=(), room_screen=(0, 0, 0, 0), preview=False):
        img.alpha_composite(self.gradient(), (0, 0))
        self.counter(img, t)
        self.callouts(img, t, list(anchors), room_screen)
        for it in self.items:
            self.draw_item(img, it, t)
        if preview and self.s.tipografia.guia_zonas_seguras:
            self.safe_zones(img)


def _paste_clipped(img: Image.Image, spr: Image.Image, x: int, y: int):
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(spr.width, img.width - x), min(spr.height, img.height - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    img.alpha_composite(spr.crop((sx0, sy0, sx1, sy1)), (x + sx0, y + sy0))
