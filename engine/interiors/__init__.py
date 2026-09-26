"""Interiores de revelación. Cada módulo registra su interior con sus OBJECTS."""
from engine.interiors import bodega_snacks, cine, gamer, gimnasio, oficina, spa, streaming  # noqa: F401
from engine.interiors.base import INTERIORS, Interior

__all__ = ["INTERIORS", "Interior"]
