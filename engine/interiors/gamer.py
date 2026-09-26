import math

from engine.interiors.base import Interior, register
from engine.world import mix, shade


@register
class Gamer(Interior):
    tipo = "gamer"
    OBJECTS = {
        "monitores": ("Monitores", 0.4, 1.05),
        "escritorio": ("Escritorio", 0.36, 0.72),
        "silla": ("Silla gamer", 0.56, 0.9),
        "pc": ("PC gamer", 0.66, 0.45),
        "leds": ("Tiras LED", 0.2, 2.45),
        "poster": ("Póster", 0.1, 1.6),
        "puff": ("Puff", 0.1, 0.3),
        "minirefri": ("Mini refri", 0.74, 0.4),
    }
    wall = (34, 30, 48)

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        acc = self.acc
        # póster
        px = X(0.1)
        d.rectangle((px - m(0.35), FY(2.05), px + m(0.35), FY(1.15)), fill=(250, 250, 250))
        d.rectangle((px - m(0.31), FY(2.01), px + m(0.31), FY(1.19)), fill=mix(acc, (0, 0, 0), 0.3))
        d.polygon([(px - m(0.2), FY(1.3)), (px, FY(1.85)), (px + m(0.2), FY(1.3))], fill=self.led)
        # puff
        d.ellipse((X(0.1) - m(0.45), FY(0.6), X(0.1) + m(0.45), FY(0.0)), fill=shade(acc, 0.9))
        d.ellipse((X(0.1) - m(0.3), FY(0.55), X(0.1) + m(0.1), FY(0.4)), fill=shade(acc, 1.2))
        # escritorio
        dx0, dx1 = X(0.2), X(0.6)
        d.rectangle((dx0, FY(0.78), dx1, FY(0.7)), fill=(24, 24, 28))
        d.rectangle((dx0 + m(0.05), FY(0.7), dx0 + m(0.12), FY(0)), fill=(24, 24, 28))
        d.rectangle((dx1 - m(0.12), FY(0.7), dx1 - m(0.05), FY(0)), fill=(24, 24, 28))
        d.rectangle((dx0, FY(0.705), dx1, FY(0.69)), fill=acc)
        # monitores
        for i, rx in enumerate((0.3, 0.4, 0.5)):
            self.monitor(d, X(rx), FY(0.78), m(0.6), m(0.36), t, i)
        # teclado + ratón con RGB
        d.rectangle((X(0.34), FY(0.82), X(0.44), FY(0.78)), fill=self.led)
        d.ellipse((X(0.46), FY(0.82), X(0.47), FY(0.78)), fill=acc)
        # silla gamer (de espaldas a la cámara, girada)
        sx = X(0.56)
        d.rounded_rectangle((sx - m(0.28), FY(1.45), sx + m(0.28), FY(0.55)), radius=m(0.12), fill=(28, 28, 32))
        d.rounded_rectangle((sx - m(0.2), FY(1.35), sx + m(0.2), FY(0.65)), radius=m(0.1), fill=acc)
        d.rectangle((sx - m(0.32), FY(0.6), sx + m(0.32), FY(0.48)), fill=(28, 28, 32))
        d.rectangle((sx - m(0.03), FY(0.48), sx + m(0.03), FY(0.12)), fill=(80, 80, 88))
        for k in (-1, 0, 1):
            d.line((sx, FY(0.12), sx + k * m(0.3), FY(0.03)), fill=(60, 60, 66), width=max(2, int(m(0.04))))
        # torre PC con ventiladores
        pcx = X(0.66)
        d.rectangle((pcx - m(0.22), FY(0.7), pcx + m(0.22), FY(0)), fill=(20, 20, 24))
        d.rectangle((pcx - m(0.18), FY(0.66), pcx + m(0.18), FY(0.04)), fill=(40, 40, 60))
        for j, h in enumerate((0.52, 0.34, 0.16)):
            c = self.led if (int(t * 4) + j) % 2 else acc
            r = m(0.07)
            d.ellipse((pcx - r, FY(h) - r, pcx + r, FY(h) + r), outline=c, width=max(2, int(m(0.025))))
        # mini refri
        fx = X(0.74)
        d.rounded_rectangle((fx - m(0.25), FY(0.85), fx + m(0.25), FY(0)), radius=m(0.04), fill=(235, 235, 240))
        d.rectangle((fx - m(0.2), FY(0.78), fx + m(0.2), FY(0.08)), fill=(170, 220, 240))
        for j in range(3):
            for k in range(3):
                cx = fx - m(0.13) + k * m(0.13)
                cy = FY(0.2 + j * 0.2)
                d.rectangle((cx - m(0.04), cy - m(0.07), cx + m(0.04), cy + m(0.05)), fill=(40, 200, 90) if (j + k) % 2 else (230, 40, 60))

    def screens(self, d, t):
        X, FY, m = self.X, self.FY, self.m
        return [((X(rx) - m(0.3), FY(0.78) - m(0.12) - m(0.36), X(rx) + m(0.3), FY(0.78) - m(0.12)), self.acc) for rx in (0.3, 0.4, 0.5)]
