"""Registro de tipos de etapa. Cada módulo registra su clase con @register."""
from engine.stages import (  # noqa: F401
    acabados, cierre, excavacion, grava_acero, impermeabilizacion, losa, marcado, muros,
    pregunta, relleno, revelacion, techo, terminado,
)
from engine.stages.base import REGISTRY, Ctx, SfxEvent, Stage, WorldState


def make_stage(etapa) -> Stage:
    return REGISTRY[etapa.tipo](etapa)


__all__ = ["REGISTRY", "Ctx", "SfxEvent", "Stage", "WorldState", "make_stage"]
