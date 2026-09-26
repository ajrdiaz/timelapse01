from PIL import Image

from engine.stages.base import SfxEvent, Stage, ease, register, seg
from engine.world import WALL_T, lerp, paste_rect

FORM_T = 0.07


def darken(canvas, box, alpha):
    from engine.world import ibox

    b = ibox(box, canvas.width, canvas.height)
    if b is None or alpha <= 0:
        return
    canvas.alpha_composite(Image.new("RGBA", (b[2] - b[0], b[3] - b[1]), (0, 0, 0, int(255 * alpha))), b[:2])


@register
class Muros(Stage):
    """Encofrado → vaciado → desencofrado."""
    tipo = "muros"

    def walls(self, L):
        wt = L.m(WALL_T)
        return [(L.bx0, L.bx0 + wt), (L.bx1 - wt, L.bx1)]

    def levels(self, t):
        pour = seg(t, 0.35, 0.7)
        return ease(seg(pour, 0, 0.6)), ease(seg(pour, 0.4, 1.0)), ease(pour)

    def draw(self, canvas, t, ctx):
        L, d = ctx.L, ctx.draw
        m = L.m
        top, bot = L.roof_bot_y, L.floor_y
        lv_l, lv_r, lv_back = self.levels(t)
        stripped = t >= 0.7
        # pared trasera del recinto (se ve a través del corte)
        if lv_back > 0:
            yb = lerp(bot, top, lv_back)
            paste_rect(canvas, ctx.A.concreto_encofrado, (L.ix0, yb, L.ix1, bot))
            darken(canvas, (L.ix0, yb, L.ix1, bot), 0.28)
        # muros cortados
        for (x0, x1), lv in zip(self.walls(L), (lv_l, lv_r)):
            if lv > 0:
                tex = ctx.A.concreto_encofrado if stripped else ctx.A.concreto
                paste_rect(canvas, tex, (x0, lerp(bot, top, lv), x1, bot))
        # encofrado de madera
        form_up = ease(seg(t, 0.0, 0.33))
        form_down = ease(seg(t, 0.72, 0.97))
        if form_up > 0 and form_down < 1:
            h_top = lerp(bot, top, form_up)
            h_top = lerp(h_top, bot, form_down)
            ft = m(FORM_T)
            for x0, x1 in self.walls(L):
                for fx0, fx1 in ((x0 - ft, x0), (x1, x1 + ft)):
                    paste_rect(canvas, ctx.A.madera, (fx0, h_top, fx1, bot))
                # puntales diagonales de apoyo hacia el interior
                inner = x1 + ft if x0 < L.cx else x0 - ft
                foot = inner + (m(0.8) if x0 < L.cx else -m(0.8))
                if h_top < bot - m(0.5):
                    d.line((inner, (h_top + bot) / 2, foot, bot), fill=(170, 120, 70), width=max(2, int(m(0.06))))

    def pour_point(self, ctx, t):
        L = ctx.L
        lv_l, lv_r, _ = self.levels(t)
        (a0, a1), (b0, b1) = self.walls(L)
        if lv_l < 1:
            return ((a0 + a1) / 2, L.roof_bot_y - L.m(0.4))
        return ((b0 + b1) / 2, L.roof_bot_y - L.m(0.4))

    def worker_spots(self, ctx, t):
        L = ctx.L
        n = self.e.obreros
        return [(lerp(L.ix0 + L.m(0.9), L.ix1 - L.m(0.9), (i + 0.5) / max(1, n)), L.floor_y, -1 if i % 2 else 1)
                for i in range(n)]

    def sfx_events(self, t0, t1):
        ev = super().sfx_events(t0, t1)
        if self.e.sfx:
            d = t1 - t0
            ev += [SfxEvent(t0 + i * 0.35, "martillo", 0.8) for i in range(int(0.33 * d / 0.35))]
            ev.append(SfxEvent(t0 + 0.35 * d, "vertido", 0.5, 0.35 * d))
            ev += [SfxEvent(t0 + 0.72 * d + i * 0.5, "madera", 0.7) for i in range(int(0.25 * d / 0.5))]
        return ev
