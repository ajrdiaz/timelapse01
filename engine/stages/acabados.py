from engine.stages.base import SfxEvent, Stage, ease, register, seg
from engine.world import lerp, paste_rect


def draw_vent(d, L, k):
    m = L.m
    x = L.vent_x
    top = lerp(L.roof_top_y, L.ground_y - m(0.75), k)
    d.rectangle((x - m(0.08), top, x + m(0.08), L.roof_top_y), fill=(236, 236, 230))
    d.line((x + m(0.04), top, x + m(0.04), L.roof_top_y), fill=(255, 255, 255), width=max(1, int(m(0.02))))
    if k >= 1:
        d.pieslice((x - m(0.2), top - m(0.18), x + m(0.2), top + m(0.1)), 180, 360, fill=(210, 210, 204))


def draw_hatch(d, L, drop):
    m = L.m
    y = L.ground_y - drop
    x0, x1 = L.hatch_x0 - m(0.2), L.hatch_x1 + m(0.2)
    d.rounded_rectangle((x0, y - m(0.14), x1, y), radius=m(0.04), fill=(70, 96, 70))
    d.rectangle((x0, y - m(0.05), x1, y), fill=(52, 72, 52))
    cx = (x0 + x1) / 2
    d.ellipse((cx - m(0.16), y - m(0.3), cx + m(0.16), y - m(0.12)), outline=(190, 190, 190), width=max(2, int(m(0.035))))


@register
class Acabados(Stage):
    """Pasto en rollos, ventilación y escotilla."""
    tipo = "acabados"
    ambience = [("pasto", 1.0)]

    def draw(self, canvas, t, ctx):
        L, d = ctx.L, ctx.draw
        m = L.m
        k1 = ease(seg(t, 0, 0.5))
        if k1 > 0:
            x1 = lerp(L.pit_x0, L.pit_x1, k1)
            paste_rect(canvas, ctx.A.relleno, (L.pit_x0, L.ground_y - 2, x1, L.ground_y + m(0.05)))
            paste_rect(canvas, ctx.A.pasto, (L.pit_x0, L.ground_y - m(0.25), x1, L.ground_y + m(0.18)))
        k2 = ease(seg(t, 0.4, 0.7))
        if k2 > 0:
            draw_vent(d, L, k2)
        k3 = ease(seg(t, 0.7, 0.95))
        if k3 > 0:
            draw_hatch(d, L, (1 - k3) * m(1.4))

    def draw_active(self, canvas, t, ctx):
        L, d = ctx.L, ctx.draw
        k1 = ease(seg(t, 0, 0.5))
        if 0 < k1 < 1:
            x = lerp(L.pit_x0, L.pit_x1, k1)
            r = L.m(0.22) * (1 - k1 * 0.6)
            d.ellipse((x - r, L.ground_y - 2 * r, x + r, L.ground_y), fill=(70, 150, 55), outline=(90, 60, 35), width=max(1, int(r * 0.3)))

    def sfx_events(self, t0, t1):
        ev = super().sfx_events(t0, t1)
        if self.e.sfx:
            ev.append(SfxEvent(t0 + (t1 - t0) * 0.95, "escotilla", 1.0))
        return ev
