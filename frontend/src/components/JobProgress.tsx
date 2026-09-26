import { useEffect, useState } from "react";
import { api, type Job } from "../api";

/** Sigue un trabajo de render por SSE y muestra la barra de progreso en tiempo real. */
export function useJob(jobId: string | null, onDone?: (j: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    if (!jobId) return;
    const es = new EventSource(`/api/jobs/${jobId}/events`);
    es.onmessage = (ev) => {
      const j = JSON.parse(ev.data) as Job;
      setJob(j);
      if (["listo", "error", "cancelado"].includes(j.status)) {
        es.close();
        onDone?.(j);
      }
    };
    es.onerror = () => {
      // reconexión automática del navegador; si el trabajo terminó, cerramos
      api.get<Job>(`/api/jobs/${jobId}`).then((j) => {
        setJob(j);
        if (["listo", "error", "cancelado"].includes(j.status)) {
          es.close();
          onDone?.(j);
        }
      }).catch(() => es.close());
    };
    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);
  return job;
}

export default function JobProgress({ job, onCancel }: { job: Job | null; onCancel?: () => void }) {
  if (!job) return null;
  const pct = Math.round(job.progress * 100);
  const color = job.status === "error" ? "bg-red-500" : job.status === "cancelado" ? "bg-zinc-500" : "bg-yellow-400";
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
      <div className="mb-1 flex items-center justify-between text-sm">
        <span>
          {job.borrador ? "Borrador" : "Render final"} · <b>{job.status.replace("_", " ")}</b> · {job.message}
        </span>
        <span className="font-mono">{pct}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full ${color} transition-all duration-300`} style={{ width: `${pct}%` }} />
      </div>
      {job.status === "error" && <div className="mt-2 text-sm text-red-300">{job.error}</div>}
      {onCancel && ["en_cola", "renderizando"].includes(job.status) && (
        <button onClick={onCancel} className="mt-2 rounded-md bg-red-600/80 px-3 py-1 text-sm hover:bg-red-600">Cancelar render</button>
      )}
    </div>
  );
}
