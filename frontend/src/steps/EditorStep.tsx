import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, chainStarts, type Catalog, type Job, type Project, type Scene } from "../api";
import ErrorBox from "../components/ErrorBox";
import JobProgress, { useJob } from "../components/JobProgress";
import { FieldEditor, SECTIONS, Section, type FormCtx } from "../components/SchemaForm";
import Spinner from "../components/Spinner";

/** Convierte los mensajes de validación del backend en rutas del formulario. */
function mapErrors(errors: string[]): { byPath: Record<string, string[]>; general: string[] } {
  const byPath: Record<string, string[]> = {};
  const general: string[] = [];
  const push = (p: string, m: string) => ((byPath[p] ??= []).push(m));
  for (const e of errors) {
    const i = e.indexOf(": ");
    const loc = i > 0 ? e.slice(0, i) : "";
    const msg = i > 0 ? e.slice(i + 2) : e;
    if (loc && !msg.startsWith("Incoherencias")) {
      push(loc, msg);
      continue;
    }
    for (const part of msg.replace(/^Incoherencias:\s*/, "").split(" | ")) {
      general.push(part);
      const m = part.match(/^([a-z_]+(?:\.[a-z_]+)*)(?:\[(\d+)\])?(?:\.([a-z_]+))?/);
      if (m) push([m[1], m[2], m[3]].filter((x) => x !== undefined).join("."), part);
      for (const mm of part.matchAll(/etapas\[(\d+)\]/g)) push(`etapas.${mm[1]}`, part);
    }
  }
  return { byPath, general };
}

function sectionErrors(byPath: Record<string, string[]>, key: string) {
  return Object.keys(byPath).filter((p) => p === key || p.startsWith(key + ".")).length;
}

const STAGE_COLORS = ["#f59e0b", "#84cc16", "#06b6d4", "#a855f7", "#ef4444", "#10b981", "#3b82f6", "#eab308", "#ec4899", "#14b8a6", "#f97316", "#8b5cf6", "#22c55e"];

export default function EditorStep({ project, schema, catalog, onSaved, onRender }: {
  project: Project;
  schema: any;
  catalog: Catalog | null;
  onSaved: (s: Scene) => void;
  onRender: () => void;
}) {
  const [scene, setScene] = useState<Scene>(project.scene!);
  const [saved, setSaved] = useState<Scene>(project.scene!);
  const [errors, setErrors] = useState<string[]>([]);
  const [valid, setValid] = useState(true);
  const [t, setT] = useState<number>(() => {
    const rev = project.scene!.etapas.find((e: any) => e.tipo === "revelacion");
    return rev ? rev.inicio_seg + 2 : 10;
  });
  const [frame, setFrame] = useState<string | null>(null);
  const [frameBusy, setFrameBusy] = useState(false);
  const [thumbs, setThumbs] = useState<{ t: number; png: string }[]>([]);
  const [thumbBusy, setThumbBusy] = useState(false);
  const [guides, setGuides] = useState(true);
  const [err, setErr] = useState<unknown>(null);
  const [uploads, setUploads] = useState<{ fonts: string[]; music: string[] }>({ fonts: [], music: [] });
  const [history, setHistory] = useState(project.history_list?.length ?? 0);
  const [draftJob, setDraftJob] = useState<string | null>(null);
  const [draftUrl, setDraftUrl] = useState<string | null>(null);
  const job = useJob(draftJob, (j: Job) => {
    if (j.status === "listo") setDraftUrl(`/api/projects/${project.id}/files/borrador.mp4?v=${Date.now()}`);
  });
  const dirty = JSON.stringify(scene) !== JSON.stringify(saved);
  const reqId = useRef(0);

  useEffect(() => {
    api.get<any>(`/api/projects/${project.id}`).then((p) => setUploads(p.uploads ?? { fonts: [], music: [] }));
  }, [project.id]);

  // validación en vivo
  useEffect(() => {
    const h = setTimeout(async () => {
      const r = await api.post<{ ok: boolean; errors: string[] }>("/api/validate", { scene }).catch(() => null);
      if (!r) return;
      setValid(r.ok);
      setErrors(r.errors);
    }, 300);
    return () => clearTimeout(h);
  }, [scene]);

  // fotograma de vista previa
  useEffect(() => {
    if (!valid) return;
    const id = ++reqId.current;
    const h = setTimeout(async () => {
      setFrameBusy(true);
      try {
        const r = await api.post<{ frames: { png: string }[] }>("/api/preview", {
          scene, times: [t], project_id: project.id, calidad: 2, guias: guides,
        });
        if (id === reqId.current) setFrame(r.frames[0].png);
      } catch (e) {
        if (id === reqId.current) setErr(e);
      } finally {
        if (id === reqId.current) setFrameBusy(false);
      }
    }, 250);
    return () => clearTimeout(h);
  }, [scene, t, valid, guides, project.id]);

  const refreshThumbs = useCallback(async () => {
    setThumbBusy(true);
    try {
      const times = scene.etapas.map((e: any) =>
        e.tipo === "revelacion" ? e.inicio_seg + Math.min(e.duracion_seg - 0.1, (scene.revelacion.flash_offset_seg ?? 0) + 1.5) : e.inicio_seg + e.duracion_seg * 0.6);
      const r = await api.post<{ frames: { t: number; png: string }[] }>("/api/preview", {
        scene, times, project_id: project.id, calidad: 1, guias: false,
      });
      setThumbs(r.frames);
    } catch (e) {
      setErr(e);
    } finally {
      setThumbBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene, project.id]);

  useEffect(() => {
    if (valid && thumbs.length === 0) refreshThumbs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valid]);

  const { byPath, general } = useMemo(() => mapErrors(errors), [errors]);

  const update = (key: string, v: any) => {
    let s = { ...scene, [key]: v };
    if (key === "etapas" || key === "gancho") s = chainStarts(s);
    setScene(s);
  };

  const save = async (note = "") => {
    setErr(null);
    try {
      const r = await api.put<{ scene: Scene; version: number }>(`/api/projects/${project.id}/scene`, { scene, note });
      setSaved(r.scene);
      setScene(r.scene);
      setHistory(r.version);
      onSaved(r.scene);
      return true;
    } catch (e) {
      setErr(e);
      return false;
    }
  };

  const undo = async () => {
    setErr(null);
    try {
      const r = await api.post<{ scene: Scene; history: any[] }>(`/api/projects/${project.id}/undo`);
      setScene(r.scene);
      setSaved(r.scene);
      setHistory(r.history.length);
      onSaved(r.scene);
    } catch (e) {
      setErr(e);
    }
  };

  const rescale = async () => {
    const r = await api.post<{ scene: Scene }>("/api/rescale", { scene, duracion_seg: scene.general.duracion_seg });
    setScene(r.scene);
  };

  const draft = async () => {
    if (dirty && !(await save("antes de borrador"))) return;
    setDraftUrl(null);
    try {
      const j = await api.post<Job>("/api/render", { project_id: project.id, borrador: true });
      setDraftJob(j.id);
    } catch (e) {
      setErr(e);
    }
  };

  const ctx: FormCtx = {
    defs: schema.$defs ?? {},
    catalog,
    scene,
    errorsByPath: byPath,
    uploads,
    onUpload: async (file: File) => {
      try {
        const r = await api.upload<{ filename: string; kind: string }>(`/api/projects/${project.id}/upload`, file);
        if (r.kind === "fuente") {
          setUploads((u) => ({ ...u, fonts: [...new Set([...u.fonts, r.filename])] }));
          setScene((s) => ({ ...s, tipografia: { ...s.tipografia, fuente: r.filename } }));
        } else {
          setUploads((u) => ({ ...u, music: [...new Set([...u.music, r.filename])] }));
          setScene((s) => ({ ...s, audio: { ...s.audio, musica_propia: r.filename } }));
        }
      } catch (e) {
        setErr(e);
      }
    },
  };

  const dur = Number(scene.general?.duracion_seg ?? 62);
  const stageSum = scene.etapas.reduce((a: number, e: any) => a + Number(e.duracion_seg || 0), 0) + Number(scene.gancho?.duracion_seg ?? 0);

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
      <div className="space-y-2">
        <div className="sticky top-0 z-20 -mx-1 flex flex-wrap items-center gap-2 bg-zinc-950/95 px-1 py-2 backdrop-blur">
          <button onClick={() => save()} disabled={!dirty || !valid}
            className="rounded-md bg-yellow-400 px-3 py-1.5 text-sm font-bold text-zinc-950 hover:bg-yellow-300 disabled:opacity-40">
            {dirty ? "Guardar" : "Guardado ✓"}
          </button>
          <button onClick={undo} disabled={history < 2} className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm hover:bg-zinc-700 disabled:opacity-40"
            title="Vuelve a la versión guardada anterior">
            ↶ Deshacer ({Math.max(0, history - 1)})
          </button>
          {dirty && <button onClick={() => setScene(saved)} className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm hover:bg-zinc-700">Descartar cambios</button>}
          <button onClick={rescale} className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm hover:bg-zinc-700" title="Reparte las duraciones de forma proporcional hasta llenar la duración total">
            ⇔ Reescalar tiempos
          </button>
          <button onClick={draft} disabled={!valid || job?.status === "renderizando"} className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm hover:bg-zinc-700 disabled:opacity-40">
            ⚡ Borrador rápido
          </button>
          <button onClick={async () => { if (!dirty || (await save())) onRender(); }} disabled={!valid}
            className="ml-auto rounded-md bg-emerald-500 px-3 py-1.5 text-sm font-bold text-zinc-950 hover:bg-emerald-400 disabled:opacity-40">
            Render final →
          </button>
        </div>
        {!valid && (
          <ErrorBox error={new ApiError("La escena tiene errores de validación", "invalid_scene", general.length ? general : errors)} />
        )}
        <ErrorBox error={err} onClose={() => setErr(null)} />
        {SECTIONS.map(([key, title]) => {
          const n = schema.properties[key];
          const extra = key === "etapas" ? (
            <span className={`text-xs ${Math.abs(stageSum - dur) > 0.05 ? "text-red-400" : "text-zinc-500"}`}>
              suma {stageSum.toFixed(1)} / {dur} s
            </span>
          ) : null;
          return (
            <Section key={key} title={title} errors={sectionErrors(byPath, key)} defaultOpen={key === "general" || key === "etapas"} extra={extra}>
              {key === "etapas" ? (
                <>
                  <div className="py-2 text-xs text-zinc-400">
                    Los inicios se encadenan solos. Si la suma no coincide con la duración, usa «Reescalar tiempos».
                  </div>
                  <FieldEditor schema={n} value={scene.etapas} path="etapas" ctx={ctx} bare onChange={(v) => update("etapas", v)} />
                </>
              ) : (
                <FieldEditor schema={n} value={scene[key]} path={key} ctx={ctx} bare onChange={(v) => update(key, v)} />
              )}
            </Section>
          );
        })}
      </div>

      <aside className="space-y-3 lg:sticky lg:top-2 lg:max-h-[calc(100vh-1rem)] lg:self-start lg:overflow-y-auto">
        <div className="relative mx-auto aspect-[9/16] w-full max-w-[380px] overflow-hidden rounded-xl border border-zinc-800 bg-black">
          {frame && <img src={frame} className={`h-full w-full object-contain ${frameBusy ? "opacity-70" : ""}`} />}
          {frameBusy && <div className="absolute right-2 top-2"><Spinner /></div>}
          {!valid && <div className="absolute inset-0 flex items-center justify-center bg-black/60 p-6 text-center text-sm text-red-300">Corrige los errores para ver la vista previa</div>}
        </div>
        <div>
          <input type="range" min={0} max={dur - 0.01} step={0.05} value={t} onChange={(e) => setT(Number(e.target.value))} className="w-full" />
          <div className="flex h-2 overflow-hidden rounded">
            <div style={{ width: `${(scene.gancho.duracion_seg / dur) * 100}%` }} className="bg-zinc-600" title="gancho" />
            {scene.etapas.map((e: any, i: number) => (
              <div key={i} title={`${e.tipo} ${e.inicio_seg.toFixed(1)}s`} style={{ width: `${(e.duracion_seg / dur) * 100}%`, background: STAGE_COLORS[i % STAGE_COLORS.length] }} />
            ))}
          </div>
          <div className="mt-1 flex items-center justify-between text-xs text-zinc-400">
            <span className="font-mono">{t.toFixed(2)} s / {dur} s</span>
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={guides} onChange={(e) => setGuides(e.target.checked)} /> zonas seguras
            </label>
          </div>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-zinc-400">
            <span>Miniaturas por etapa</span>
            <button onClick={refreshThumbs} disabled={thumbBusy || !valid} className="rounded bg-zinc-800 px-2 py-0.5 hover:bg-zinc-700 disabled:opacity-40">
              {thumbBusy ? "…" : "Actualizar"}
            </button>
          </div>
          <div className="flex gap-1 overflow-x-auto pb-1">
            {thumbs.map((th, i) => (
              <button key={i} onClick={() => setT(th.t)} className="flex-none" title={scene.etapas[i]?.tipo}>
                <img src={th.png} className="h-28 rounded border border-zinc-800 hover:border-yellow-400" />
                <div className="w-[63px] truncate text-[10px] text-zinc-500">{scene.etapas[i]?.tipo}</div>
              </button>
            ))}
          </div>
        </div>
        <JobProgress job={job} onCancel={() => draftJob && api.post(`/api/jobs/${draftJob}/cancel`)} />
        {draftUrl && <video src={draftUrl} controls className="mx-auto w-full max-w-[300px] rounded-lg" />}
      </aside>
    </div>
  );
}
