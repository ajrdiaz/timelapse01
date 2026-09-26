from engine.interiors.base import Interior, register
from engine.world import shade

SNACK_COLS = [(230, 40, 50), (250, 200, 30), (40, 120, 220), (60, 190, 80), (240, 120, 30), (160, 60, 200)]


@register
class BodegaSnacks(Interior):
    tipo = "bodega_snacks"
    OBJECTS = {
        "estantes": ("Estantes llenos", 0.2, 1.4),
        "expendedora": ("Máquina expendedora", 0.5, 1.2),
        "refri": ("Refri de bebidas", 0.7, 1.0),
        "cajas": ("Cajas de reserva", 0.4, 0.3),
        "leds": ("LEDs", 0.3, 2.45),
    }
    wall = (60, 50, 44)

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        x0, x1 = X(0.03), X(0.37)
        for i in range(5):
            y = FY(0.3 + i * 0.45)
            d.rectangle((x0, y, x1, y + m(0.04)), fill=(150, 110, 70))
            n = int((x1 - x0) / m(0.14))
            for k in range(n):
                c = SNACK_COLS[(i * 3 + k) % len(SNACK_COLS)]
                h = m(0.22 + 0.1 * ((i + k) % 3) / 2)
                d.rectangle((x0 + k * m(0.14) + m(0.02), y - h, x0 + k * m(0.14) + m(0.12), y), fill=c)
        d.rectangle((x0, FY(2.2), x0 + m(0.04), FY(0)), fill=(130, 90, 60))
        d.rectangle((x1 - m(0.04), FY(2.2), x1, FY(0)), fill=(130, 90, 60))
        # máquina expendedora
        e0, e1 = X(0.42), X(0.58)
        d.rectangle((e0, FY(2.0), e1, FY(0)), fill=shade(self.acc, 0.9))
        d.rectangle((e0 + m(0.06), FY(1.9), e1 - m(0.25), FY(0.6)), fill=(200, 230, 240))
        for i in range(5):
            for k in range(3):
                d.rectangle((e0 + m(0.1) + k * m(0.16), FY(1.8 - i * 0.24), e0 + m(0.2) + k * m(0.16), FY(1.65 - i * 0.24)), fill=SNACK_COLS[(i + k) % 6])
        d.rectangle((e1 - m(0.2), FY(1.4), e1 - m(0.06), FY(1.0)), fill=(30, 30, 30))
        # refri de bebidas
        r0, r1 = X(0.62), X(0.77)
        d.rectangle((r0, FY(2.0), r1, FY(0)), fill=(30, 30, 34))
        d.rectangle((r0 + m(0.06), FY(1.92), r1 - m(0.06), FY(0.1)), fill=(170, 220, 240))
        for i in range(6):
            for k in range(4):
                d.rectangle((r0 + m(0.1) + k * m(0.17), FY(1.8 - i * 0.29), r0 + m(0.18) + k * m(0.17), FY(1.62 - i * 0.29)), fill=SNACK_COLS[(k + 2) % 6])
        # cajas
        for i in range(3):
            d.rectangle((X(0.37) + i * m(0.3), FY(0.35 + 0.0), X(0.37) + i * m(0.3) + m(0.28), FY(0)), fill=(190, 150, 100))

    def screens(self, d, t):
        X, FY, m = self.X, self.FY, self.m
        return [((X(0.62) + m(0.06), FY(1.92), X(0.77) - m(0.06), FY(0.1)), (200, 240, 255))]
