"""Cola de renders en segundo plano. Un hilo consume la cola; cada render usa un pool multiproceso
de N núcleos (engine.render). El progreso se publica por SSE y los trabajos se pueden cancelar."""
from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field, fields
from typing import Callable, Optional

from backend.app import config, projects
from engine.render import DRAFT, RenderCancelled, render_cover, render_video

log = logging.getLogger("tf.jobs")


@dataclass
class Job:
    id: str
    project_id: str
    borrador: bool
    status: str = "en_cola"  # en_cola | renderizando | listo | error | cancelado
    progress: float = 0.0
    message: str = "En cola…"
    result: dict = field(default_factory=dict)
    error: str = ""
    created: float = field(default_factory=time.time)
    version: int = 0
    cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def public(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "cancel"}


class JobManager:
    def __init__(self, post_hook: Optional[Callable[[Job], None]] = None):
        self.jobs: dict[str, Job] = {}
        self.q: "queue.Queue[str]" = queue.Queue()
        self.cond = threading.Condition()
        self.post_hook = post_hook
        self._thread = threading.Thread(target=self._loop, daemon=True, name="render-queue")
        self._thread.start()

    def _touch(self, job: Job, **kw) -> None:
        with self.cond:
            for k, v in kw.items():
                setattr(job, k, v)
            job.version += 1
            self.cond.notify_all()

    def submit(self, project_id: str, borrador: bool) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], project_id=project_id, borrador=borrador)
        self.jobs[job.id] = job
        self.q.put(job.id)
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.jobs[job_id]
        job.cancel.set()
        if job.status == "en_cola":
            self._touch(job, status="cancelado", message="Cancelado")
        return job

    def wait_change(self, job: Job, version: int, timeout: float = 15.0) -> bool:
        with self.cond:
            return self.cond.wait_for(lambda: job.version != version, timeout=timeout)

    def _loop(self) -> None:
        while True:
            jid = self.q.get()
            job = self.jobs.get(jid)
            if job is None or job.cancel.is_set():
                continue
            self._run(job)

    def _run(self, job: Job) -> None:
        self._touch(job, status="renderizando", message="Preparando…")
        try:
            p = projects.get(job.project_id)
            scene = p.scene()
            if scene is None:
                raise RuntimeError("El proyecto no tiene escena.")
            name = "borrador.mp4" if job.borrador else "video.mp4"
            out = p.output / name
            kw = dict(size=DRAFT["size"], fps=DRAFT["fps"], ss=DRAFT["ss"], preset="veryfast") if job.borrador else {}

            def prog(f, msg):
                self._touch(job, progress=round(f * (0.97 if not job.borrador else 1.0), 4), message=msg)

            info = render_video(scene, str(out), workers=config.WORKERS, progress=prog, cancel=job.cancel,
                                project_dir=str(p.dir), fonts_dir=str(p.uploads), **kw)
            files = [name]
            if not job.borrador:
                if scene.exportacion.portada.generar:
                    self._touch(job, message="Generando portada…")
                    render_cover(scene, str(p.output / "portada.png"), fonts_dir=str(p.uploads))
                    files.append("portada.png")
                if scene.exportacion.texto_publicacion and self.post_hook:
                    self._touch(job, message="Escribiendo texto de publicación con Claude…")
                    try:
                        self.post_hook(job)
                        files.append("publicacion.txt")
                    except Exception as e:  # el video ya está listo: no falla todo el trabajo
                        info["post_error"] = str(e)
            info["files"] = files
            self._touch(job, status="listo", progress=1.0, message="Listo", result=info)
        except RenderCancelled:
            self._touch(job, status="cancelado", message="Cancelado")
        except Exception as e:
            log.error("render falló: %s", traceback.format_exc())
            self._touch(job, status="error", message="Error", error=str(e))
