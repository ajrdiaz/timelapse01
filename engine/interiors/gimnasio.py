import math

from engine.interiors.base import Interior, register
from engine.world import shade


@register
class Gimnasio(Interior):
    tipo = "gimnasio"
    OBJECTS = {
        "rack": ("Rack de sentadillas", 0.12, 1.3),
        "mancuernas": ("Mancuernas", 0.36, 0.5),
        "caminadora": ("Caminadora", 0.6, 0.8),
        "espejo": ("Espejo", 0.36, 1.6),
        "costal": ("Costal de box", 0.74, 1.3),
        "leds": ("Luces LED", 0.5, 2.45),
    }
    wall = (40, 40, 44)
    floor = (30, 30, 32)

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        steel = (120, 120, 128)
        # rack
        x0, x1 = X(0.05), X(0.2)
        for x in (x0, x1):
            d.rectangle((x - m(0.04), FY(2.1), x + m(0.04), FY(0)), fill=steel)
        d.rectangle((x0, FY(2.1), x1, FY(2.02)), fill=steel)
        y = FY(1.35)
        d.line((x0 - m(0.35), y, x1 + m(0.35), y), fill=(180, 180, 186), width=max(2, int(m(0.04))))
        for x in (x0 - m(0.28), x1 + m(0.28)):
            d.rectangle((x - m(0.05), y - m(0.25), x + m(0.05), y + m(0.25)), fill=self.acc)
        # espejo
        d.rectangle((X(0.27), FY(2.2), X(0.46), FY(0.9)), fill=(190, 215, 225))
        d.line((X(0.3), FY(2.1), X(0.36), FY(1.8)), fill=(240, 250, 255), width=max(2, int(m(0.03))))
        # mancuernas
        d.rectangle((X(0.27), FY(0.55), X(0.46), FY(0.5)), fill=steel)
        d.rectangle((X(0.28), FY(0.5), X(0.29), FY(0)), fill=steel)
        d.rectangle((X(0.44), FY(0.5), X(0.45), FY(0)), fill=steel)
        for i in range(5):
            cx = X(0.29 + i * 0.037)
            r = m(0.05 + i * 0.008)
            d.ellipse((cx - r, FY(0.55) - 2 * r, cx + r, FY(0.55)), fill=shade(self.acc, 0.7 + i * 0.1))
        # caminadora
        tx = X(0.6)
        d.polygon([(tx - m(0.6), FY(0.1)), (tx + m(0.5), FY(0.1)), (tx + m(0.5), FY(0.25)), (tx - m(0.6), FY(0.2))], fill=(30, 30, 34))
        d.line((tx + m(0.45), FY(0.25), tx + m(0.35), FY(1.2)), fill=steel, width=max(2, int(m(0.06))))
        d.rectangle((tx + m(0.2), FY(1.3), tx + m(0.5), FY(1.1)), fill=(20, 20, 24))
        d.rectangle((tx + m(0.24), FY(1.27), tx + m(0.46), FY(1.14)), fill=self.led)
        # costal colgante (se balancea)
        cx = X(0.74)
        sw = math.sin(t * 2.2) * m(0.06)
        d.line((cx, self.y0, cx + sw, FY(1.9)), fill=(90, 90, 90), width=max(2, int(m(0.02))))
        d.rounded_rectangle((cx + sw - m(0.18), FY(1.9), cx + sw + m(0.18), FY(0.8)), radius=m(0.12), fill=(160, 30, 30))

    def screens(self, d, t):
        return []
