import math

from engine.interiors.base import Interior, register
from engine.world import mix, shade


@register
class Streaming(Interior):
    tipo = "streaming"
    OBJECTS = {
        "microfono": ("Micrófono", 0.42, 1.2),
        "camara": ("Cámara", 0.6, 1.5),
        "ring_light": ("Ring light", 0.66, 1.6),
        "panel_acustico": ("Paneles acústicos", 0.15, 1.7),
        "pantalla_verde": ("Pantalla verde", 0.08, 1.2),
        "escritorio": ("Escritorio", 0.36, 0.75),
        "leds": ("LEDs", 0.3, 2.45),
    }
    wall = (30, 30, 40)

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        # pantalla verde enrollable
        d.rectangle((X(0.02), FY(2.3), X(0.14), FY(0.2)), fill=(40, 200, 80))
        d.rectangle((X(0.015), FY(2.35), X(0.145), FY(2.28)), fill=(40, 40, 40))
        # paneles acústicos
        for i in range(3):
            for k in range(2):
                x = X(0.17) + i * m(0.34)
                y = FY(2.2) + k * m(0.4)
                d.rectangle((x, y, x + m(0.3), y + m(0.36)), fill=shade(self.acc, 0.8 + 0.15 * ((i + k) % 2)))
                for j in range(4):
                    d.line((x + m(0.06) * (j + 1), y, x + m(0.06) * (j + 1), y + m(0.36)), fill=shade(self.acc, 0.6), width=max(1, int(m(0.015))))
        # escritorio + monitor
        d.rectangle((X(0.22), FY(0.78), X(0.5), FY(0.7)), fill=(240, 240, 240))
        d.rectangle((X(0.23), FY(0.7), X(0.24), FY(0)), fill=(200, 200, 200))
        d.rectangle((X(0.48), FY(0.7), X(0.49), FY(0)), fill=(200, 200, 200))
        self.monitor(d, X(0.3), FY(0.78), m(0.6), m(0.36), t)
        # micrófono con brazo
        mx = X(0.42)
        d.line((X(0.47), FY(0.78), X(0.47), FY(1.05), mx, FY(1.2)), fill=(40, 40, 40), width=max(2, int(m(0.03))))
        d.rounded_rectangle((mx - m(0.06), FY(1.35), mx + m(0.06), FY(1.1)), radius=m(0.05), fill=(30, 30, 30))
        # letrero ON AIR
        on = int(t * 2) % 2 == 0
        d.rounded_rectangle((X(0.28), FY(2.3), X(0.42), FY(2.05)), radius=m(0.05), fill=(230, 30, 40) if on else (90, 20, 25))
        # ring light + cámara en trípode
        rx = X(0.66)
        d.line((rx, FY(1.3), rx, FY(0)), fill=(40, 40, 40), width=max(2, int(m(0.03))))
        for k in (-1, 1):
            d.line((rx, FY(0.5), rx + k * m(0.25), FY(0)), fill=(40, 40, 40), width=max(2, int(m(0.03))))
        r = m(0.32)
        d.ellipse((rx - r, FY(1.6) - r, rx + r, FY(1.6) + r), outline=(255, 250, 235), width=max(3, int(m(0.07))))
        cx = X(0.6)
        d.rectangle((cx - m(0.1), FY(1.58), cx + m(0.1), FY(1.42)), fill=(20, 20, 20))
        d.ellipse((cx - m(0.16), FY(1.56), cx - m(0.06), FY(1.44)), fill=(60, 60, 90))

    def screens(self, d, t):
        X, FY, m = self.X, self.FY, self.m
        r = m(0.32)
        return [((X(0.66) - r, FY(1.6) - r, X(0.66) + r, FY(1.6) + r), (255, 250, 235))]
