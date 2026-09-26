import math

from engine.interiors.base import Interior, register
from engine.world import shade


@register
class Oficina(Interior):
    tipo = "oficina"
    OBJECTS = {
        "escritorio": ("Escritorio", 0.42, 0.75),
        "librero": ("Librero", 0.1, 1.4),
        "lampara": ("Lámpara", 0.53, 1.25),
        "planta": ("Planta", 0.7, 0.8),
        "pizarra": ("Pizarra", 0.4, 1.7),
        "silla": ("Silla ergonómica", 0.36, 0.9),
    }
    wall = (72, 66, 58)
    floor = (120, 84, 52)

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        wood = (140, 94, 56)
        # librero
        b0, b1 = X(0.02), X(0.2)
        d.rectangle((b0, FY(2.2), b1, FY(0)), fill=shade(wood, 0.8))
        cols = [(180, 40, 40), (40, 90, 160), (220, 180, 60), (60, 130, 70), (230, 230, 220)]
        for i in range(5):
            y = FY(0.1 + i * 0.42)
            d.rectangle((b0, y - m(0.03), b1, y), fill=wood)
            x = b0 + m(0.05)
            k = 0
            while x < b1 - m(0.1):
                w = m(0.05 + 0.02 * ((i + k) % 3))
                d.rectangle((x, y - m(0.3 + 0.04 * ((k + i) % 2)), x + w, y - m(0.03)), fill=cols[(i + k) % 5])
                x += w + m(0.01)
                k += 1
        # pizarra
        d.rectangle((X(0.28), FY(2.1), X(0.52), FY(1.35)), fill=(250, 250, 250), outline=(160, 160, 160), width=max(2, int(m(0.03))))
        d.line((X(0.3), FY(1.6), X(0.36), FY(1.8), X(0.42), FY(1.7), X(0.5), FY(1.95)), fill=self.acc, width=max(2, int(m(0.03))))
        # escritorio de madera
        d.rectangle((X(0.25), FY(0.78), X(0.6), FY(0.7)), fill=wood)
        d.rectangle((X(0.47), FY(0.7), X(0.6), FY(0)), fill=shade(wood, 0.85))
        d.rectangle((X(0.26), FY(0.7), X(0.27), FY(0)), fill=shade(wood, 0.7))
        self.monitor(d, X(0.42), FY(0.78), m(0.55), m(0.33), t)
        # lámpara
        lx = X(0.55)
        d.line((lx, FY(0.78), lx - m(0.05), FY(1.1), lx - m(0.15), FY(1.2)), fill=(30, 30, 30), width=max(2, int(m(0.025))))
        d.polygon([(lx - m(0.25), FY(1.1)), (lx - m(0.05), FY(1.1)), (lx - m(0.1), FY(1.25)), (lx - m(0.2), FY(1.25))], fill=self.acc)
        # silla
        sx = X(0.36)
        d.rounded_rectangle((sx - m(0.2), FY(1.25), sx + m(0.2), FY(0.55)), radius=m(0.08), fill=(40, 40, 44))
        d.rectangle((sx - m(0.03), FY(0.55), sx + m(0.03), FY(0.1)), fill=(80, 80, 80))
        d.line((sx - m(0.25), FY(0.04), sx + m(0.25), FY(0.04)), fill=(60, 60, 60), width=max(2, int(m(0.04))))
        # planta
        px = X(0.7)
        d.polygon([(px - m(0.18), FY(0.45)), (px + m(0.18), FY(0.45)), (px + m(0.13), FY(0)), (px - m(0.13), FY(0))], fill=(200, 120, 80))
        for k in range(9):
            a = -1.4 + k * 0.35
            d.ellipse((px + math.sin(a) * m(0.4) - m(0.1), FY(0.45) - math.cos(a) * m(0.6) - m(0.06), px + math.sin(a) * m(0.4) + m(0.1), FY(0.45) - math.cos(a) * m(0.6) + m(0.06)), fill=(60, 150, 70))
            d.line((px, FY(0.45), px + math.sin(a) * m(0.4), FY(0.45) - math.cos(a) * m(0.6)), fill=(50, 120, 60), width=max(1, int(m(0.02))))

    def screens(self, d, t):
        X, FY, m = self.X, self.FY, self.m
        return [((X(0.55) - m(0.3), FY(1.1), X(0.55), FY(0.8)), (255, 220, 150))]
