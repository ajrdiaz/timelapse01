import { useState } from "react";
import { api, type Catalog, type Idea, type Project } from "../api";
import ErrorBox from "../components/ErrorBox";
import Spinner from "../components/Spinner";

const inputCls = "w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-yellow-400";

export default function IdeasStep({ project, onIdeas, onChoose }: {
  project: Project | null;
  catalog: Catalog | null;
  onIdeas: (pid: string) => void;
  onChoose: (idea: Idea, pid: string) => void;
}) {
  const [tema, setTema] = useState(project?.tema ?? "");
  const [dur, setDur] = useState(project?.duracion_seg ?? 62);
  const [tono, setTono] = useState("");
  const [idioma, setIdioma] = useState(project?.idioma ?? "es");
  const [ideas, setIdeas] = useState<Idea[]>(project?.ideas ?? []);
  const [pid, setPid] = useState<string | null>(project?.id ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ project_id: string; ideas: Idea[] }>("/api/ideas", {
        tema, duracion_seg: dur, tono, idioma, project_id: pid,
      });
      setIdeas(r.ideas);
      setPid(r.project_id);
      onIdeas(r.project_id);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 md:grid-cols-[2fr_1fr_1fr_1fr_auto]">
        <label className="text-xs text-zinc-400">
          Tema o nicho (opcional)
          <input className={inputCls} placeholder="p. ej. patio pequeño, gamer, fitness…" value={tema}
            onChange={(e) => setTema(e.target.value)} onKeyDown={(e) => e.key === "Enter" && generate()} />
        </label>
        <label className="text-xs text-zinc-400">
          Duración: {dur} s {dur <= 60 && <span className="text-amber-400">(TikTok monetiza &gt; 60 s)</span>}
          <input type="range" min={15} max={180} value={dur} onChange={(e) => setDur(Number(e.target.value))} className="mt-3 w-full" />
        </label>
        <label className="text-xs text-zinc-400">
          Tono
          <select className={inputCls} value={tono} onChange={(e) => setTono(e.target.value)}>
            <option value="">Variado</option>
            <option value="divertido">Divertido</option>
            <option value="serio">Serio</option>
            <option value="misterioso">Misterioso</option>
          </select>
        </label>
        <label className="text-xs text-zinc-400">
          Idioma
          <select className={inputCls} value={idioma} onChange={(e) => setIdioma(e.target.value)}>
            <option value="es">Español</option>
            <option value="en">English</option>
            <option value="pt">Português</option>
          </select>
        </label>
        <div className="flex items-end">
          <button onClick={generate} disabled={busy}
            className="w-full rounded-md bg-yellow-400 px-4 py-2 text-sm font-bold text-zinc-950 hover:bg-yellow-300 disabled:opacity-50">
            {ideas.length ? "Regenerar" : "Generar 5 ideas"}
          </button>
        </div>
      </div>
      {busy && <div className="mt-4"><Spinner label="Claude está pensando ideas…" /></div>}
      <ErrorBox error={error} onClose={() => setError(null)} />
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {ideas.map((it, i) => (
          <div key={i} className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
            <div className="mb-1 text-xs uppercase tracking-wide text-zinc-500">
              {it.tono} · {it.estilo_visual.replace("_", " ")}
            </div>
            <h3 className="text-lg font-bold">{it.titulo}</h3>
            <div className="my-2 rounded-md bg-black/40 px-3 py-2 text-center font-black tracking-wide text-yellow-300">“{it.gancho}”</div>
            <dl className="space-y-1 text-sm">
              <div><dt className="inline text-zinc-500">Se construye: </dt><dd className="inline">{it.proyecto}</dd></div>
              <div><dt className="inline text-zinc-500">Revelación: </dt><dd className="inline font-semibold">{it.revelacion}</dd></div>
              <div className="text-zinc-400"><dt className="inline text-zinc-500">Por qué funciona: </dt><dd className="inline">{it.por_que_funciona}</dd></div>
            </dl>
            <div className="mt-auto flex gap-2 pt-3">
              <button className="flex-1 rounded-md bg-yellow-400 py-1.5 text-sm font-bold text-zinc-950 hover:bg-yellow-300"
                onClick={() => pid && onChoose(it, pid)}>
                Elegir
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
