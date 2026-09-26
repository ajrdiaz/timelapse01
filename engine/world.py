"""Geometría del mundo (metros → píxeles) y utilidades de dibujo por rectángulos/polígonos."""
from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

WALL_T = 0.25
SLAB_T = 0.25
ROOF_T = 0.25
GRAVEL_T = 0.15
OVERDIG = 0.55  # espacio de trabajo a cada lado del búnker
COAT_T = 0.06  # impermeabilizante
WORKER_H = 1.75  # altura de un obrero en metros: referencia de escala


@dataclass
class Layout:
    W: int
    H: int
    ppm: float
    ground_y: float
    bx0: float
    bx1: float
    ix0: float
    ix1: float
    roof_top_y: float
    roof_bot_y: float
    floor_y: float
    slab_bot_y: float
    pit_bot_y: float
    pit_x0: float
    pit_x1: float
    hatch_x0: float
    hatch_x1: float
    vent_x: float

    def m(self, v: float) -> float:
        return v * self.ppm

    @property
    def pit_depth(self) -> float:
        return self.pit_bot_y - self.ground_y

    @property
    def cx(self) -> float:
        return (self.bx0 + self.bx1) / 2

    @property
    def room(self) -> tuple[float, float, float, float]:
        return self.ix0, self.roof_bot_y, self.ix1, self.floor_y


def make_layout(esc, W: int, H: int) -> Layout:
    """esc: modelo Escenario. W,H: tamaño del lienzo del mundo en px."""
    view_w = max(10.0, esc.ancho_m + 2 * WALL_T + 2 * OVERDIG + 3.2)
    ppm = W / view_w
    depth_m = esc.profundidad_m + ROOF_T + esc.alto_m + SLAB_T + GRAVEL_T
    ground_y = H * 0.80 - depth_m * ppm
    ground_y = max(H * 0.42, ground_y)
    cx = W * 0.47
    half = (esc.ancho_m / 2 + WALL_T) * ppm
    bx0, bx1 = cx - half, cx + half
    ix0, ix1 = bx0 + WALL_T * ppm, bx1 - WALL_T * ppm
    roof_top = ground_y + esc.profundidad_m * ppm
    roof_bot = roof_top + ROOF_T * ppm
    floor_y = roof_bot + esc.alto_m * ppm
    slab_bot = floor_y + SLAB_T * ppm
    pit_bot = slab_bot + GRAVEL_T * ppm
    hatch_w = 0.8 * ppm
    hatch_x1 = ix1 - 0.5 * ppm
    return Layout(
        W=W, H=H, ppm=ppm, ground_y=ground_y,
        bx0=bx0, bx1=bx1, ix0=ix0, ix1=ix1,
        roof_top_y=roof_top, roof_bot_y=roof_bot, floor_y=floor_y,
        slab_bot_y=slab_bot, pit_bot_y=pit_bot,
        pit_x0=bx0 - OVERDIG * ppm, pit_x1=bx1 + OVERDIG * ppm,
        hatch_x0=hatch_x1 - hatch_w, hatch_x1=hatch_x1,
        vent_x=ix0 + 0.7 * ppm,
    )


# --- utilidades de dibujo ----------------------------------------------------
def ibox(box, W: int, H: int):
    x0, y0, x1, y1 = box
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    b = (max(0, int(round(x0))), max(0, int(round(y0))), min(W, int(round(x1))), min(H, int(round(y1))))
    if b[2] <= b[0] or b[3] <= b[1]:
        return None
    return b


def paste_rect(canvas: Image.Image, tex: Image.Image, box) -> None:
    """Pega la región `box` de la textura (alineada al mundo) en el lienzo."""
    b = ibox(box, canvas.width, canvas.height)
    if b is None:
        return
    region = tex.crop(b)
    if region.mode == "RGBA":
        canvas.alpha_composite(region, (b[0], b[1]))
    else:
        canvas.paste(region, b[:2])


def paste_poly(canvas: Image.Image, tex: Image.Image, pts) -> None:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    b = ibox((min(xs), min(ys), max(xs) + 1, max(ys) + 1), canvas.width, canvas.height)
    if b is None:
        return
    mask = Image.new("L", (b[2] - b[0], b[3] - b[1]), 0)
    ImageDraw.Draw(mask).polygon([(x - b[0], y - b[1]) for x, y in pts], fill=255)
    region = tex.crop(b)
    if region.mode == "RGBA":
        a = region.getchannel("A")
        from PIL import ImageChops

        mask = ImageChops.multiply(mask, a)
        region = region.convert("RGB")
    canvas.paste(region, b[:2], mask)


def paste_mask(canvas: Image.Image, tex: Image.Image, mask: Image.Image, box) -> None:
    """Pega la textura usando una máscara L del tamaño del lienzo, restringida a `box`."""
    b = ibox(box, canvas.width, canvas.height)
    if b is None:
        return
    canvas.paste(tex.crop(b).convert("RGB"), b[:2], mask.crop(b))


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def seg(t: float, a: float, b: float) -> float:
    """Progreso 0..1 de t dentro del sub-intervalo [a, b]."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return max(0.0, min(1.0, (t - a) / (b - a)))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def shade(c, k: float):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def mix(a, b, t: float):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def rot(px: float, py: float, ang: float, ox: float = 0, oy: float = 0):
    c, s = math.cos(ang), math.sin(ang)
    return ox + px * c - py * s, oy + px * s + py * c


class SafeDraw(ImageDraw.ImageDraw):
    """ImageDraw que tolera cajas invertidas o degeneradas (útil a escalas pequeñas)."""

    @staticmethod
    def _box(xy):
        if len(xy) == 4 and not isinstance(xy[0], (tuple, list)):
            x0, y0, x1, y1 = xy
        else:
            (x0, y0), (x1, y1) = xy
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        return (x0, y0, max(x1, x0 + 1), max(y1, y0 + 1))

    def ellipse(self, xy, *a, **k):
        return super().ellipse(self._box(xy), *a, **k)

    def rectangle(self, xy, *a, **k):
        return super().rectangle(self._box(xy), *a, **k)

    def rounded_rectangle(self, xy, radius=0, *a, **k):
        b = self._box(xy)
        radius = max(0, min(radius, (b[2] - b[0]) / 2, (b[3] - b[1]) / 2))
        return super().rounded_rectangle(b, radius, *a, **k)

    def pieslice(self, xy, *a, **k):
        return super().pieslice(self._box(xy), *a, **k)

    def line(self, xy, fill=None, width=0, joint=None):
        return super().line(xy, fill, max(1, int(width)), joint)


def Draw(im):
    return SafeDraw(im)
