import math

from engine.stages.base import SfxEvent, Stage, dig_floor, dig_poly, dig_profile, ease, register, seg
from engine.world import lerp, paste_poly

CYCLE = 1.4  # segundos de video por palada


def cycle_target(ph, dig_pt, dump_pt, rest_pt):
    """Objetivo de la cuchara, curl y carga para la fase ph (0..1) de una palada."""
    if ph < 0.3:
        k = ease(ph / 0.3)
        return (lerp(rest_pt[0], dig_pt[0], k), lerp(rest_pt[1], dig_pt[1], k)), -0.2, 0.0
    if ph < 0.45:
        k = (ph - 0.3) / 0.15
        return (dig_pt[0] + k * 30, dig_pt[1] - k * 20), -0.2 + k * 1.0, k
    if ph < 0.75:
        k = ease((ph - 0.45) / 0.3)
        return (lerp(dig_pt[0], dump_pt[0], k), lerp(dig_pt[1], dump_pt[1], k)), 0.8, 1.0
    if ph < 0.87:
        k = (ph - 0.75) / 0.12
        return dump_pt, 0.8 - 1.6 * k, 1.0 - k
    k = ease((ph - 0.87) / 0.13)
    return (lerp(dump_pt[0], rest_pt[0], k), lerp(dump_pt[1], rest_pt[1], k)), -0.8 + 0.6 * k, 0.0


@register
class Excavacion(Stage):
    tipo = "excavacion"

    def apply_state(self, st, t):
        st.dig = t
        st.pile = max(st.pile, t)

    def draw(self, canvas, t, ctx):
        L = ctx.L
        poly = dig_poly(L, t)
        if not poly:
            return
        paste_poly(canvas, ctx.A.pozo, poly)
        ctx.draw.line(poly[2:] + [poly[0]], fill=(58, 38, 22), width=max(2, int(L.m(0.04))))

    def excavator(self, ctx, t):
        L = ctx.L
        m = L.m
        dl, dn, xf = dig_profile(L, t)
        home = L.pit_x1 - m(1.55)
        # la excavadora baja cuando el frente la alcanza
        near = seg(xf, home - m(2.2), home + m(1.0))
        y = L.ground_y + lerp(dl, dn, ease(near))
        x = home
        e = self.e
        opts = ctx.scene.personajes.excavadora
        if opts.entrada_salida:
            k_in = seg(t, 0.0, 0.08)
            x = lerp(L.W + m(2.5), home, ease(k_in))
            k_out = seg(t, 0.93, 1.0)
            if k_out > 0:
                x = lerp(home, L.W + m(3.0), ease(k_out))
                y = lerp(L.pit_bot_y, L.ground_y, ease(min(1, k_out * 1.6)))
        ph = ((ctx.t - e.inicio_seg) / CYCLE) % 1.0
        dig_pt = (min(xf + m(0.2), home - m(2.6)), L.ground_y + dn - m(0.1))
        dump_pt = (L.pit_x1 + m(0.9), L.ground_y - m(1.3))
        rest = (home - m(3.6), y - m(1.6))
        tgt, curl, load = cycle_target(ph, dig_pt, dump_pt, rest)
        if t < 0.08 or t > 0.93:
            tgt, curl, load = (x - m(3.4), y - m(1.2)), 0.3, 0.0
        return {"x": x, "y": y, "target": tgt, "curl": curl, "load": load}

    def worker_spots(self, ctx, t):
        L = ctx.L
        out = []
        for i in range(self.e.obreros):
            x = L.pit_x0 + L.m(0.45) + i * L.m(0.9)
            out.append((x, dig_floor(L, t, x), 1))
        return out

    def sfx_events(self, t0, t1):
        ev = super().sfx_events(t0, t1)
        if self.e.sfx:
            n = int((t1 - t0) / CYCLE)
            for i in range(n):
                ev.append(SfxEvent(t0 + i * CYCLE + 0.4 * CYCLE, "golpe_tierra", 0.9))
                ev.append(SfxEvent(t0 + i * CYCLE + 0.8 * CYCLE, "tierra", 0.6))
        return ev
