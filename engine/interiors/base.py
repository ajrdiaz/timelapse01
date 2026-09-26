"""Base de interiores. Cada interior declara OBJECTS = {id: (etiqueta, rx, h)}: rx es la posición
horizontal relativa al ancho de la habitación (0..1) y h la altura en metros sobre el piso.
Los callouts apuntan a esos puntos y los muebles se dibujan con las mismas coordenadas."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from engine.world import Draw, hex_rgb, ibox, mix, shade

INTERIORS: dict[str, "Interior"] = {}


def register(cls):
    INTERIORS[cls.tipo] = cls()
    return cls


class Interior:
    tipo = "base"
    OBJECTS: dict[str, tuple[str, float, float]] = {}
    wall = (40, 36, 52)
    floor = (58, 46, 40)
    led_on_ceiling = True
    warm = False

    # coordenadas --------------------------------------------------------------
    def setup(self, ctx):
        L = ctx.L
        self.L = L
        self.x0, self.y0, self.x1, self.y1 = L.room
        self.rw = self.x1 - self.x0
        self.rh = self.y1 - self.y0
        self.m = L.m
        r = ctx.scene.revelacion
        self.acc = hex_rgb(r.color_acento)
        self.led = hex_rgb(r.color_leds)

    def X(self, rx: float) -> float:
        return self.x0 + rx * self.rw

    def Y(self, ry: float) -> float:
        return self.y0 + ry * self.rh

    def FY(self, meters_above_floor: float) -> float:
        return self.y1 - self.m(meters_above_floor)

    def anchor(self, obj: str, ctx) -> tuple[float, float]:
        """Punto de mundo (px) al que apunta un callout."""
        self.setup(ctx)
        _, rx, h = self.OBJECTS[obj]
        return self.X(rx), self.FY(h)

    # dibujo --------------------------------------------------------------------
    def draw(self, canvas: Image.Image, ctx, t: float) -> None:
        self.setup(ctx)
        d = Draw(canvas)
        self.background(canvas, d, ctx)
        self.furniture(canvas, d, ctx, t)
        self.ladder(d)
        self.glow(canvas, ctx, t)

    def background(self, canvas, d, ctx):
        m = self.m
        wall = mix(self.wall, self.acc, 0.12)
        d.rectangle((self.x0, self.y0, self.x1, self.y1), fill=wall)
        # paneles de pared
        step = m(0.8)
        x = self.x0 + step
        while x < self.x1:
            d.line((x, self.y0, x, self.y1 - m(0.1)), fill=shade(wall, 0.85), width=max(1, int(m(0.02))))
            x += step
        d.rectangle((self.x0, self.y1 - m(0.12), self.x1, self.y1), fill=self.floor)
        d.rectangle((self.x0, self.y1 - m(0.14), self.x1, self.y1 - m(0.12)), fill=shade(self.floor, 1.4))

    def ladder(self, d):
        from engine.stages.techo import draw_ladder

        L = self.L
        draw_ladder(d, L, L.hatch_x0, L.hatch_x1, L.roof_top_y, L.floor_y)

    def furniture(self, canvas, d, ctx, t):
        pass

    def led_strips(self, d, color, width):
        m = self.m
        if self.led_on_ceiling:
            d.rectangle((self.x0, self.y0, self.x1, self.y0 + width), fill=color)
        d.rectangle((self.x0, self.y1 - m(0.16) - width, self.x1, self.y1 - m(0.16)), fill=color)

    def screens(self, d, t):
        """Zonas brillantes adicionales para el resplandor (sobrescribir)."""
        return []

    def glow(self, canvas, ctx, t):
        """Tiras LED con resplandor; el halo borroso se cachea y se modula por pulso."""
        m = self.m
        b = ibox((self.x0, self.y0, self.x1, self.y1), canvas.width, canvas.height)
        if b is None:
            return
        key = ("glow", self.tipo, b, self.led)
        cache = ctx.draw_cache
        if key not in cache:
            lay = Image.new("RGBA", (b[2] - b[0], b[3] - b[1]), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ox, oy = b[0], b[1]
            w = max(2, int(m(0.05)))
            ld.rectangle((0, 0, lay.width, w * 1.5), fill=self.led + (255,))
            ld.rectangle((0, lay.height - m(0.16) - w, lay.width, lay.height - m(0.16)), fill=self.led + (255,))
            for (a, bb, c, dd), col in self.screens(ld, 0):
                ld.rectangle((a - ox, bb - oy, c - ox, dd - oy), fill=col + (200,))
            halo = lay.filter(ImageFilter.GaussianBlur(m(0.22)))
            cache[key] = (halo, lay)
        halo, core = cache[key]
        pulse = 0.75 + 0.25 * math.sin(t * 5.0)
        a = halo.getchannel("A").point(lambda v, p=pulse: int(min(255, v * 1.6 * p)))
        h2 = halo.copy()
        h2.putalpha(a)
        canvas.alpha_composite(h2, b[:2])
        canvas.alpha_composite(core, b[:2])

    # helpers de muebles -------------------------------------------------------
    def monitor(self, d, cx, bottom, w, h, t, seed=0):
        m = self.m
        d.rectangle((cx - m(0.03), bottom - m(0.12), cx + m(0.03), bottom), fill=(30, 30, 34))
        d.rectangle((cx - m(0.12), bottom - m(0.02), cx + m(0.12), bottom), fill=(30, 30, 34))
        box = (cx - w / 2, bottom - m(0.12) - h, cx + w / 2, bottom - m(0.12))
        d.rectangle(box, fill=(18, 18, 22))
        inner = (box[0] + m(0.03), box[1] + m(0.03), box[2] - m(0.03), box[3] - m(0.03))
        col_a = mix(self.acc, (20, 20, 60), 0.3)
        col_b = mix(self.led, (255, 255, 255), 0.2)
        d.rectangle(inner, fill=col_a)
        k = (math.sin(t * 2 + seed) + 1) / 2
        hy = inner[1] + (inner[3] - inner[1]) * (0.55 + 0.15 * k)
        d.polygon([(inner[0], inner[3]), (inner[0], hy), ((inner[0] + inner[2]) / 2, hy - m(0.08)), (inner[2], hy + m(0.02)), (inner[2], inner[3])], fill=col_b)
        return box
