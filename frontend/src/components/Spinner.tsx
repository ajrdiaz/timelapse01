import { useEffect, useState } from "react";

export default function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-zinc-300">
      <span className="h-4 w-4 flex-none animate-spin rounded-full border-2 border-zinc-600 border-t-yellow-400" />
      {label}
    </span>
  );
}

/** Tiempo transcurrido «m:ss» mientras `active` es verdadero (para esperas largas de Claude). */
export function useElapsed(active: boolean): string {
  const [start, setStart] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!active) {
      setStart(null);
      return;
    }
    setStart(Date.now());
    setNow(Date.now());
    const h = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(h);
  }, [active]);
  const s = start ? Math.max(0, Math.floor((now - start) / 1000)) : 0;
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
