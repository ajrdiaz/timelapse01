import { useEffect, useRef, useState } from "react";
import { api, type Project, type Publicacion, type Scene } from "../api";
import ErrorBox from "../components/ErrorBox";
import PublicacionPanel from "../components/PublicacionPanel";
import Markdown from "../components/Markdown";
import Spinner, { useElapsed } from "../components/Spinner";

export default function GuionStep({ project, onUpdate, onNext }: {
  project: Project;
  onUpdate: (p: Partial<Project>) => void;
  onNext: () => void;
}) {
  const [md, setMd] = useState(project.descripcion_md ?? "");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [instr, setInstr] = useState("");
  const [dur, setDur] = useState<number>(project.scene?.general?.duracion_seg ?? project.duracion_seg ?? 62);
  const started = useRef(false);
  const banner = useRef<HTMLDivElement>(null);
  const elapsed = useElapsed(!!busy);

  // el botón puede quedar lejos del aviso (p. ej. en pantallas estrechas): llevar el aviso a la vista
  useEffect(() => {
    if (busy) banner.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [busy]);

  const generate = async () => {
    if (!project.idea) return;
    if (project.scene && !window.confirm(
      "Esto reemplaza el guion actual, la escena (con tus cambios del editor) y el texto para TikTok, " +
      "y borra el historial de «Deshacer». No se puede recuperar. ¿Continuar?")) return;
    setBusy("Claude está escribiendo el guion, la escena y el texto para TikTok… (suele tardar 1–2 min)");
    setError(null);
    try {
      const r = await api.post<{ descripcion_md: string; scene: Scene; publicacion: Publicacion | null; history: Project["history_list"] }>("/api/scene", {
        project_id: project.id, idea: project.idea, duracion_seg: dur, idioma: project.idioma ?? "es",
      });
      setMd(r.descripcion_md);
      onUpdate({ descripcion_md: r.descripcion_md, scene: r.scene, has_scene: true, publicacion: r.publicacion, history_list: r.history });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  useEffect(() => {
    if (!started.current && project.idea && !project.scene && !md) {
      started.current = true;
      generate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const regenerate = async () => {
    if (!instr.trim()) return;
    setBusy("Claude está aplicando tus instrucciones…");
    setError(null);
    try {
      const r = await api.post<{ scene: Scene; cambios: string; history: Project["history_list"] }>("/api/scene/edit", { project_id: project.id, instruccion: instr });
      const note = `\n\n---\n**Cambios (${new Date().toLocaleTimeString()}):** ${instr}\n\n${r.cambios}\n`;
      const newMd = md + note;
      setMd(newMd);
      await api.put(`/api/projects/${project.id}/descripcion`, { descripcion_md: newMd });
      onUpdate({ scene: r.scene, descripcion_md: newMd, history_list: r.history });
      setInstr("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  const saveMd = async () => {
    await api.put(`/api/projects/${project.id}/descripcion`, { descripcion_md: md });
    onUpdate({ descripcion_md: md });
    setEditing(false);
  };

  const s = project.scene;
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="mb-3 flex items-center gap-2">
          <h2 className="font-semibold">Descripción detallada</h2>
          <div className="ml-auto flex gap-2">
            {md && !editing && <button className="rounded-md bg-zinc-800 px-3 py-1 text-sm hover:bg-zinc-700" onClick={() => setEditing(true)}>Editar texto</button>}
            {editing && <button className="rounded-md bg-yellow-400 px-3 py-1 text-sm font-bold text-zinc-950" onClick={saveMd}>Guardar texto</button>}
          </div>
        </div>
        {busy && (
          <div ref={banner} className="mb-3 rounded-lg border border-yellow-400/40 bg-yellow-400/10 p-3">
            <Spinner label={`${busy} · ${elapsed}`} />
          </div>
        )}
        <ErrorBox error={error} onClose={() => setError(null)} />
        {editing ? (
          <textarea className="h-[65vh] w-full rounded-md border border-zinc-700 bg-zinc-950 p-3 font-mono text-sm" value={md} onChange={(e) => setMd(e.target.value)} />
        ) : (
          md ? (
            <div className={busy ? "pointer-events-none opacity-40 transition-opacity" : "transition-opacity"}>
              <Markdown text={md} />
            </div>
          ) : !busy && <p className="text-sm text-zinc-400">Aún no hay guion.</p>
        )}
      </div>
      <aside className="space-y-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm">
          <div className="text-xs uppercase text-zinc-500">Idea elegida</div>
          <div className="font-bold">{project.idea?.titulo}</div>
          <div className="text-yellow-300">“{project.idea?.gancho}”</div>
          <div className="mt-1 text-zinc-400">{project.idea?.proyecto} → {project.idea?.revelacion}</div>
          <label className="mt-3 block text-xs text-zinc-400">
            Duración: {dur} s
            <input type="range" min={15} max={180} value={dur} onChange={(e) => setDur(Number(e.target.value))} className="w-full" />
          </label>
          <button disabled={!!busy} onClick={generate}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-md bg-zinc-800 py-1.5 hover:bg-zinc-700 disabled:opacity-50">
            {busy?.startsWith("Claude está escribiendo") ? (
              <Spinner label={`Generando guion… ${elapsed}`} />
            ) : s ? "Generar guion desde cero" : "Generar guion"}
          </button>
        </div>
        {s && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="mb-2 text-sm font-semibold">Re-generar con instrucciones</div>
            <textarea className="h-24 w-full rounded-md border border-zinc-700 bg-zinc-950 p-2 text-sm" value={instr}
              placeholder="«haz la excavación más larga», «cambia la revelación a un cine»…" onChange={(e) => setInstr(e.target.value)} />
            <button disabled={!!busy || !instr.trim()} onClick={regenerate}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-md bg-zinc-800 py-1.5 text-sm hover:bg-zinc-700 disabled:opacity-50">
              {busy?.startsWith("Claude está aplicando") ? <Spinner label={`Aplicando cambios… ${elapsed}`} /> : "Aplicar con Claude"}
            </button>
            <div className="mt-4 text-xs text-zinc-400">
              {s.etapas.length} etapas · {s.general.duracion_seg} s · interior «{s.revelacion.tipo_interior}» · {s.revelacion.callouts.length} callouts
            </div>
            <button onClick={onNext} className="mt-3 w-full rounded-md bg-yellow-400 py-2 text-sm font-bold text-zinc-950 hover:bg-yellow-300">
              Ir al editor →
            </button>
          </div>
        )}
        {s && <PublicacionPanel projectId={project.id} post={project.publicacion} onChange={(publicacion) => onUpdate({ publicacion })} />}
      </aside>
    </div>
  );
}
