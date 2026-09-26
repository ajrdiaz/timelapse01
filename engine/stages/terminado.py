import math

from engine.stages.base import SfxEvent, Stage, register


@register
class Terminado(Stage):
    tipo = "terminado"

    def draw_active(self, canvas, t, ctx):
        # destellos sobre la escotilla
        L, d = ctx.L, ctx.draw
        cx = (L.hatch_x0 + L.hatch_x1) / 2
        for i in range(4):
            a = t * 6 + i * 1.7
            r = L.m(0.08) * (0.5 + 0.5 * math.sin(a * 2))
            x = cx + math.cos(a) * L.m(0.6)
            y = L.ground_y - L.m(0.5) + math.sin(a * 1.3) * L.m(0.25)
            d.polygon([(x, y - r * 2), (x + r * 0.5, y), (x, y + r * 2), (x - r * 0.5, y)], fill=(255, 250, 200))
            d.polygon([(x - r * 2, y), (x, y - r * 0.5), (x + r * 2, y), (x, y + r * 0.5)], fill=(255, 250, 200))

    def worker_spots(self, ctx, t):
        L = ctx.L
        return [(L.pit_x0 + L.m(0.3) + i * L.m(0.8), L.ground_y, 1) for i in range(self.e.obreros)]

    def sfx_events(self, t0, t1):
        return [SfxEvent(t0 + 0.05, "tada", 0.9)] if self.e.sfx else []
