import { useState } from "react";
import { api, type Job, type Project, type Publicacion } from "../api";
import ErrorBox from "../components/ErrorBox";
import JobProgress, { useJob } from "../components/JobProgress";
import PublicacionPanel from "../components/PublicacionPanel";

export default function RenderStep({ project, onRefresh }: { project: Project; onRefresh: () => void }) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [post, setPost] = useState<Publicacion | null>(project.publicacion ?? null);
  const [outputs, setOutputs] = useState<string[]>(project.outputs ?? []);
  const [v, setV] = useState(Date.now());
  const job = useJob(jobId, async (j: Job) => {
    if (j.status === "listo") {
      setV(Date.now());
      const p = await api.get<Project>(`/api/projects/${project.id}`);
      setOutputs(p.outputs);
      setPost(p.publicacion ?? null);
      onRefresh();
    }
  });

  const start = async () => {
    setErr(null);
    try {
      const j = await api.post<Job>("/api/render", { project_id: project.id, borrador: false });
      setJobId(j.id);
    } catch (e) {
      setErr(e);
    }
  };

  const s = project.scene!;
  const running = job && ["en_cola", "renderizando"].includes(job.status);
  const file = (n: string) => `/api/projects/${project.id}/files/${n}?v=${v}`;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      <div className="space-y-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm">
          <h2 className="mb-2 text-lg font-semibold">Render final</h2>
          <p className="text-zinc-400">
            {s.general.resolucion} · {s.general.fps} fps · {s.general.duracion_seg} s · CRF {s.exportacion.crf} · máx. {s.exportacion.max_mb} MB
            {s.audio.musica_propia ? ` · música: ${s.audio.musica_propia}` : " · música generada"}
          </p>
          <button onClick={start} disabled={!!running}
            className="mt-3 rounded-md bg-emerald-500 px-4 py-2 font-bold text-zinc-950 hover:bg-emerald-400 disabled:opacity-40">
            {outputs.includes("video.mp4") ? "Renderizar de nuevo" : "Renderizar video"}
          </button>
        </div>
        <ErrorBox error={err} onClose={() => setErr(null)} />
        <JobProgress job={job} onCancel={() => jobId && api.post(`/api/jobs/${jobId}/cancel`)} />
        {job?.result?.post_error && <ErrorBox error={new Error("No se pudo generar el texto de publicación: " + job.result.post_error)} />}
        {(outputs.includes("video.mp4") || outputs.includes("portada.png") || outputs.includes("publicacion.txt")) && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <h3 className="mb-2 font-semibold">Descargas</h3>
            <div className="flex flex-wrap gap-2 text-sm">
              {["video.mp4", "portada.png", "publicacion.txt", "borrador.mp4"].filter((n) => outputs.includes(n)).map((n) => (
                <a key={n} href={file(n) + "&download=true"} className="rounded-md bg-zinc-800 px-3 py-1.5 hover:bg-zinc-700">⬇ {n}</a>
              ))}
            </div>
            {job?.result?.mb && <div className="mt-2 text-xs text-zinc-500">{job.result.mb} MB · {job.result.frames} fotogramas · {job.result.seconds} s de render · {job.result.per_frame_core} s/fotograma/núcleo</div>}
          </div>
        )}
        <PublicacionPanel projectId={project.id} post={post}
          onChange={(p) => {
            setPost(p);
            if (!outputs.includes("publicacion.txt")) setOutputs([...outputs, "publicacion.txt"]);
            onRefresh();
          }} />
      </div>
      <div className="flex flex-wrap items-start justify-center gap-4">
        {outputs.includes("video.mp4") && <video key={v} src={file("video.mp4")} controls className="w-full max-w-[340px] rounded-xl border border-zinc-800" />}
        {outputs.includes("portada.png") && <img src={file("portada.png")} className="w-full max-w-[200px] rounded-xl border border-zinc-800" />}
      </div>
    </div>
  );
}
