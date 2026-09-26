import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Catalog, type Idea, type Project, type Scene } from "./api";
import IdeasStep from "./steps/IdeasStep";
import GuionStep from "./steps/GuionStep";
import EditorStep from "./steps/EditorStep";
import RenderStep from "./steps/RenderStep";
import ErrorBox from "./components/ErrorBox";

const STEPS = ["Ideas", "Guion", "Editor", "Render"];

interface Health {
  ffmpeg: { ok: boolean; detail: string };
  claude: { ok: boolean; detail: string };
  model: string;
  workers: number;
}

export default function App() {
  const [step, setStep] = useState(0);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState<ApiError | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [schema, setSchema] = useState<any>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showProjects, setShowProjects] = useState(false);

  useEffect(() => {
    api.get<Health>("/api/health").then(setHealth).catch(setHealthErr);
    api.get<Catalog>("/api/catalog").then(setCatalog).catch(() => {});
    api.get<any>("/api/schema").then(setSchema).catch(() => {});
  }, []);

  const loadProject = useCallback(async (id: string, goto?: number) => {
    const p = await api.get<Project>(`/api/projects/${id}`);
    setProject(p);
    localStorage.setItem("tf_project", id);
    if (goto !== undefined) setStep(goto);
    return p;
  }, []);

  useEffect(() => {
    const id = localStorage.getItem("tf_project");
    if (id)
      loadProject(id)
        .then((p) => setStep(p.scene ? 2 : p.ideas?.length ? 0 : 0))
        .catch(() => localStorage.removeItem("tf_project"));
  }, [loadProject]);

  const openProjects = async () => {
    setProjects(await api.get<Project[]>("/api/projects"));
    setShowProjects(true);
  };

  const newProject = () => {
    setProject(null);
    localStorage.removeItem("tf_project");
    setStep(0);
  };

  const canGo = (i: number) => i === 0 || (i === 1 && !!project?.idea) || (i >= 2 && !!project?.scene);

  return (
    <div className="mx-auto min-h-screen max-w-[1500px] px-4 pb-16">
      <header className="flex flex-wrap items-center gap-4 py-4">
        <div className="text-xl font-black tracking-tight">
          <span className="text-yellow-400">Timelapse</span>Forge
        </div>
        <nav className="flex gap-1">
          {STEPS.map((s, i) => (
            <button key={s} disabled={!canGo(i)} onClick={() => setStep(i)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition disabled:opacity-30 ${
                step === i ? "bg-yellow-400 text-zinc-950" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"}`}>
              {i + 1}. {s}
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2 text-sm">
          {project && <span className="max-w-[260px] truncate text-zinc-400">📁 {project.titulo}</span>}
          <button className="rounded-md bg-zinc-800 px-3 py-1 hover:bg-zinc-700" onClick={openProjects}>Proyectos</button>
          <button className="rounded-md bg-zinc-800 px-3 py-1 hover:bg-zinc-700" onClick={newProject}>Nuevo</button>
        </div>
      </header>

      {healthErr && <ErrorBox error={healthErr} />}
      {health && !health.ffmpeg.ok && <ErrorBox error={new ApiError(health.ffmpeg.detail, "ffmpeg_missing")} />}
      {health && !health.claude.ok && <ErrorBox error={new ApiError(health.claude.detail, "claude_missing")} />}

      {showProjects && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={() => setShowProjects(false)}>
          <div className="max-h-[80vh] w-[560px] overflow-auto rounded-xl border border-zinc-700 bg-zinc-900 p-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="mb-3 font-semibold">Proyectos</h2>
            {projects.length === 0 && <p className="text-sm text-zinc-400">Aún no hay proyectos.</p>}
            {projects.map((p) => (
              <button key={p.id} className="mb-1 flex w-full items-center justify-between rounded-md bg-zinc-800 px-3 py-2 text-left text-sm hover:bg-zinc-700"
                onClick={async () => {
                  const full = await loadProject(p.id);
                  setStep(full.scene ? 2 : full.idea ? 1 : 0);
                  setShowProjects(false);
                }}>
                <span className="truncate">{p.titulo}</span>
                <span className="text-xs text-zinc-500">
                  {p.has_scene ? "escena" : "ideas"} · {p.outputs.length} archivos
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <main className="mt-2">
        {step === 0 && (
          <IdeasStep project={project} catalog={catalog}
            onIdeas={(pid) => loadProject(pid)}
            onChoose={async (idea: Idea, pid: string) => {
              await api.put(`/api/projects/${pid}/descripcion`, { descripcion_md: "" }).catch(() => {});
              const p = await loadProject(pid);
              setProject({ ...p, idea, scene: null, descripcion_md: "" });
              setStep(1);
            }} />
        )}
        {step === 1 && project && (
          <GuionStep project={project} onUpdate={(p) => setProject({ ...project, ...p })} onNext={() => setStep(2)} />
        )}
        {step === 2 && project?.scene && schema && (
          <EditorStep project={project} schema={schema} catalog={catalog}
            onSaved={(scene: Scene) => setProject({ ...project, scene })}
            onRender={() => setStep(3)} />
        )}
        {step === 3 && project?.scene && <RenderStep project={project} onRefresh={() => loadProject(project.id)} />}
      </main>
      <footer className="mt-10 text-center text-xs text-zinc-600">
        {health && `Modelo: ${health.model} (Claude Agent SDK) · ${health.workers} núcleos de render`}
      </footer>
    </div>
  );
}
