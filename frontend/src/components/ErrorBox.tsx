import { ApiError } from "../api";

const HINTS: Record<string, string> = {
  claude_missing: "Instala Claude Code (npm i -g @anthropic-ai/claude-code) y ejecuta `claude login`.",
  claude_auth: "Ejecuta `claude login` en la máquina donde corre el backend y vuelve a intentarlo.",
  claude_process: "Revisa que `claude` funcione en una terminal y que la sesión esté iniciada.",
  ffmpeg_missing: "Instala ffmpeg (ver README) y reinicia el backend.",
  invalid_scene: "Corrige los campos marcados o pulsa «Reescalar tiempos».",
  validation: "Claude devolvió un JSON que no cumple el esquema dos veces. Prueba de nuevo o cambia la instrucción.",
  network: "Arranca todo con `make dev` o `./run.sh`.",
};

export default function ErrorBox({ error, onClose }: { error: unknown; onClose?: () => void }) {
  if (!error) return null;
  const e = error instanceof ApiError ? error : new ApiError(String((error as any)?.message ?? error));
  return (
    <div className="my-3 rounded-lg border border-red-500/50 bg-red-950/40 p-3 text-sm">
      <div className="flex items-start gap-2">
        <span>⚠️</span>
        <div className="flex-1">
          <div className="font-semibold text-red-200">{e.message}</div>
          {HINTS[e.code] && <div className="mt-1 text-red-300/80">{HINTS[e.code]}</div>}
          {e.details.length > 0 && (
            <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-red-300/90">
              {e.details.slice(0, 15).map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          )}
        </div>
        {onClose && (
          <button onClick={onClose} className="text-red-300 hover:text-white">
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
