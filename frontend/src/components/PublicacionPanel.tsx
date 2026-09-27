import { useState } from "react";
import { api, type Publicacion } from "../api";
import ErrorBox from "./ErrorBox";
import Spinner, { useElapsed } from "./Spinner";

/** Descripción + hashtags del video, listos para copiar y pegar en TikTok. */
export default function PublicacionPanel({ projectId, post, onChange }: {
  projectId: string;
  post: Publicacion | null | undefined;
  onChange: (p: Publicacion) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const elapsed = useElapsed(busy);

  const generate = async () => {
    setBusy(true);
    setErr(null);
    try {
      onChange(await api.post<Publicacion>(`/api/projects/${projectId}/post-text`));
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  const copy = async (what: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      setTimeout(() => setCopied((c) => (c === what ? null : c)), 1500);
    } catch (e) {
      setErr(e);
    }
  };

  const tags = post?.hashtags.join(" ") ?? "";
  const btn = "rounded-md bg-zinc-800 px-3 py-1 text-sm hover:bg-zinc-700";
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <div className="mb-2 flex items-center">
        <h3 className="font-semibold">Texto para TikTok</h3>
        <button onClick={generate} disabled={busy} className={`ml-auto ${btn} disabled:opacity-60`}>
          {busy ? <Spinner label={`Generando… ${elapsed}`} /> : post ? "Regenerar" : "Generar con Claude"}
        </button>
      </div>
      <ErrorBox error={err} onClose={() => setErr(null)} />
      {post ? (
        <div className={`space-y-3 text-sm ${busy ? "pointer-events-none opacity-40" : ""}`}>
          <div>
            <div className="mb-1 flex items-center text-xs text-zinc-400">
              Descripción
              <button onClick={() => copy("desc", post.descripcion)} className="ml-auto text-yellow-300 hover:text-yellow-200">
                {copied === "desc" ? "✓ Copiada" : "Copiar"}
              </button>
            </div>
            <p className="whitespace-pre-wrap rounded-md bg-zinc-950 p-3">{post.descripcion}</p>
          </div>
          <div>
            <div className="mb-1 flex items-center text-xs text-zinc-400">
              Hashtags
              <button onClick={() => copy("tags", tags)} className="ml-auto text-yellow-300 hover:text-yellow-200">
                {copied === "tags" ? "✓ Copiados" : "Copiar"}
              </button>
            </div>
            <p className="rounded-md bg-zinc-950 p-3 text-sky-300">{tags}</p>
          </div>
          <button onClick={() => copy("all", `${post.descripcion.trim()}\n\n${tags}`)}
            className="w-full rounded-md bg-yellow-400 py-1.5 font-bold text-zinc-950 hover:bg-yellow-300">
            {copied === "all" ? "✓ Copiado" : "Copiar descripción + hashtags"}
          </button>
          {post.etiqueta_ia && (
            <p className="text-xs text-zinc-400">
              Al publicar, marca la etiqueta «Contenido generado por IA». {post.nota_etiqueta_ia}
            </p>
          )}
        </div>
      ) : (
        !busy && <p className="text-sm text-zinc-400">Se genera junto con el guion. Si falta, pulsa «Generar con Claude».</p>
      )}
    </div>
  );
}
