from engine.stages.base import Stage, ease, register
from engine.world import WALL_T, lerp, paste_rect
from engine.stages.grava_acero import REBAR


@register
class Losa(Stage):
    tipo = "losa"
    ambience = [("rastrillo", 1.2)]

    def front(self, L, t):
        return lerp(L.bx0, L.bx1, ease(t))

    def draw(self, canvas, t, ctx):
        L = ctx.L
        if t <= 0:
            return
        x1 = self.front(L, t)
        paste_rect(canvas, ctx.A.concreto, (L.bx0, L.floor_y, x1, L.slab_bot_y))
        if t > 0.85:
            # varillas de arranque para los muros
            h = L.m(0.6) * (t - 0.85) / 0.15
            for x in (L.bx0 + L.m(WALL_T / 2), L.bx1 - L.m(WALL_T / 2)):
                ctx.draw.line((x, L.floor_y, x, L.floor_y - h), fill=REBAR, width=max(2, int(L.m(0.025))))

    def draw_active(self, canvas, t, ctx):
        L = ctx.L
        x1 = self.front(L, t)
        if 0 < t < 1:
            ov = (max(L.bx0, x1 - L.m(1.2)), L.floor_y, x1, L.slab_bot_y)
            ctx.draw.rectangle(ov, fill=(118, 118, 114))

    def pour_point(self, ctx, t):
        L = ctx.L
        return (self.front(ctx.L, t), L.floor_y - L.m(0.35))

    def worker_spots(self, ctx, t):
        L = ctx.L
        return [(lerp(L.bx0 + L.m(0.6), L.bx1 - L.m(0.6), (i + 0.5) / max(1, self.e.obreros)), L.floor_y, 1 - 2 * (i % 2))
                for i in range(self.e.obreros)]
