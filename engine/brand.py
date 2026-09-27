"""Plantilla de marca del canal (brand.json): el estilo que se repite en todos los videos.

brand.json es una escena parcial con la misma forma que el esquema (engine/schema.py). Cada valor que
aparece ahí queda fijado: se sobrescribe en toda escena (generada por Claude, editada o guardada), así
que solo el contenido (textos, etapas, días, interior, callouts…) cambia de un video a otro.

Caso especial: `gancho.colores_lineas` fija el color de cada línea del gancho por posición.
Si brand.json no existe, no se fija nada.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOK_COLORS = "colores_lineas"


def brand_path() -> Path:
    return Path(os.environ.get("TF_BRAND_FILE", ROOT / "brand.json"))


_cache: dict[str, Any] = {"key": None, "brand": {}}


def load_brand() -> dict:
    """Lee y valida brand.json (se recarga solo si el archivo cambia)."""
    p = brand_path()
    key = (str(p), p.stat().st_mtime_ns) if p.is_file() else (str(p), None)
    if _cache["key"] != key:
        brand = json.loads(p.read_text(encoding="utf-8")) if key[1] is not None else {}
        _validate(brand, p)
        _cache.update(key=key, brand=brand)
    return _cache["brand"]


def _validate(brand: dict, p: Path) -> None:
    from pydantic import ValidationError

    from engine.schema import Scene

    if not isinstance(brand, dict):
        raise ValueError(f"{p}: debe ser un objeto JSON")
    colors = brand.get("gancho", {}).get(HOOK_COLORS)
    if colors is not None and (not isinstance(colors, list) or not colors):
        raise ValueError(f"{p}: gancho.{HOOK_COLORS} debe ser una lista de colores no vacía")
    try:
        Scene.model_validate(_apply(Scene().model_dump(), brand))
    except ValidationError as e:
        raise ValueError(f"{p} no es válido: {e}") from e


def _merge(dst: dict, src: dict) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)


def _apply(scene: dict, brand: dict) -> dict:
    d = copy.deepcopy(scene)
    b = copy.deepcopy(brand)
    colors = b.get("gancho", {}).pop(HOOK_COLORS, None)
    _merge(d, b)
    if colors:
        for i, ln in enumerate(d.get("gancho", {}).get("lineas") or []):
            if isinstance(ln, dict):
                ln["color"] = colors[min(i, len(colors) - 1)]
    return d


def apply_brand(scene: dict) -> dict:
    """Devuelve una copia de la escena (dict, puede ser inválida) con el estilo de marca aplicado."""
    return _apply(scene, load_brand())


def locked_paths() -> list[str]:
    """Rutas de los campos fijados por la marca (p. ej. 'tipografia.fuente', 'gancho.lineas.*.color')."""
    out: list[str] = []

    def walk(node: dict, prefix: str) -> None:
        for k, v in node.items():
            if prefix == "gancho" and k == HOOK_COLORS:
                out.append("gancho.lineas.*.color")
            elif isinstance(v, dict):
                walk(v, f"{prefix}.{k}" if prefix else k)
            else:
                out.append(f"{prefix}.{k}" if prefix else k)

    walk(load_brand(), "")
    return out
