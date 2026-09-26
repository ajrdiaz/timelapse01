import math

from PIL import Image, ImageDraw

from engine.stages.base import SfxEvent, Stage, ease, fill_level, register, seg
from engine.stages.excavacion import CYCLE, cycle_target
from engine.stages.techo import DUCT_T
from engine.world import COAT_T, lerp, paste_mask


def fill_mask(ctx):
    L = ctx.L
    key = "fill_mask"
    if key not in ctx.draw_cache:
        m = L.m
        c = m(COAT_T)
        mask = Image.new("L", (L.W, L.H), 0)
        d = ImageDraw.Draw(mask)
        d.rectangle((L.pit_x0, L.ground_y - 2, L.pit_x1, L.pit_bot_y), fill=255)
        d.rectangle((L.bx0 - c, L.roof_top_y - c, L.bx1 + c, L.slab_bot_y), fill=0)
        d.rectangle((L.hatch_x0 - m(DUCT_T) - c, L.ground_y, L.hatch_x1 + m(DUCT_T) + c, L.roof_top_y), fill=0)
        ctx.draw_cache[key] = mask
    return ctx.draw_cache[key]


@register
class Relleno(Stage):
    tipo = "relleno"

    def apply_state(self, st, t):
        st.fill = t
        st.pile = st.pile * (1 - ease(t))

    def draw(self, canvas, t, ctx):
        L = ctx.L
        if t <= 0:
            return
        lvl = fill_level(L, t)
        paste_mask(canvas, ctx.A.relleno, fill_mask(ctx), (L.pit_x0, lvl, L.pit_x1, L.pit_bot_y))

    def excavator(self, ctx, t):
        L = ctx.L
        m = L.m
        x = L.pit_x1 + m(1.75)
        y = L.ground_y
        ph = ((ctx.t - self.e.inicio_seg) / CYCLE) % 1.0
        scoop = (L.pit_x1 + m(0.6), L.ground_y - m(0.2))
        k = (math.sin(ctx.t * 1.3) + 1) / 2
        lvl = fill_level(L, t)
        dump = (lerp(L.pit_x0 + m(1.0), L.pit_x1 - m(0.5), k), min(lvl, L.ground_y) - m(1.4))
        rest = (x - m(3.4), y - m(1.8))
        # la palada del relleno va al revés: recoge del montón y vacía en el pozo
        tgt, curl, load = cycle_target(ph, scoop, dump, rest)
        return {"x": x, "y": y, "target": tgt, "curl": curl, "load": load}

    def worker_spots(self, ctx, t):
        L = ctx.L
        lvl = fill_level(L, t)
        out = []
        for i in range(self.e.obreros):
            x = lerp(L.pit_x0 + L.m(0.3), L.pit_x1 - L.m(2.0), (i + 0.5) / max(1, self.e.obreros))
            y = lvl if not (L.bx0 <= x <= L.bx1) else min(lvl, L.roof_top_y - L.m(COAT_T))
            out.append((x, y, 1 - 2 * (i % 2)))
        return out

    def sfx_events(self, t0, t1):
        ev = super().sfx_events(t0, t1)
        if self.e.sfx:
            ev += [SfxEvent(t0 + i * CYCLE + 0.8 * CYCLE, "tierra", 0.8) for i in range(int((t1 - t0) / CYCLE))]
        return ev
