from engine.stages.base import SfxEvent, Stage, ease, register, seg
from engine.world import SLAB_T, lerp, paste_rect

REBAR = (150, 72, 40)


def draw_rebar_line(d, L, x0, x1, y, k):
    """Varilla horizontal con cortes transversales cada 20 cm, hasta la fracción k."""
    if k <= 0:
        return
    xe = lerp(x0, x1, k)
    w = max(2, int(L.m(0.025)))
    d.line((x0, y, xe, y), fill=REBAR, width=w)
    x = x0 + L.m(0.1)
    r = L.m(0.022)
    while x < xe:
        d.ellipse((x - r, y - r - w, x + r, y + r - w), fill=(120, 58, 32))
        x += L.m(0.2)


@register
class GravaAcero(Stage):
    tipo = "grava_acero"

    def draw(self, canvas, t, ctx):
        L = ctx.L
        k = ease(seg(t, 0.0, 0.5))
        if k > 0:
            paste_rect(canvas, ctx.A.grava, (L.pit_x0, L.slab_bot_y, lerp(L.pit_x0, L.pit_x1, k), L.pit_bot_y))
        k2 = ease(seg(t, 0.5, 1.0))
        y = L.slab_bot_y - L.m(SLAB_T * 0.3)
        draw_rebar_line(ctx.draw, L, L.bx0 + L.m(0.05), L.bx1 - L.m(0.05), y, k2)
        # separadores (silletas)
        if k2 > 0:
            x = L.bx0 + L.m(0.3)
            while x < lerp(L.bx0, L.bx1, k2):
                ctx.draw.rectangle((x - L.m(0.02), y, x + L.m(0.02), L.slab_bot_y), fill=(80, 80, 80))
                x += L.m(1.0)

    def worker_spots(self, ctx, t):
        L = ctx.L
        return [(lerp(L.bx0 + L.m(0.5), L.bx1 - L.m(0.5), (i + 0.5) / max(1, self.e.obreros)), L.slab_bot_y, 1 - 2 * (i % 2))
                for i in range(self.e.obreros)]

    def sfx_events(self, t0, t1):
        ev = super().sfx_events(t0, t1)
        if self.e.sfx:
            mid = (t0 + t1) / 2
            ev += [SfxEvent(t0 + i * 0.6, "grava", 0.8) for i in range(int((mid - t0) / 0.6))]
            ev += [SfxEvent(mid + i * 0.4, "metal", 0.6) for i in range(int((t1 - mid) / 0.4))]
        return ev
