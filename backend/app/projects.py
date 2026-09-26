"""Persistencia de proyectos en disco: projects/<id>/ con scene.json, ideas.json, historial, previews y output."""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from backend.app import config
from engine.schema import Scene

_lock = threading.RLock()
MAX_HISTORY = 100


def _read(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


class Project:
    def __init__(self, pid: str):
        if not re.fullmatch(r"[a-z0-9-]{4,64}", pid):
            raise KeyError(pid)
        self.id = pid
        self.dir = config.PROJECTS_DIR / pid

    # rutas
    @property
    def meta_path(self): return self.dir / "project.json"
    @property
    def scene_path(self): return self.dir / "scene.json"
    @property
    def history_dir(self): return self.dir / "history"
    @property
    def previews(self): return self.dir / "previews"
    @property
    def output(self): return self.dir / "output"
    @property
    def uploads(self): return self.dir / "uploads"

    def exists(self) -> bool:
        return self.meta_path.exists()

    def meta(self) -> dict:
        return _read(self.meta_path, {})

    def update_meta(self, **kw) -> dict:
        with _lock:
            m = self.meta()
            m.update(kw, updated=time.time())
            _write(self.meta_path, m)
            return m

    # contenido
    def ideas(self): return _read(self.dir / "ideas.json", [])
    def save_ideas(self, ideas): _write(self.dir / "ideas.json", ideas)
    def idea(self): return _read(self.dir / "idea.json")
    def save_idea(self, idea): _write(self.dir / "idea.json", idea)

    def descripcion(self) -> str:
        p = self.dir / "descripcion.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def save_descripcion(self, md: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "descripcion.md").write_text(md, encoding="utf-8")

    def scene_dict(self) -> Optional[dict]:
        return _read(self.scene_path)

    def scene(self) -> Optional[Scene]:
        d = self.scene_dict()
        return Scene.model_validate(d) if d else None

    def history(self) -> list[Path]:
        return sorted(self.history_dir.glob("scene_*.json"))

    def save_scene(self, scene: Scene, note: str = "") -> int:
        """Guarda la escena validada y añade una versión al historial."""
        with _lock:
            data = scene.model_dump()
            if self.scene_dict() == data:
                return len(self.history())
            hist = self.history()
            n = int(hist[-1].stem.split("_")[1]) + 1 if hist else 1
            _write(self.history_dir / f"scene_{n:04d}.json", {"note": note, "time": time.time(), "scene": data})
            for old in hist[: max(0, len(hist) + 1 - MAX_HISTORY)]:
                old.unlink(missing_ok=True)
            _write(self.scene_path, data)
            self.update_meta(titulo=scene.general.titulo)
            return n

    def undo(self) -> Optional[dict]:
        """Descarta la última versión y restaura la anterior."""
        with _lock:
            hist = self.history()
            if len(hist) < 2:
                return None
            hist[-1].unlink()
            prev = _read(hist[-2])["scene"]
            _write(self.scene_path, prev)
            return prev

    def history_list(self) -> list[dict]:
        out = []
        for p in self.history():
            d = _read(p, {})
            out.append({"version": int(p.stem.split("_")[1]), "note": d.get("note", ""), "time": d.get("time")})
        return out

    def outputs(self) -> list[str]:
        if not self.output.exists():
            return []
        return sorted(p.name for p in self.output.iterdir() if p.is_file())

    def summary(self) -> dict:
        m = self.meta()
        return {**m, "id": self.id, "has_scene": self.scene_path.exists(), "outputs": self.outputs(),
                "history": len(self.history())}


def create(titulo: str = "", tema: str = "") -> Project:
    pid = time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]
    p = Project(pid)
    for d in (p.dir, p.previews, p.output, p.uploads, p.history_dir):
        d.mkdir(parents=True, exist_ok=True)
    _write(p.meta_path, {"id": pid, "titulo": titulo or "Proyecto sin título", "tema": tema,
                         "created": time.time(), "updated": time.time()})
    return p


def get(pid: str) -> Project:
    p = Project(pid)
    if not p.exists():
        raise KeyError(pid)
    return p


def list_all() -> list[dict]:
    if not config.PROJECTS_DIR.exists():
        return []
    out = []
    for d in config.PROJECTS_DIR.iterdir():
        try:
            p = Project(d.name)
            if p.exists():
                out.append(p.summary())
        except KeyError:
            continue
    return sorted(out, key=lambda x: x.get("updated", 0), reverse=True)
