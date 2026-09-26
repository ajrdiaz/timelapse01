"""Clase base de etapa, contexto de dibujo y registro."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from PIL import Image, ImageDraw

from engine.world import Layout, ease, lerp, seg


@dataclass
class WorldState:
    """Estado acumulado por las etapas (lo que no pertenece a una sola etapa)."""
    pile: float = 0.0  # montón de tierra 0..1
    dig: float = 0.0  # progreso de excavación 0..1
    fill: float = 0.0  # progreso del relleno 0..1
    interior: float = 0.0  # 0 = oscuro/vacío, 1 = amueblado


@dataclass
class SfxEvent:
    t: float
    name: str
    gain: float = 1.0
    dur: float = 0.0  # para sonidos continuos (motor, vertido)


@dataclass
class Ctx:
    L: Layout
    A: object  # engine.assets.Assets
    scene: object
    etapa: object
    index: int
    t: float  # tiempo global (s)
    current: bool
    state: WorldState
    draw: object = None  # ImageDraw sobre el lienzo
    night: float = 0.0
    draw_cache: dict = field(default_factory=dict)

    @property
    def m(self) -> Callable[[float], float]:
        return self.L.m


REGISTRY: dict[str, type["Stage"]] = {}


def register(cls):
    REGISTRY[cls.tipo] = cls
    return cls


class Stage:
    tipo = "base"
    live = False  # True: se redibuja cada fotograma aunque haya terminado
    #: sonidos de obra por defecto (nombre, golpes por segundo)
    ambience: list[tuple[str, float]] = []

    def __init__(self, etapa):
        self.e = etapa

    # estado acumulado --------------------------------------------------------
    def apply_state(self, st: WorldState, t: float) -> None:  # noqa: D401
        pass

    # dibujo persistente (se cachea cuando la etapa ya terminó) ----------------
    def draw(self, canvas: Image.Image, t: float, ctx: Ctx) -> None:
        pass

    # dibujo transitorio solo mientras la etapa está activa --------------------
    def draw_active(self, canvas: Image.Image, t: float, ctx: Ctx) -> None:
        pass

    # obreros -------------------------------------------------------------------
    def worker_spots(self, ctx: Ctx, t: float) -> list[tuple[float, float, int]]:
        L = ctx.L
        n = self.e.obreros
        xs = [L.pit_x0 + L.m(0.4) + i * L.m(1.1) for i in range(n)]
        return [(x, L.ground_y, 1 if i % 2 == 0 else -1) for i, x in enumerate(xs)]

    # máquina -------------------------------------------------------------------
    def pour_point(self, ctx: Ctx, t: float) -> Optional[tuple[float, float]]:
        return None

    def excavator(self, ctx: Ctx, t: float) -> Optional[dict]:
        """Posición y objetivo de la excavadora cuando la etapa la usa."""
        L = ctx.L
        x = L.pit_x1 + L.m(1.7)
        ph = (ctx.t * 0.4) % 1
        tgt = (L.pit_x1 - L.m(0.5), L.ground_y - L.m(1.2) + math.sin(ph * 2 * math.pi) * L.m(0.3))
        return {"x": x, "y": L.ground_y, "target": tgt, "curl": 0.2, "load": 0.0}

    # sonido --------------------------------------------------------------------
    def sfx_events(self, t0: float, t1: float) -> list[SfxEvent]:
        """Eventos de sonido de la etapa entre t0 y t1 (segundos absolutos)."""
        ev: list[SfxEvent] = []
        if not self.e.sfx:
            return ev
        mach = self.e.maquina
        if mach == "excavadora":
            ev.append(SfxEvent(t0, "motor", 0.6, t1 - t0))
        elif mach == "bomba_concreto":
            ev.append(SfxEvent(t0, "vertido", 0.55, t1 - t0))
        for name, rate in self.ambience:
            if rate <= 0:
                continue
            n = int((t1 - t0) * rate)
            for i in range(n):
                tt = t0 + (i + 0.5) / rate
                ev.append(SfxEvent(tt, name, 0.7 + 0.3 * ((i * 7919) % 5) / 5))
        return ev


# --- geometría compartida ------------------------------------------------------
N_LAYERS = 4


def dig_profile(L: Layout, p: float) -> tuple[float, float, float]:
    """(profundidad completa, profundidad de la capa en curso, x del frente) en px."""
    p = max(0.0, min(1.0, p))
    ld = L.pit_depth / N_LAYERS
    k = min(N_LAYERS - 1, int(p * N_LAYERS))
    f = p * N_LAYERS - k
    if p >= 1.0:
        return L.pit_depth, L.pit_depth, L.pit_x1
    return k * ld, (k + 1) * ld, lerp(L.pit_x0, L.pit_x1, ease(f))


def dig_poly(L: Layout, p: float) -> list[tuple[float, float]]:
    dl, dn, xf = dig_profile(L, p)
    g = L.ground_y
    slope = L.m(0.35)
    if p <= 0:
        return []
    pts = [(L.pit_x0, g - 2), (L.pit_x1, g - 2)]
    if p >= 1:
        return pts + [(L.pit_x1, g + dl), (L.pit_x0, g + dl)]
    xf2 = max(L.pit_x0, min(L.pit_x1, xf))
    pts += [(L.pit_x1, g + dl), (min(L.pit_x1, xf2 + slope), g + dl), (xf2, g + dn), (L.pit_x0, g + dn)]
    return pts


def dig_floor(L: Layout, p: float, x: float) -> float:
    dl, dn, xf = dig_profile(L, p)
    if x < L.pit_x0 or x > L.pit_x1:
        return L.ground_y
    return L.ground_y + (dn if x <= xf else dl)


def fill_level(L: Layout, p: float) -> float:
    return lerp(L.pit_bot_y, L.ground_y, ease(p))


__all__ = [
    "Stage", "Ctx", "WorldState", "SfxEvent", "register", "REGISTRY", "dig_profile", "dig_poly",
    "dig_floor", "fill_level", "seg", "ease", "lerp", "ImageDraw",
]
