"""Actores: obreros por poses, excavadora con cinemática inversa y manguera de concreto."""
from __future__ import annotations

import math

from PIL import ImageDraw

from engine.world import WORKER_H, shade

SKIN = (236, 188, 150)
BOOT = (60, 42, 30)
SHIRT = (240, 240, 235)


def _limb(d: ImageDraw.ImageDraw, a, b, c, w, color):
    d.line([a, b, c], fill=color, width=int(w), joint="curve")
    r = w / 2
    for p in (a, b, c):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=color)


def _pt(ox, oy, length, ang, fx):
    """Punto a `length` desde (ox,oy) con ángulo `ang` medido desde la vertical hacia abajo."""
    return ox + fx * math.sin(ang) * length, oy + math.cos(ang) * length


def pose_angles(pose: str, ph: float, jitter: float):
    """Devuelve (lean, thighL, kneeL, thighR, kneeR, armL, elbowL, armR, elbowR, bob, tool)."""
    s = math.sin(ph)
    c = math.cos(ph)
    if pose == "pala":
        k = (s + 1) / 2
        return (0.35 + 0.35 * k, -0.25, 0.45, 0.35, 0.2, 1.1 - 0.7 * k, -0.4, 0.9 - 0.6 * k, -0.2, 0.0, "pala")
    if pose == "martillo":
        k = max(0.0, s) ** 0.5
        return (0.45, -0.6, 1.4, 0.5, 1.5, 0.5, -0.3, 2.6 - 1.8 * k, -0.8 + 0.6 * k, -0.25, "martillo")
    if pose == "carretilla":
        return (0.2, 0.45 * s, 0.3 * max(0, -s), -0.45 * s, 0.3 * max(0, s), 0.7, -0.2, 0.75, -0.2, 0.02 * abs(c), "carretilla")
    if pose == "cargar":
        return (0.05, 0.4 * s, 0.3 * max(0, -s), -0.4 * s, 0.3 * max(0, s), 2.8, -1.9, 0.3 * s, 0.1, 0.02 * abs(c), "tablon")
    if pose == "apuntar":
        return (0.0, 0.12, 0.0, -0.12, 0.0, 1.6 + 0.1 * s, 0.0, 0.4, -1.2, 0.0, "casco")
    if pose == "celebrar":
        k = (s + 1) / 2
        return (0.0, 0.15, 0.2 * k, -0.15, 0.2 * k, 2.6 + 0.3 * s, 0.2, 2.6 - 0.3 * s, -0.2, -0.06 * k, None)
    # parado
    return (0.0 + 0.03 * s, 0.08, 0.0, -0.08, 0.0, 0.15 + jitter * 0.1, -0.1, 0.1, -0.15, 0.0, None)


def draw_worker(d: ImageDraw.ImageDraw, x: float, y: float, ppm: float, pose: str, t: float,
                facing: int, colors: dict, idx: int = 0) -> None:
    """Dibuja un obrero con los pies en (x, y)."""
    u = ppm * WORKER_H / 1.75
    freq = {"pala": 1.1, "martillo": 2.6, "carretilla": 1.6, "cargar": 1.5, "celebrar": 2.2}.get(pose, 0.4)
    ph = 2 * math.pi * (t * freq + idx * 0.37)
    lean, tl, kl, tr, kr, al, el, ar, er, bob, tool = pose_angles(pose, ph, (idx % 3) * 0.3)
    fx = facing
    vest = colors["chaleco"]
    helmet = colors["casco"]
    pants = colors["pantalon"]
    lw = 0.13 * u
    hip = (x, y - (0.92 + bob) * u)
    # piernas (atrás primero)
    for thigh, knee, col in ((tr, kr, shade(pants, 0.8)), (tl, kl, pants)):
        kx, ky = _pt(*hip, 0.47 * u, thigh, fx)
        fx2, fy2 = _pt(kx, ky, 0.47 * u, thigh - knee, fx)
        fy2 = min(fy2, y)
        _limb(d, hip, (kx, ky), (fx2, fy2), lw * 1.1, col)
        d.rounded_rectangle((fx2 - 0.06 * u + fx * 0.02 * u, fy2 - 0.07 * u, fx2 + 0.1 * u * fx + 0.06 * u, fy2 + 0.01 * u), radius=0.03 * u, fill=BOOT) if fx > 0 else d.rounded_rectangle((fx2 - 0.16 * u, fy2 - 0.07 * u, fx2 + 0.06 * u, fy2 + 0.01 * u), radius=0.03 * u, fill=BOOT)
    # torso
    sh = _pt(*hip, 0.55 * u, math.pi - lean, fx)
    tw = 0.34 * u
    ang = math.atan2(sh[1] - hip[1], sh[0] - hip[0])
    nx, ny = -math.sin(ang) * tw / 2, math.cos(ang) * tw / 2
    body = [(hip[0] + nx, hip[1] + ny), (sh[0] + nx, sh[1] + ny), (sh[0] - nx, sh[1] - ny), (hip[0] - nx, hip[1] - ny)]
    d.polygon(body, fill=vest)
    mid = [(hip[0] + (sh[0] - hip[0]) * k + nx * 1.02, hip[1] + (sh[1] - hip[1]) * k + ny * 1.02) for k in (0.35, 0.45)]
    mid2 = [(hip[0] + (sh[0] - hip[0]) * k - nx * 1.02, hip[1] + (sh[1] - hip[1]) * k - ny * 1.02) for k in (0.45, 0.35)]
    d.polygon(mid + mid2, fill=(230, 230, 225))  # banda reflectante
    # cabeza
    hc = _pt(*sh, 0.2 * u, math.pi - lean * 0.8, fx)
    r = 0.12 * u
    d.ellipse((hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r), fill=SKIN)
    d.pieslice((hc[0] - r * 1.15, hc[1] - r * 1.35, hc[0] + r * 1.15, hc[1] + r * 0.75), 180, 360, fill=helmet)
    d.rectangle((hc[0] - r * 1.3 + (fx > 0) * r * 0.2, hc[1] - r * 0.33, hc[0] + r * 1.3 - (fx < 0) * r * 0.2, hc[1] - r * 0.2), fill=shade(helmet, 0.85))
    # brazos
    hands = []
    for arm, elbow, col in ((ar, er, shade(vest, 0.8)), (al, el, vest)):
        ex, ey = _pt(*sh, 0.3 * u, arm, fx)
        hx, hy = _pt(ex, ey, 0.3 * u, arm + elbow, fx)
        _limb(d, sh, (ex, ey), (hx, hy), lw, col)
        d.ellipse((hx - lw * 0.55, hy - lw * 0.55, hx + lw * 0.55, hy + lw * 0.55), fill=SKIN)
        hands.append((hx, hy))
    # herramientas
    wood = (150, 100, 55)
    if tool == "pala":
        h1, h2 = hands
        dx, dy = h2[0] - h1[0], h2[1] - h1[1]
        n = math.hypot(dx, dy) or 1
        tip = (h2[0] + dx / n * 0.55 * u, h2[1] + dy / n * 0.55 * u + 0.2 * u)
        d.line((h1[0] - dx / n * 0.1 * u, h1[1] - dy / n * 0.1 * u, tip[0], tip[1]), fill=wood, width=int(0.05 * u))
        d.polygon([(tip[0] - 0.09 * u, tip[1] - 0.05 * u), (tip[0] + 0.09 * u, tip[1] - 0.05 * u), (tip[0], tip[1] + 0.16 * u)], fill=(120, 120, 128))
    elif tool == "martillo":
        hx, hy = hands[0]
        a = ar + er
        hx2, hy2 = _pt(hx, hy, 0.3 * u, a, fx)
        d.line((hx, hy, hx2, hy2), fill=wood, width=int(0.05 * u))
        px, py = -math.cos(a) * 0.09 * u * fx, math.sin(a) * 0.09 * u
        d.line((hx2 - px, hy2 - py, hx2 + px, hy2 + py), fill=(90, 90, 95), width=int(0.08 * u))
    elif tool == "carretilla":
        hx, hy = hands[1]
        wx = hx + fx * 0.9 * u
        wy = y - 0.18 * u
        d.polygon([(hx + fx * 0.15 * u, hy - 0.05 * u), (wx + fx * 0.25 * u, wy - 0.45 * u), (wx - fx * 0.05 * u, wy - 0.05 * u), (hx + fx * 0.3 * u, hy + 0.1 * u)], fill=(40, 110, 170))
        d.ellipse((wx - 0.17 * u, wy - 0.17 * u, wx + 0.17 * u, wy + 0.17 * u), fill=(30, 30, 30))
        d.line((hx, hy, wx, wy - 0.1 * u), fill=(60, 60, 60), width=int(0.04 * u))
        ax, bx = sorted((wx - fx * 0.05 * u, wx + fx * 0.35 * u))
        d.ellipse((ax, wy - 0.62 * u, bx, wy - 0.35 * u), fill=(110, 80, 55))
    elif tool == "tablon":
        hx, hy = hands[1]
        d.line((hx - fx * 0.9 * u, hy + 0.05 * u, hx + fx * 0.8 * u, hy - 0.08 * u), fill=wood, width=int(0.09 * u))


# --- excavadora -----------------------------------------------------------------
BOOM = 3.1
STICK = 2.4


def ik2(px, py, tx, ty, l1, l2, elbow_up=True):
    dx, dy = tx - px, ty - py
    dist = max(abs(l1 - l2) + 1e-3, min(l1 + l2 - 1e-3, math.hypot(dx, dy)))
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    a = math.acos(max(-1, min(1, cos_a)))
    cands = [base - a, base + a]
    # codo "arriba" = el de menor y en pantalla (y crece hacia abajo)
    th1 = min(cands, key=lambda th: py + math.sin(th) * l1) if elbow_up else max(cands, key=lambda th: py + math.sin(th) * l1)
    ex, ey = px + math.cos(th1) * l1, py + math.sin(th1) * l1
    # el efector alcanza el punto más cercano posible
    th2 = math.atan2(ty - ey, tx - ex) if math.hypot(tx - px, ty - py) <= l1 + l2 else th1
    return (ex, ey), (ex + math.cos(th2) * l2, ey + math.sin(th2) * l2)


def draw_excavator(d: ImageDraw.ImageDraw, x: float, y: float, ppm: float, color, target, facing: int = -1,
                   bucket_curl: float = 0.0, load: float = 0.0, soil=(110, 80, 50), t: float = 0.0) -> tuple:
    """x: centro de las orugas, y: suelo bajo las orugas. target: punto (px) de la cuchara.
    Devuelve la posición final de la cuchara."""
    m = lambda v: v * ppm  # noqa: E731
    f = facing
    dark = (45, 45, 48)
    # orugas
    tl = m(3.0)
    d.rounded_rectangle((x - tl / 2, y - m(0.62), x + tl / 2, y), radius=m(0.3), fill=dark)
    for i in range(5):
        wx = x - tl / 2 + m(0.3) + i * (tl - m(0.6)) / 4
        d.ellipse((wx - m(0.2), y - m(0.51), wx + m(0.2), y - m(0.11)), fill=(90, 90, 95))
        d.ellipse((wx - m(0.07), y - m(0.38), wx + m(0.07), y - m(0.24)), fill=(40, 40, 40))
    # cuerpo
    by = y - m(0.62)
    d.rectangle((x - m(0.3), by - m(0.2), x + m(0.3), by), fill=dark)
    body = (x - m(1.3), by - m(1.0), x + m(1.4), by - m(0.2))
    d.rounded_rectangle(body, radius=m(0.12), fill=color)
    cw = (x - f * m(1.35) - m(0.35), by - m(0.95), x - f * m(1.35) + m(0.35), by - m(0.25))
    d.rounded_rectangle(cw, radius=m(0.15), fill=shade(color, 0.8))
    cab_x = x + f * m(0.55)
    cab = (min(cab_x, cab_x + f * m(1.05)), by - m(2.05), max(cab_x, cab_x + f * m(1.05)), by - m(0.95))
    d.rounded_rectangle(cab, radius=m(0.1), fill=color)
    win = (cab[0] + m(0.12), cab[1] + m(0.12), cab[2] - m(0.12), cab[3] - m(0.4))
    d.rectangle(win, fill=(150, 200, 230))
    d.line((win[0], win[3], win[2], win[1]), fill=(200, 230, 250), width=max(1, int(m(0.04))))
    # escape
    ex_x = x - f * m(0.6)
    d.rectangle((ex_x - m(0.05), by - m(1.45), ex_x + m(0.05), by - m(1.0)), fill=(70, 70, 70))
    # brazo
    pv = (x + f * m(0.2), by - m(1.0))
    elbow, tip = ik2(pv[0], pv[1], target[0], target[1], m(BOOM), m(STICK), elbow_up=True)
    w1 = m(0.34)
    d.line([pv, elbow], fill=shade(color, 0.92), width=int(w1))
    d.line([elbow, tip], fill=shade(color, 0.92), width=int(w1 * 0.75))
    for p, r in ((pv, 0.22), (elbow, 0.2), (tip, 0.14)):
        d.ellipse((p[0] - m(r), p[1] - m(r), p[0] + m(r), p[1] + m(r)), fill=shade(color, 0.7))
    # pistón
    mid = ((pv[0] * 0.3 + elbow[0] * 0.7), (pv[1] * 0.3 + elbow[1] * 0.7))
    d.line([(x + f * m(0.7), by - m(0.4)), mid], fill=(200, 200, 205), width=int(m(0.1)))
    # cuchara
    ang = math.atan2(tip[1] - elbow[1], tip[0] - elbow[0]) + (1.2 + bucket_curl * 1.5) * (-1 if f < 0 else 1) * -1
    bw, bl = m(0.75), m(0.8)
    ca, sa = math.cos(ang), math.sin(ang)

    def bp(u, v):
        return tip[0] + u * ca - v * sa, tip[1] + u * sa + v * ca

    shell = [bp(0, -bw * 0.45), bp(bl * 0.8, -bw * 0.5), bp(bl, bw * 0.1), bp(bl * 0.6, bw * 0.5), bp(0, bw * 0.4)]
    d.polygon(shell, fill=(70, 70, 74))
    for k in (-0.35, 0.0, 0.3):
        a = bp(bl * 0.95, bw * k)
        b = bp(bl * 1.12, bw * k + bw * 0.05)
        d.line([a, b], fill=(160, 160, 160), width=max(1, int(m(0.06))))
    if load > 0.02:
        c = bp(bl * 0.45, -bw * 0.05)
        r = m(0.38) * load
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r * 0.8), fill=soil)
    return tip


def draw_hose(d: ImageDraw.ImageDraw, start, end, ppm: float, t: float, pouring: bool, sag: float = 1.2) -> None:
    """Manguera de bomba de concreto: curva de Bézier desde `start` hasta la boquilla `end`."""
    m = lambda v: v * ppm  # noqa: E731
    sx, sy = start
    ex, ey = end
    c1 = (sx + (ex - sx) * 0.3, sy + m(sag) + m(0.1) * math.sin(t * 3))
    c2 = (ex, ey - m(1.6))
    pts = []
    for i in range(33):
        u = i / 32
        a = (1 - u) ** 3
        b = 3 * (1 - u) ** 2 * u
        c = 3 * (1 - u) * u * u
        e = u ** 3
        pts.append((a * sx + b * c1[0] + c * c2[0] + e * ex, a * sy + b * c1[1] + c * c2[1] + e * ey))
    d.line(pts, fill=(30, 30, 32), width=int(m(0.2)), joint="curve")
    d.line(pts, fill=(55, 55, 60), width=int(m(0.1)), joint="curve")
    d.rectangle((ex - m(0.1), ey - m(0.25), ex + m(0.1), ey), fill=(200, 60, 40))
    if pouring:
        for i in range(6):
            yy = ey + (i + (t * 8) % 1) * m(0.08)
            wob = math.sin(t * 20 + i) * m(0.02)
            d.ellipse((ex - m(0.07) + wob, yy - m(0.05), ex + m(0.07) + wob, yy + m(0.08)), fill=(140, 140, 136))
