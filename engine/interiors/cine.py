from engine.interiors.base import Interior, register
from engine.world import mix, shade


@register
class Cine(Interior):
    tipo = "cine"
    OBJECTS = {
        "pantalla": ("Pantalla gigante", 0.28, 1.5),
        "proyector": ("Proyector", 0.72, 2.3),
        "sillones": ("Sillones reclinables", 0.62, 0.7),
        "palomitas": ("Máquina de palomitas", 0.06, 0.6),
        "bocinas": ("Bocinas", 0.55, 1.0),
        "leds": ("Luces LED", 0.3, 0.2),
    }
    wall = (26, 18, 22)
    floor = (90, 20, 30)

    def furniture(self, canvas, d, ctx, t):
        X, FY, m = self.X, self.FY, self.m
        # pantalla
        d.rectangle((X(0.08), FY(2.25), X(0.5), FY(0.9)), fill=(10, 10, 10))
        self.screen_box = (X(0.09), FY(2.2), X(0.49), FY(0.95))
        sb = self.screen_box
        d.rectangle(sb, fill=mix(self.acc, (30, 60, 140), 0.5))
        k = (t * 0.3) % 1
        d.ellipse((sb[0] + (sb[2] - sb[0]) * (0.2 + 0.5 * k), sb[1] + m(0.2), sb[0] + (sb[2] - sb[0]) * (0.2 + 0.5 * k) + m(0.3), sb[1] + m(0.5)), fill=(255, 220, 120))
        d.polygon([(sb[0], sb[3]), (sb[0] + (sb[2] - sb[0]) * 0.4, sb[1] + (sb[3] - sb[1]) * 0.5), (sb[2], sb[3])], fill=(40, 30, 60))
        # bocinas
        for rx in (0.04, 0.55):
            x = X(rx)
            d.rectangle((x - m(0.13), FY(1.4), x + m(0.13), FY(0.6)), fill=(20, 20, 22))
            for h, r in ((1.25, 0.06), (0.85, 0.1)):
                d.ellipse((x - m(r), FY(h) - m(r), x + m(r), FY(h) + m(r)), fill=(60, 60, 64))
        # palomitas
        px = X(0.06)
        d.rectangle((px - m(0.2), FY(0.55), px + m(0.2), FY(0)), fill=(200, 30, 30))
        d.rectangle((px - m(0.18), FY(0.95), px + m(0.18), FY(0.55)), fill=(250, 240, 200))
        for i in range(8):
            d.ellipse((px - m(0.15) + (i % 4) * m(0.08), FY(0.7 + (i // 4) * 0.1), px - m(0.1) + (i % 4) * m(0.08), FY(0.65 + (i // 4) * 0.1)), fill=(255, 250, 220))
        # sillones reclinables
        for rx in (0.58, 0.7):
            x = X(rx)
            d.rounded_rectangle((x - m(0.3), FY(0.55), x + m(0.3), FY(0.1)), radius=m(0.08), fill=shade(self.acc, 0.7))
            d.rounded_rectangle((x + m(0.1), FY(1.05), x + m(0.32), FY(0.3)), radius=m(0.08), fill=shade(self.acc, 0.85))
            d.rectangle((x - m(0.32), FY(0.7), x - m(0.22), FY(0.35)), fill=shade(self.acc, 0.6))
        # proyector y haz
        pj = X(0.72)
        d.rectangle((pj - m(0.18), self.y0 + m(0.1), pj + m(0.18), self.y0 + m(0.28)), fill=(220, 220, 224))

    def screens(self, d, t):
        X, FY = self.X, self.FY
        return [((X(0.09), FY(2.2), X(0.49), FY(0.95)), mix(self.acc, (80, 120, 255), 0.5))]
