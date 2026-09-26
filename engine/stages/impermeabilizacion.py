from engine.stages.base import Stage, ease, register, seg
from engine.stages.techo import DUCT_T
from engine.world import COAT_T, lerp

COAT = (26, 26, 30)


@register
class Impermeabilizacion(Stage):
    tipo = "impermeabilizacion"
    ambience = [("brocha", 2.2)]

    def draw(self, canvas, t, ctx):
        L, d = ctx.L, ctx.draw
        m = L.m
        c = m(COAT_T)
        k1 = ease(seg(t, 0.0, 0.4))
        k2 = ease(seg(t, 0.35, 1.0))
        if k1 > 0:
            x1 = lerp(L.bx0 - c, L.bx1 + c, k1)
            d.rectangle((L.bx0 - c, L.roof_top_y - c, min(x1, L.hatch_x0 - m(DUCT_T) - c), L.roof_top_y), fill=COAT)
            if x1 > L.hatch_x1:
                d.rectangle((L.hatch_x1 + m(DUCT_T) + c, L.roof_top_y - c, x1, L.roof_top_y), fill=COAT)
            # ducto
            dk = ease(seg(k1, 0.6, 1))
            if dk > 0:
                y0 = lerp(L.roof_top_y, L.ground_y + m(0.05), dk)
                d.rectangle((L.hatch_x0 - m(DUCT_T) - c, y0, L.hatch_x0 - m(DUCT_T), L.roof_top_y), fill=COAT)
                d.rectangle((L.hatch_x1 + m(DUCT_T), y0, L.hatch_x1 + m(DUCT_T) + c, L.roof_top_y), fill=COAT)
        if k2 > 0:
            y1 = lerp(L.roof_top_y, L.slab_bot_y, k2)
            d.rectangle((L.bx0 - c, L.roof_top_y, L.bx0, y1), fill=COAT)
            d.rectangle((L.bx1, L.roof_top_y, L.bx1 + c, y1), fill=COAT)
            # brillo húmedo
            d.line((L.bx0 - c * 0.5, L.roof_top_y, L.bx0 - c * 0.5, y1), fill=(70, 70, 80), width=max(1, int(c * 0.2)))
            d.line((L.bx1 + c * 0.5, L.roof_top_y, L.bx1 + c * 0.5, y1), fill=(70, 70, 80), width=max(1, int(c * 0.2)))

    def worker_spots(self, ctx, t):
        L = ctx.L
        spots = [((L.pit_x0 + L.bx0) / 2, L.slab_bot_y, 1), ((L.pit_x1 + L.bx1) / 2, L.slab_bot_y, -1)]
        for i in range(2, self.e.obreros):
            spots.append((lerp(L.bx0 + L.m(0.6), L.hatch_x0 - L.m(0.6), (i - 1.5) / max(1, self.e.obreros - 2)), L.roof_top_y - L.m(COAT_T), 1))
        return spots[: self.e.obreros]
