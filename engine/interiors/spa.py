import math

from engine.interiors.base import Interior, register
from engine.world import mix, shade


@register
class Spa(Interior):
    tipo = "spa"
    OBJECTS = {
        "jacuzzi": ("Jacuzzi", 0.28, 0.6),
        "sauna": ("Sauna", 0.64, 1.2),
        "plantas": ("Plantas", 0.05, 0.8),
        "velas": ("Velas", 0.46, 0.35),
        "toallas": ("Toallas", 0.47, 1.4),
        "leds": ("Luz ambiental", 0.3, 2.45),
    }
    wall = (70, 62, 56)
    floor = (190, 180, 165)
    led_on_ceiling = True

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        # jacuzzi con burbujas
        x0, x1 = X(0.12), X(0.44)
        d.rounded_rectangle((x0, FY(0.75), x1, FY(0)), radius=m(0.1), fill=(235, 235, 235))
        d.rectangle((x0 + m(0.08), FY(0.68), x1 - m(0.08), FY(0.45)), fill=mix(self.led, (60, 160, 220), 0.5))
        for i in range(10):
            ph = (t * 0.8 + i * 0.13) % 1
            bx = x0 + m(0.2) + (i * 0.37 % 1) * (x1 - x0 - m(0.4))
            by = FY(0.45 + ph * 0.35)
            r = m(0.03 + 0.02 * (i % 3))
            d.ellipse((bx - r, by - r, bx + r, by + r), outline=(240, 250, 255), width=max(1, int(m(0.012))))
        # sauna de madera
        s0, s1 = X(0.52), X(0.76)
        d.rectangle((s0, FY(2.2), s1, FY(0)), fill=(170, 110, 60))
        y = FY(2.2)
        while y < FY(0):
            d.line((s0, y, s1, y), fill=(140, 88, 46), width=max(1, int(m(0.015))))
            y += m(0.14)
        d.rectangle((s0 + m(0.2), FY(1.9), s0 + m(0.75), FY(0)), fill=(150, 96, 52))
        d.rectangle((s0 + m(0.3), FY(1.8), s0 + m(0.65), FY(1.2)), fill=(250, 200, 140))
        # toallas enrolladas
        for i in range(3):
            cx = X(0.47)
            d.ellipse((cx - m(0.16), FY(1.25 + i * 0.13) - m(0.13), cx + m(0.16), FY(1.25 + i * 0.13)), fill=shade(self.acc, 1.3 - i * 0.1))
        d.rectangle((X(0.44), FY(1.25), X(0.5), FY(1.21)), fill=(140, 100, 70))
        # plantas
        px = X(0.05)
        d.rectangle((px - m(0.15), FY(0.4), px + m(0.15), FY(0)), fill=(200, 190, 170))
        for k in range(7):
            a = -1.3 + k * 0.43
            d.line((px, FY(0.4), px + math.sin(a) * m(0.5), FY(0.4) - math.cos(a) * m(0.6)), fill=(60, 140, 70), width=max(2, int(m(0.06))))
        # velas
        for i in range(3):
            vx = X(0.46) + i * m(0.12)
            d.rectangle((vx - m(0.035), FY(0.18 + 0.05 * i), vx + m(0.035), FY(0)), fill=(245, 240, 225))
            f = m(0.02) * (1 + 0.3 * math.sin(t * 9 + i))
            d.ellipse((vx - f, FY(0.18 + 0.05 * i) - 3 * f, vx + f, FY(0.18 + 0.05 * i)), fill=(255, 190, 60))
