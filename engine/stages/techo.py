from engine.stages.base import SfxEvent, Stage, ease, register, seg
from engine.stages.grava_acero import draw_rebar_line
from engine.stages.muros import darken
from engine.world import ROOF_T, lerp, paste_rect

DUCT_T = 0.15


def draw_ladder(d, L, x0, x1, y0, y1):
    m = L.m
    rail = max(2, int(m(0.035)))
    a, b = x0 + (x1 - x0) * 0.25, x1 - (x1 - x0) * 0.25
    d.line((a, y0, a, y1), fill=(150, 150, 158), width=rail)
    d.line((b, y0, b, y1), fill=(150, 150, 158), width=rail)
    y = y0 + m(0.15)
    while y < y1:
        d.line((a, y, b, y), fill=(170, 170, 178), width=rail)
        y += m(0.3)


@register
class Techo(Stage):
    """Puntales → acero → vaciado → ducto de escotilla."""
    tipo = "techo"

    def draw(self, canvas, t, ctx):
        L, d = ctx.L, ctx.draw
        m = L.m
        p1, p2 = seg(t, 0, 0.3), ease(seg(t, 0.3, 0.5))
        p3, p4 = ease(seg(t, 0.5, 0.85)), ease(seg(t, 0.85, 1.0))
        # interior en penumbra cuando el techo se cierra
        if p3 > 0:
            darken(canvas, L.room, 0.45 * p3)
        # puntales y cimbra
        if t < 0.97:
            n = 5
            for i in range(n):
                if p1 * n * 1.6 > i:
                    x = lerp(L.ix0 + m(0.5), L.ix1 - m(0.5), i / (n - 1))
                    d.rectangle((x - m(0.05), L.roof_bot_y, x + m(0.05), L.floor_y), fill=(186, 134, 80))
            k = ease(seg(p1, 0.5, 1))
            if k > 0:
                paste_rect(canvas, ctx.A.madera, (L.ix0, L.roof_bot_y, lerp(L.ix0, L.ix1, k), L.roof_bot_y + m(0.06)))
        draw_rebar_line(d, L, L.bx0 + m(0.05), L.bx1 - m(0.05), L.roof_top_y + m(ROOF_T * 0.4), p2)
        if p3 > 0:
            x1 = lerp(L.bx0, L.bx1, p3)
            paste_rect(canvas, ctx.A.concreto, (L.bx0, L.roof_top_y, min(x1, L.hatch_x0), L.roof_bot_y))
            if x1 > L.hatch_x1:
                paste_rect(canvas, ctx.A.concreto, (L.hatch_x1, L.roof_top_y, x1, L.roof_bot_y))
        if p4 > 0:
            dt = m(DUCT_T)
            ytop = lerp(L.roof_top_y, L.ground_y, p4)
            d.rectangle((L.hatch_x0, ytop, L.hatch_x1, L.roof_bot_y), fill=(38, 36, 34))
            for x0, x1 in ((L.hatch_x0 - dt, L.hatch_x0), (L.hatch_x1, L.hatch_x1 + dt)):
                paste_rect(canvas, ctx.A.concreto, (x0, ytop, x1, L.roof_top_y + 1))
            draw_ladder(d, L, L.hatch_x0, L.hatch_x1, ytop + m(0.1), L.floor_y)

    def pour_point(self, ctx, t):
        L = ctx.L
        if t < 0.5:
            return None
        return (lerp(L.bx0, L.bx1, ease(seg(t, 0.5, 0.85))), L.roof_top_y - L.m(0.35))

    def worker_spots(self, ctx, t):
        L = ctx.L
        n = self.e.obreros
        y = L.floor_y if t < 0.5 else L.roof_top_y
        return [(lerp(L.bx0 + L.m(0.7), L.bx1 - L.m(1.4), (i + 0.5) / max(1, n)), y, 1 - 2 * (i % 2)) for i in range(n)]

    def sfx_events(self, t0, t1):
        ev = super().sfx_events(t0, t1)
        if self.e.sfx:
            d = t1 - t0
            ev += [SfxEvent(t0 + i * 0.3, "martillo", 0.8) for i in range(int(0.3 * d / 0.3))]
            ev += [SfxEvent(t0 + 0.3 * d + i * 0.35, "metal", 0.6) for i in range(int(0.2 * d / 0.35))]
            ev += [SfxEvent(t0 + 0.9 * d, "golpe_tierra", 0.5)]
        return ev
