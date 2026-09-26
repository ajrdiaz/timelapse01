from engine.stages.base import SfxEvent, Stage, ease, register, seg
from engine.world import lerp


@register
class Marcado(Stage):
    tipo = "marcado"
    ambience = [("martillo", 1.5)]

    def draw(self, canvas, t, ctx):
        L, d = ctx.L, ctx.draw
        m = L.m
        g = L.ground_y
        xs = [L.pit_x0, L.bx0, L.bx1, L.pit_x1]
        # estacas (van apareciendo)
        for i, x in enumerate(xs):
            k = ease(seg(t, i * 0.12, i * 0.12 + 0.2))
            if k <= 0:
                continue
            h = m(0.55) * k
            d.rectangle((x - m(0.04), g - h, x + m(0.04), g + m(0.12)), fill=(196, 146, 86))
            d.polygon([(x - m(0.06), g - h), (x + m(0.06), g - h), (x, g - h - m(0.06))], fill=(230, 60, 40))
        # hilo y línea de cal
        k = ease(seg(t, 0.25, 0.9))
        if k > 0:
            x1 = lerp(L.pit_x0, L.pit_x1, k)
            d.line((L.pit_x0, g - m(0.45), x1, g - m(0.45)), fill=(250, 250, 250), width=max(1, int(m(0.015))))
            x = L.pit_x0
            while x < x1:
                d.rectangle((x, g - m(0.03), min(x1, x + m(0.25)), g + m(0.02)), fill=(245, 245, 240))
                x += m(0.4)

    def worker_spots(self, ctx, t):
        L = ctx.L
        out = []
        for i in range(self.e.obreros):
            x = lerp(L.pit_x0 - L.m(0.3), L.pit_x1, (i + 0.5) / max(1, self.e.obreros))
            out.append((x, L.ground_y, 1 if i % 2 else -1))
        return out
