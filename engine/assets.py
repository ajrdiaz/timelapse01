"""Texturas procedurales, cacheadas en disco por hash de parámetros.

Todas las texturas "de mundo" tienen el tamaño del lienzo y están alineadas a coordenadas de
mundo, de modo que se pegan por rectángulos (crop + paste) sin costuras.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from engine.world import Layout, hex_rgb, mix, shade

CACHE_DIR = Path(os.environ.get("TF_CACHE_DIR", Path(__file__).resolve().parent.parent / ".cache" / "assets"))
ASSET_VERSION = 4


def _key(name: str, params: dict) -> str:
    raw = json.dumps({"n": name, "v": ASSET_VERSION, **params}, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def cached(name: str, params: dict, fn, mode: str = "RGB") -> Image.Image:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}_{_key(name, params)}.png"
    if path.exists():
        try:
            im = Image.open(path)
            im.load()
            return im.convert(mode)
        except Exception:
            pass
    im = fn().convert(mode)
    tmp = path.with_suffix(f".{os.getpid()}.tmp.png")
    im.save(tmp, compress_level=1)
    os.replace(tmp, path)
    return im


# --- ruido --------------------------------------------------------------------
def fbm(w: int, h: int, seed: int, base: int = 64, octaves: int = 4, aspect: float = 1.0) -> np.ndarray:
    """Ruido fractal 0..1 por suma de ruido blanco reescalado (rápido y determinista)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    cell = base
    for _ in range(octaves):
        gw = max(2, int(w / cell) + 2)
        gh = max(2, int(h / (cell * aspect)) + 2)
        g = rng.random((gh, gw), dtype=np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += np.asarray(im, np.float32) / 255.0 * amp
        tot += amp
        amp *= 0.5
        cell = max(2, cell // 2)
    return acc / tot


def _tint(noise: np.ndarray, color, contrast: float) -> np.ndarray:
    c = np.array(color, np.float32)
    k = 1.0 + (noise[..., None] - 0.5) * contrast
    return np.clip(c * k, 0, 255)


def _stones(img: Image.Image, rng: np.random.Generator, count: int, rmin: float, rmax: float, base, box=None):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box or (0, 0, img.width, img.height)
    for _ in range(count):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        r = rng.uniform(rmin, rmax)
        k = rng.uniform(0.75, 1.25)
        col = shade(base, k)
        ry = r * rng.uniform(0.55, 0.9)
        d.ellipse((x - r, y - ry, x + r, y + ry), fill=col)
        d.ellipse((x - r * 0.5, y - ry * 0.7, x + r * 0.1, y - ry * 0.1), fill=shade(col, 1.18))


class Assets:
    """Conjunto de texturas para un layout + escena concretos."""

    def __init__(self, L: Layout, scene):
        self.L = L
        self.scene = scene
        esc = scene.escenario
        self.seed = scene.general.seed
        self.cols = [hex_rgb(c) for c in esc.colores_suelo]
        self.p = {"W": L.W, "H": L.H, "ppm": round(L.ppm, 3), "gy": round(L.ground_y, 1), "seed": self.seed}
        self._c: dict[str, Image.Image] = {}

    def __getattr__(self, name: str) -> Image.Image:
        if name.startswith("_") or name in ("L", "scene", "seed", "cols", "p"):
            raise AttributeError(name)
        if name not in self._c:
            self._c[name] = getattr(self, "_make_" + name)()
        return self._c[name]

    # suelo -------------------------------------------------------------------
    def _make_suelo(self):
        esc = self.scene.escenario
        params = dict(self.p, cols=esc.colores_suelo, dens=esc.densidad_piedras)
        return cached("suelo", params, self._gen_suelo)

    def _gen_suelo(self):
        L = self.L
        W, H = L.W, L.H
        rng = np.random.default_rng(self.seed + 11)
        n = fbm(W, H, self.seed + 1, base=int(L.ppm * 0.6), octaves=5)
        fine = fbm(W, H, self.seed + 2, base=6, octaves=2)
        ys = np.arange(H, dtype=np.float32)[:, None]
        wob = (fbm(W, 8, self.seed + 3, base=int(L.ppm), octaves=2)[0][None, :] - 0.5) * L.ppm * 0.5
        b1 = L.ground_y + L.ppm * 1.1 + wob
        b2 = L.ground_y + L.ppm * 2.9 + wob * 1.4
        c0, c1, c2 = (np.array(c, np.float32) for c in self.cols)
        t1 = np.clip((ys - b1) / (L.ppm * 0.25) + 0.5, 0, 1)[..., None]
        t2 = np.clip((ys - b2) / (L.ppm * 0.25) + 0.5, 0, 1)[..., None]
        base = c0 * (1 - t1) + c1 * t1
        base = base * (1 - t2) + c2 * t2
        k = 1.0 + (n[..., None] - 0.5) * 0.35 + (fine[..., None] - 0.5) * 0.16
        arr = np.clip(base * k, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, "RGB")
        dens = self.scene.escenario.densidad_piedras
        area_m2 = (W / L.ppm) * ((H - L.ground_y) / L.ppm)
        count = int(area_m2 * 6 * dens)
        _stones(img, rng, count, L.ppm * 0.03, L.ppm * 0.09, mix(self.cols[1], (130, 124, 116), 0.55), (0, L.ground_y + L.ppm * 0.2, W, H))
        return img

    def _make_pozo(self):
        """Pared trasera del pozo: tierra más oscura con estrías de la cuchara."""
        return cached("pozo", dict(self.p, cols=self.scene.escenario.colores_suelo), self._gen_pozo)

    def _gen_pozo(self):
        L = self.L
        arr = np.asarray(self.suelo, np.float32) * 0.66
        streak = fbm(L.W, L.H, self.seed + 5, base=int(L.ppm * 0.25), octaves=2, aspect=6.0)
        arr *= (0.85 + streak[..., None] * 0.3)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def _make_relleno(self):
        return cached("relleno", dict(self.p, cols=self.scene.escenario.colores_suelo), self._gen_relleno)

    def _gen_relleno(self):
        L = self.L
        n = fbm(L.W, L.H, self.seed + 21, base=int(L.ppm * 0.15), octaves=4)
        c = mix(self.cols[0], self.cols[1], 0.5)
        arr = _tint(n, shade(c, 1.07), 0.7)
        speck = np.random.default_rng(self.seed + 22).random((L.H, L.W)) > 0.985
        arr[speck] *= 0.6
        return Image.fromarray(arr.astype(np.uint8))

    def _make_grava(self):
        return cached("grava", self.p, self._gen_grava)

    def _gen_grava(self):
        L = self.L
        img = Image.new("RGB", (L.W, L.H), (105, 104, 100))
        rng = np.random.default_rng(self.seed + 31)
        y0 = L.slab_bot_y - L.ppm * 0.1
        y1 = L.pit_bot_y + L.ppm * 0.1
        count = int((L.W / L.ppm) * 900 * (y1 - y0) / L.ppm)
        _stones(img, rng, count, L.ppm * 0.012, L.ppm * 0.035, (150, 148, 140), (0, y0, L.W, y1))
        return img

    def _make_concreto(self):
        return cached("concreto", self.p, lambda: self._gen_concreto(False))

    def _make_concreto_encofrado(self):
        return cached("concreto_enc", self.p, lambda: self._gen_concreto(True))

    def _gen_concreto(self, marks: bool):
        L = self.L
        n = fbm(L.W, L.H, self.seed + (41 if marks else 40), base=int(L.ppm * 0.4), octaves=5)
        arr = _tint(n, (168, 168, 162), 0.22)
        rng = np.random.default_rng(self.seed + 42)
        pores = rng.random((L.H, L.W)) > 0.994
        arr[pores] *= 0.7
        img = Image.fromarray(arr.astype(np.uint8))
        if marks:
            d = ImageDraw.Draw(img)
            step = L.ppm * 0.2
            y = L.ground_y - L.ppm * 2
            while y < L.H:
                d.line((0, y, L.W, y), fill=(142, 142, 137), width=max(1, int(L.ppm * 0.012)))
                y += step
            # orificios de los tensores
            for yy in np.arange(L.ground_y, L.H, L.ppm * 0.6):
                for xx in np.arange(0, L.W, L.ppm * 0.6):
                    r = L.ppm * 0.018
                    d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(120, 120, 116))
        return img

    def _make_madera(self):
        return cached("madera", self.p, self._gen_madera)

    def _gen_madera(self):
        L = self.L
        grain = fbm(L.W, L.H, self.seed + 51, base=int(L.ppm * 0.3), octaves=3, aspect=0.08)
        arr = _tint(grain, (196, 140, 82), 0.45)
        img = Image.fromarray(arr.astype(np.uint8))
        d = ImageDraw.Draw(img)
        step = L.ppm * 0.2
        y = 0.0
        while y < L.H:
            d.line((0, y, L.W, y), fill=(120, 80, 42), width=max(1, int(L.ppm * 0.015)))
            y += step
        return img

    def _make_pasto(self):
        """Franja de pasto RGBA alineada a ground_y (hojas por encima y tierra con raíces debajo)."""
        return cached("pasto", self.p, self._gen_pasto, mode="RGBA")

    def _gen_pasto(self):
        L = self.L
        img = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        rng = np.random.default_rng(self.seed + 61)
        g = L.ground_y
        thick = L.ppm * 0.14
        n = fbm(L.W, 16, self.seed + 62, base=12, octaves=2)[0]
        for x in range(L.W):
            k = 0.85 + n[x] * 0.3
            d.line((x, g - 2, x, g + thick), fill=shade((64, 150, 52), k) + (255,))
        blade_h = L.ppm * 0.16
        for _ in range(int(L.W * 1.6)):
            x = rng.uniform(0, L.W)
            h = blade_h * rng.uniform(0.4, 1.0)
            lean = rng.uniform(-0.3, 0.3) * h
            col = shade((78, 170, 60), rng.uniform(0.75, 1.2)) + (255,)
            d.line((x, g + 2, x + lean, g - h), fill=col, width=max(1, int(L.ppm * 0.012)))
        return img

    # cielos (a resolución de salida: se componen tras la cámara) ---------------
    def sky(self, kind: str, w: int, h: int) -> Image.Image:
        key = f"sky_{kind}_{w}x{h}"
        if key not in self._c:
            self._c[key] = cached("sky_" + kind, {"w": w, "h": h, "seed": self.seed}, lambda: self._gen_sky(kind, w, h))
        return self._c[key]

    def _gen_sky(self, kind, w, h):
        top, bot = {
            "dia": ((70, 150, 230), (180, 222, 250)),
            "atardecer": ((70, 60, 140), (255, 150, 90)),
            "noche": ((6, 10, 30), (30, 40, 80)),
        }[kind]
        ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        arr = np.array(top, np.float32) * (1 - ys) + np.array(bot, np.float32) * ys
        arr = np.repeat(arr, w, axis=1)
        if kind == "noche":
            rng = np.random.default_rng(self.seed + 71)
            for _ in range(int(w * h / 2500)):
                x, y = rng.integers(0, w), rng.integers(0, int(h * 0.6))
                b = rng.uniform(150, 255)
                arr[y, x] = (b, b, b)
                if rng.random() < 0.15 and x + 1 < w and y + 1 < h:
                    arr[y + 1, x] = arr[y, x + 1] = (b * 0.7,) * 3
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def sprite(self, kind: str, size: int) -> Image.Image:
        key = f"sprite_{kind}_{size}"
        if key not in self._c:
            self._c[key] = cached("sprite_" + kind, {"s": size, "seed": self.seed}, lambda: self._gen_sprite(kind, size), "RGBA")
        return self._c[key]

    def _gen_sprite(self, kind, s):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if kind == "sol":
            for i in range(12, 0, -1):
                r = s / 2 * i / 12
                a = int(255 * (1 - i / 12) ** 1.5) if i > 5 else 255
                c = (255, 236, 150, a) if i > 5 else (255, 245, 190, 255)
                d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=c)
        elif kind == "luna":
            r = s * 0.3
            glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((s / 2 - r * 1.6,) * 2 + (s / 2 + r * 1.6,) * 2, fill=(200, 210, 255, 60))
            img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.08)))
            d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=(235, 238, 250, 255))
            for (ox, oy, rr) in ((-0.3, -0.2, 0.22), (0.25, 0.1, 0.16), (-0.05, 0.35, 0.12)):
                cx, cy = s / 2 + ox * r, s / 2 + oy * r
                d.ellipse((cx - rr * r, cy - rr * r, cx + rr * r, cy + rr * r), fill=(205, 208, 225, 255))
        elif kind.startswith("nube"):
            rng = np.random.default_rng(self.seed + zlib.crc32(kind.encode()) % 1000)
            h = int(s * 0.45)
            img = Image.new("RGBA", (s, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            for _ in range(7):
                r = rng.uniform(0.12, 0.22) * s
                x = rng.uniform(0.25, 0.75) * s
                y = h * 0.62 - rng.uniform(0, 0.25) * h
                d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(255, 255, 255, 235))
            d.rectangle((s * 0.18, h * 0.6, s * 0.82, h * 0.78), fill=(255, 255, 255, 235))
            img = img.filter(ImageFilter.GaussianBlur(max(1, s * 0.01)))
        return img

    # fondo --------------------------------------------------------------------
    def _make_fondo(self):
        f = self.scene.escenario.fondo
        return cached("fondo", dict(self.p, c=f.cerca, a=f.arbol, v=f.casa_vecino), self._gen_fondo, "RGBA")

    def _gen_fondo(self):
        L = self.L
        f = self.scene.escenario.fondo
        img = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        g = L.ground_y
        m = L.m
        # colinas lejanas
        pts = [(0, g)]
        for i in range(0, 41):
            x = L.W * i / 40
            y = g - m(1.2) - math.sin(i * 0.45 + self.seed) * m(0.35) - math.sin(i * 0.17) * m(0.5)
            pts.append((x, y))
        pts.append((L.W, g))
        d.polygon(pts, fill=(118, 170, 110, 255))
        if f.casa_vecino:
            hx0, hx1 = m(0.2), m(4.6)
            hy = g - m(3.3)
            d.rectangle((hx0, hy, hx1, g), fill=(222, 206, 176, 255))
            d.polygon([(hx0 - m(0.3), hy), ((hx0 + hx1) / 2, hy - m(1.8)), (hx1 + m(0.3), hy)], fill=(160, 70, 60, 255))
            for wx in (hx0 + m(0.6), hx0 + m(2.6)):
                d.rectangle((wx, hy + m(0.7), wx + m(1.0), hy + m(1.7)), fill=(120, 170, 210, 255), outline=(250, 250, 250, 255), width=max(2, int(m(0.06))))
                d.line((wx + m(0.5), hy + m(0.7), wx + m(0.5), hy + m(1.7)), fill=(250, 250, 250, 255), width=max(2, int(m(0.04))))
            d.rectangle((hx1 - m(1.2), hy + m(1.2), hx1 - m(0.4), g), fill=(120, 80, 50, 255))
        if f.arbol:
            tx = L.W - m(1.8)
            d.rectangle((tx - m(0.18), g - m(3.0), tx + m(0.18), g), fill=(110, 76, 46, 255))
            rng = np.random.default_rng(self.seed + 81)
            for _ in range(14):
                r = m(rng.uniform(0.6, 1.0))
                x = tx + m(rng.uniform(-1.1, 1.1))
                y = g - m(3.4) + m(rng.uniform(-1.0, 0.8))
                d.ellipse((x - r, y - r, x + r, y + r), fill=shade((60, 140, 60), rng.uniform(0.8, 1.15)) + (255,))
        if f.cerca:
            fy = g - m(1.3)
            d.rectangle((0, fy + m(0.25), L.W, fy + m(0.38)), fill=(170, 120, 75, 255))
            d.rectangle((0, fy + m(0.85), L.W, fy + m(0.98)), fill=(170, 120, 75, 255))
            x = 0.0
            while x < L.W:
                d.polygon([(x, g), (x, fy + m(0.1)), (x + m(0.09), fy), (x + m(0.18), fy + m(0.1)), (x + m(0.18), g)], fill=(196, 146, 96, 255))
                d.line((x, fy + m(0.1), x, g), fill=(150, 104, 62, 255), width=max(1, int(m(0.015))))
                x += m(0.22)
        return img
