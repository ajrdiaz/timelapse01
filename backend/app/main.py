"""API de TimelapseForge (FastAPI)."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import logging
import random
import secrets
import shutil
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from backend.app import config, projects
from backend.app.jobs import JobManager
from backend.app.llm import LLMError, claude_available, structured
from backend.app.prompts import (EDIT_SYSTEM, IdeasResponse, PostText, SceneOnly, SceneResponse, edit_prompt,
                                 ideas_prompt, post_prompt, scene_prompt, system, POST_SYSTEM)
from engine.brand import apply_brand, brand_path, load_brand, locked_paths
from engine.catalog import INTERIOR_TYPES, MACHINES, POSES, PROGRESSIONS, STAGE_TYPES, TONES
from engine.interiors import INTERIORS
from engine.schema import Scene, chain_starts, coherence_errors, rescale_times

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tf.api")
load_brand()  # un brand.json inválido debe fallar al arrancar, no a mitad de un render
app = FastAPI(title="TimelapseForge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- errores uniformes ----------------------------------------------------------------
def err(status: int, code: str, message: str, details: Optional[list] = None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or []}})


def validation_details(e: ValidationError) -> list[str]:
    out = []
    for x in e.errors():
        loc = ".".join(str(p) for p in x["loc"])
        msg = x["msg"].replace("Value error, ", "")
        out.append(f"{loc}: {msg}" if loc else msg)
    return out


@app.exception_handler(LLMError)
async def _llm_err(_: Request, e: LLMError):
    return err(502 if e.code != "claude_auth" else 401, e.code, str(e), e.details)


@app.exception_handler(ValidationError)
async def _val_err(_: Request, e: ValidationError):
    return err(422, "invalid_scene", "El JSON de escena no es válido.", validation_details(e))


@app.exception_handler(KeyError)
async def _key_err(_: Request, e: KeyError):
    return err(404, "not_found", f"No existe: {e}")


def parse_scene(d: dict) -> Scene:
    return Scene.model_validate(apply_brand(d))


# --- salud y catálogo -----------------------------------------------------------------
@app.get("/api/health")
def health():
    ff = shutil.which("ffmpeg")
    cl = claude_available()
    return {"ffmpeg": {"ok": bool(ff), "path": ff, "detail": "" if ff else "Falta ffmpeg: instálalo (ver README)."},
            "claude": cl, "model": config.CLAUDE_MODEL, "workers": config.WORKERS}


@app.get("/api/catalog")
def catalog():
    return {
        "stage_types": STAGE_TYPES, "poses": POSES, "machines": MACHINES, "tones": TONES,
        "interiors": {k: {"descripcion": v, "objetos": {o: lab for o, (lab, *_r) in INTERIORS[k].OBJECTS.items()}}
                      for k, v in INTERIOR_TYPES.items()},
    }


@app.get("/api/schema")
def schema():
    return Scene.model_json_schema()


@app.get("/api/defaults")
def defaults():
    return apply_brand(Scene().model_dump())


@app.get("/api/brand")
def brand():
    """Estilo fijo del canal: valores de brand.json y rutas de campos bloqueados en el editor."""
    return {"archivo": str(brand_path()), "valores": load_brand(), "campos": locked_paths()}


# --- proyectos --------------------------------------------------------------------------
class NewProject(BaseModel):
    titulo: str = ""
    tema: str = ""


@app.get("/api/projects")
def list_projects():
    return projects.list_all()


@app.post("/api/projects")
def new_project(body: NewProject):
    return projects.create(body.titulo, body.tema).summary()


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = projects.get(pid)
    return {**p.summary(), "ideas": p.ideas(), "idea": p.idea(), "descripcion_md": p.descripcion(),
            "scene": p.scene_dict(), "history_list": p.history_list(), "uploads": _uploads(p),
            "publicacion": p.publicacion()}


def _uploads(p) -> dict:
    files = sorted(f.name for f in p.uploads.iterdir() if f.is_file()) if p.uploads.exists() else []
    return {"fonts": [f for f in files if Path(f).suffix.lower() in FONT_EXT],
            "music": [f for f in files if Path(f).suffix.lower() in MUSIC_EXT]}


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    p = projects.get(pid)
    shutil.rmtree(p.dir)
    return {"ok": True}


class SceneBody(BaseModel):
    scene: dict
    note: str = ""


@app.put("/api/projects/{pid}/scene")
def save_scene(pid: str, body: SceneBody):
    p = projects.get(pid)
    s = parse_scene(body.scene)
    v = p.save_scene(s, body.note or "edición manual")
    return {"ok": True, "version": v, "scene": s.model_dump()}


@app.post("/api/projects/{pid}/undo")
def undo(pid: str):
    p = projects.get(pid)
    prev = p.undo()
    if prev is None:
        return err(409, "no_history", "No hay versiones anteriores.")
    return {"scene": prev, "history": p.history_list()}


class MdBody(BaseModel):
    descripcion_md: str


@app.put("/api/projects/{pid}/descripcion")
def save_md(pid: str, body: MdBody):
    projects.get(pid).save_descripcion(body.descripcion_md)
    return {"ok": True}


# --- validación / reescalado --------------------------------------------------------------
@app.post("/api/validate")
def validate(body: SceneBody):
    try:
        s = parse_scene(body.scene)
        return {"ok": True, "errors": [], "scene": s.model_dump()}
    except ValidationError as e:
        return {"ok": False, "errors": validation_details(e)}


class RescaleBody(BaseModel):
    scene: dict
    duracion_seg: Optional[float] = None
    solo_encadenar: bool = False


@app.post("/api/rescale")
def rescale(body: RescaleBody):
    d = chain_starts(body.scene) if body.solo_encadenar else rescale_times(body.scene, body.duracion_seg)
    return {"scene": d}


# --- LLM: ideas, escena, edición, publicación ------------------------------------------------
class IdeasBody(BaseModel):
    tema: str = ""
    duracion_seg: float = Field(62, ge=15, le=180)
    tono: str = ""
    idioma: str = "es"
    project_id: Optional[str] = None


@app.post("/api/ideas")
async def ideas(body: IdeasBody):
    res = await structured(system("ideas"), ideas_prompt(body.tema, body.duracion_seg, body.tono, body.idioma,
                                                         projects.used_ideas()), IdeasResponse)
    p = projects.get(body.project_id) if body.project_id else projects.create(body.tema or "Nuevo video", body.tema)
    data = [i.model_dump() for i in res.ideas]
    p.save_ideas(data)
    p.update_meta(tema=body.tema, duracion_seg=body.duracion_seg, idioma=body.idioma)
    return {"project_id": p.id, "ideas": data}


class SceneReq(BaseModel):
    project_id: str
    idea: dict
    duracion_seg: float = Field(62, ge=15, le=180)
    idioma: str = "es"


def _normalize_llm_scene(d: dict) -> dict:
    """Arregla la aritmética de tiempos (el LLM suele desviarse unas décimas) y aplica el estilo de marca
    antes de validar."""
    if isinstance(d.get("scene"), dict):
        d = {**d, "scene": apply_brand(rescale_times(d["scene"]))}
    return d


def _music_for_new_video(recent: int = 3) -> tuple[int, str]:
    """Semilla y progresión al azar para un video nuevo (la semilla fija el arreglo de la música). Se evitan
    las progresiones de los últimos videos para que no suenen parecidos seguidos."""
    seed = secrets.randbelow(2**31)
    used = []
    for m in projects.list_all():
        d = projects.Project(m["id"]).scene_dict()
        if d:
            used.append(d.get("audio", {}).get("progresion"))
        if len(used) >= recent:
            break
    options = [p for p in PROGRESSIONS if p not in used] or list(PROGRESSIONS)
    return seed, random.Random(seed).choice(options)


@app.post("/api/scene")
async def make_scene(body: SceneReq):
    p = projects.get(body.project_id)
    base = rescale_times(apply_brand(Scene().model_dump()), body.duracion_seg)
    base["general"]["idioma"] = body.idioma
    seed, progresion = _music_for_new_video()

    def prep(d):
        d = _normalize_llm_scene(d)
        d["scene"]["general"]["seed"] = seed
        d["scene"]["audio"]["progresion"] = progresion
        d["scene"]["general"]["duracion_seg"] = body.duracion_seg
        d["scene"] = rescale_times(d["scene"], body.duracion_seg)
        return d

    res = await structured(system("scene"), scene_prompt(body.idea, body.duracion_seg, body.idioma, base),
                           SceneResponse, prepare=prep)
    p.save_idea(body.idea)
    p.save_descripcion(res.descripcion_md)
    p.save_scene(res.scene, "generada por Claude", reset_history=True)
    post = res.publicacion.model_dump() if res.publicacion else None
    if post:
        p.save_publicacion(post)
    else:  # Claude no lo incluyó: se pide aparte, sin hacer fallar el guion
        try:
            post = await generate_post(p)
        except Exception as e:
            log.warning("no se pudo generar el texto de publicación: %s", e)
    return {"descripcion_md": res.descripcion_md, "scene": res.scene.model_dump(), "history": p.history_list(),
            "publicacion": post}


class EditReq(BaseModel):
    project_id: str
    instruccion: str = Field(min_length=2, max_length=1000)
    scene: Optional[dict] = None


@app.post("/api/scene/edit")
async def edit_scene(body: EditReq):
    p = projects.get(body.project_id)
    cur = body.scene or p.scene_dict()
    if not cur:
        return err(409, "no_scene", "El proyecto aún no tiene escena.")
    res = await structured(system("edit"), edit_prompt(cur, body.instruccion), SceneOnly, prepare=_normalize_llm_scene)
    p.save_scene(res.scene, f"Claude: {body.instruccion[:80]}")
    return {"scene": res.scene.model_dump(), "cambios": res.cambios, "history": p.history_list()}


async def generate_post(p: projects.Project) -> dict:
    s = p.scene()
    res = await structured(POST_SYSTEM, post_prompt(s, p.descripcion()), PostText)
    data = res.model_dump()
    p.save_publicacion(data)
    return data


@app.post("/api/projects/{pid}/post-text")
async def post_text(pid: str):
    p = projects.get(pid)
    if p.scene() is None:
        return err(409, "no_scene", "El proyecto aún no tiene escena.")
    return await generate_post(p)


def _post_hook(job):
    """Tras el render: solo se escribe si aún no existe (no se pisa el texto que ya se copió)."""
    p = projects.get(job.project_id)
    if p.publicacion() is None:
        asyncio.run(generate_post(p))


jobs = JobManager(post_hook=_post_hook)


# --- vista previa ------------------------------------------------------------------------
_renderers: "OrderedDict[str, Any]" = OrderedDict()
_rlock = threading.Lock()
PREVIEW_SIZE = (540, 960)


def _renderer(scene: Scene, fonts_dir: Optional[str], ss: int):
    from engine.frame import FrameRenderer

    key = hashlib.sha1((scene.model_dump_json() + str(fonts_dir) + str(ss)).encode()).hexdigest()
    with _rlock:
        if key in _renderers:
            _renderers.move_to_end(key)
            return _renderers[key]
        fr = FrameRenderer(scene, size=PREVIEW_SIZE, ss=ss, preview=True, fonts_dir=fonts_dir)
        _renderers[key] = fr
        while len(_renderers) > 3:
            _renderers.popitem(last=False)
        return fr


class PreviewReq(BaseModel):
    scene: dict
    times: list[float] = Field(min_length=1, max_length=40)
    project_id: Optional[str] = None
    calidad: int = Field(2, ge=1, le=2, description="1 = rápido (sin supermuestreo), 2 = normal")
    guias: bool = True


_preview_lock = threading.Lock()


@app.post("/api/preview")
async def preview(body: PreviewReq):
    s = parse_scene(body.scene)
    fonts = str(projects.get(body.project_id).uploads) if body.project_id else None

    def work():
        with _preview_lock:
            fr = _renderer(s, fonts, body.calidad)
            out = []
            for t in body.times:
                t = max(0.0, min(s.general.duracion_seg - 1e-3, t))
                img = fr.render(t, preview=body.guias)
                buf = io.BytesIO()
                img.save(buf, "PNG", compress_level=1)
                out.append({"t": t, "png": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()})
            return out

    return {"frames": await asyncio.to_thread(work)}


# --- render ------------------------------------------------------------------------------
class RenderReq(BaseModel):
    project_id: str
    borrador: bool = False


@app.post("/api/render")
def render(body: RenderReq):
    if not shutil.which("ffmpeg"):
        return err(500, "ffmpeg_missing", "Falta ffmpeg: instálalo y reinicia (ver README).")
    p = projects.get(body.project_id)
    if p.scene() is None:
        return err(409, "no_scene", "El proyecto aún no tiene escena.")
    return jobs.submit(p.id, body.borrador).public()


@app.get("/api/jobs/{jid}")
def job(jid: str):
    return jobs.jobs[jid].public()


@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: str):
    return jobs.cancel(jid).public()


@app.get("/api/jobs/{jid}/events")
async def job_events(jid: str, request: Request):
    job = jobs.jobs[jid]

    async def gen():
        version = -1
        while True:
            if await request.is_disconnected():
                break
            if job.version != version:
                version = job.version
                yield f"data: {json.dumps(job.public(), ensure_ascii=False)}\n\n"
                if job.status in ("listo", "error", "cancelado"):
                    break
            else:
                changed = await asyncio.to_thread(jobs.wait_change, job, version, 10.0)
                if not changed:
                    yield ": ping\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --- archivos ------------------------------------------------------------------------------
FONT_EXT = {".ttf", ".otf", ".woff", ".woff2"}
MUSIC_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


@app.post("/api/projects/{pid}/upload")
async def upload(pid: str, file: UploadFile = File(...)):
    p = projects.get(pid)
    name = Path(file.filename or "archivo").name
    ext = Path(name).suffix.lower()
    if ext not in FONT_EXT | MUSIC_EXT:
        return err(400, "bad_file", "Solo se aceptan fuentes (.ttf/.otf/.woff) o audio (.mp3/.wav/.m4a/.ogg/.flac).")
    p.uploads.mkdir(parents=True, exist_ok=True)
    data = await file.read()
    if len(data) > 60 * 1024 * 1024:
        return err(400, "too_big", "Archivo demasiado grande (máx. 60 MB).")
    (p.uploads / name).write_bytes(data)
    kind = "fuente" if ext in FONT_EXT else "musica"
    if kind == "fuente":
        try:
            from PIL import ImageFont

            ImageFont.truetype(str(p.uploads / name), 20)
        except Exception:
            (p.uploads / name).unlink()
            return err(400, "bad_font", "La fuente no se pudo leer.")
    return {"filename": name, "kind": kind}


@app.get("/api/projects/{pid}/files/{name}")
def get_file(pid: str, name: str, download: bool = False):
    p = projects.get(pid)
    path = (p.output / Path(name).name)
    if not path.is_file():
        return err(404, "not_found", "Archivo no encontrado.")
    return FileResponse(path, filename=path.name if download else None)


# --- frontend compilado (modo producción) ---------------------------------------------------
_dist = config.ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
