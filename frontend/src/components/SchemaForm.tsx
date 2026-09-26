import { useState, type ReactNode } from "react";
import type { Catalog, Scene } from "../api";

/** Editor generado a partir del JSON Schema de Pydantic (escena). */

type S = Record<string, any>;

export interface FormCtx {
  defs: Record<string, S>;
  catalog: Catalog | null;
  scene: Scene;
  errorsByPath: Record<string, string[]>;
  uploads: { fonts: string[]; music: string[] };
  onUpload: (file: File) => Promise<void>;
}

const WORDS: Record<string, string> = {
  duracion: "duración", seg: "(s)", resolucion: "resolución", titulo: "título", subtitulo: "subtítulo",
  intensidad: "intensidad", dia: "día", dias: "días", lineas: "líneas", tamanos: "tamaños", maquina: "máquina",
  revelacion: "revelación", aparicion: "aparición", posicion: "posición", animacion: "animación", pantalon: "pantalón",
  vineta: "viñeta", musica: "música", sfx: "efectos", bpm: "BPM", lufs: "LUFS", crf: "CRF", mb: "MB",
  tipografia: "tipografía", exportacion: "exportación", publicacion: "publicación", camara: "cámara",
  leds: "LEDs", cta: "CTA", ancho: "ancho", alto: "alto", m: "(m)", progresion: "progresión", vecino: "vecino",
  arbol: "árbol", guia: "guía", obreros: "obreros", pregunta: "pregunta", sincronizado: "sincronizado",
  densidad: "densidad", piedras: "piedras", ciclos: "ciclos", zoom: "zoom", offset: "(desde revelación)",
};

export function humanize(key: string): string {
  const s = key.split("_").map((w) => WORDS[w] ?? w).join(" ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function resolve(node: S, defs: Record<string, S>): { node: S; nullable: boolean } {
  let nullable = false;
  let n = node;
  if (n.$ref) n = { ...defs[n.$ref.split("/").pop()!], ...Object.fromEntries(Object.entries(n).filter(([k]) => k !== "$ref")) };
  if (n.anyOf) {
    const opts = n.anyOf.filter((o: S) => o.type !== "null");
    nullable = opts.length < n.anyOf.length;
    const inner = resolve(opts[0], defs).node;
    n = { ...inner, ...Object.fromEntries(Object.entries(n).filter(([k]) => k !== "anyOf")) };
  }
  if (n.allOf && n.allOf.length === 1) n = { ...resolve(n.allOf[0], defs).node, ...n, allOf: undefined };
  return { node: n, nullable };
}

export function defaultFor(node: S, defs: Record<string, S>): any {
  const { node: n } = resolve(node, defs);
  if (n.default !== undefined) return structuredClone(n.default);
  if (n.type === "object" && n.properties) {
    const o: S = {};
    for (const [k, v] of Object.entries(n.properties)) o[k] = defaultFor(v as S, defs);
    return o;
  }
  if (n.type === "array") return [];
  if (n.enum) return n.enum[0];
  if (n.type === "string") return "";
  if (n.type === "number" || n.type === "integer") return n.minimum ?? 0;
  if (n.type === "boolean") return false;
  return null;
}

function Tip({ text }: { text?: string }) {
  if (!text) return null;
  return (
    <span className="group relative ml-1 inline-block cursor-help text-zinc-500">
      ⓘ
      <span className="pointer-events-none absolute left-4 top-0 z-30 hidden w-64 rounded-md border border-zinc-700 bg-zinc-900 p-2 text-xs font-normal text-zinc-200 shadow-xl group-hover:block">
        {text}
      </span>
    </span>
  );
}

function Row({ label, tip, children, errs }: { label: string; tip?: string; children: ReactNode; errs?: string[] }) {
  return (
    <div className="py-1.5">
      <div className="mb-1 flex items-center text-xs font-medium text-zinc-400">
        {label}
        <Tip text={tip} />
      </div>
      {children}
      {errs?.map((e, i) => (
        <div key={i} className="mt-0.5 text-xs text-red-400">
          {e}
        </div>
      ))}
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm outline-none focus:border-yellow-400";

const numCls = "w-24 flex-none rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm outline-none focus:border-yellow-400";

function NumberField({ n, value, onChange }: { n: S; value: number; onChange: (v: number) => void }) {
  const min = n.minimum ?? n.exclusiveMinimum;
  const max = n.maximum ?? n.exclusiveMaximum;
  const isInt = n.type === "integer";
  const slider = min !== undefined && max !== undefined && max - min <= 10000;
  const range = slider ? max - min : 100;
  const step = isInt ? 1 : range <= 1.5 ? 0.01 : range <= 30 ? 0.1 : 0.5;
  return (
    <div className="flex items-center gap-2">
      {slider && (
        <input type="range" className="flex-1" min={min} max={max} step={step} value={value ?? min}
          onChange={(e) => onChange(Number(e.target.value))} />
      )}
      <input type="number" className={slider ? numCls : inputCls} min={min} max={max} step={step}
        value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))} />
    </div>
  );
}

function ColorField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2">
      <input type="color" value={/^#[0-9a-fA-F]{6}$/.test(value) ? value : "#000000"}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        className="h-8 w-12 cursor-pointer rounded border border-zinc-700 bg-transparent" />
      <input className="w-28 rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-sm outline-none focus:border-yellow-400" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function StringField({ n, value, onChange }: { n: S; value: string; onChange: (v: string) => void }) {
  const max = n.maxLength;
  const len = (value ?? "").length;
  return (
    <div className="relative">
      <input className={inputCls + " pr-12"} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
      {max && (
        <span className={`absolute right-2 top-1.5 text-[10px] ${len > max ? "text-red-400" : "text-zinc-500"}`}>
          {len}/{max}
        </span>
      )}
    </div>
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" onClick={() => onChange(!value)}
      className={`relative h-6 w-11 rounded-full transition ${value ? "bg-yellow-400" : "bg-zinc-700"}`}>
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${value ? "left-5" : "left-0.5"}`} />
    </button>
  );
}

function Select({ options, value, onChange }: { options: { v: any; label: string }[]; value: any; onChange: (v: any) => void }) {
  return (
    <select className={inputCls} value={String(value ?? "")}
      onChange={(e) => {
        const o = options.find((x) => String(x.v) === e.target.value);
        onChange(o ? o.v : e.target.value);
      }}>
      {options.map((o) => (
        <option key={String(o.v)} value={String(o.v)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function UploadButton({ accept, label, onUpload }: { accept: string; label: string; onUpload: (f: File) => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  return (
    <label className="inline-flex cursor-pointer items-center rounded-md border border-zinc-700 px-2 py-1 text-xs hover:border-yellow-400">
      {busy ? "Subiendo…" : label}
      <input type="file" accept={accept} className="hidden"
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          setBusy(true);
          try {
            await onUpload(f);
          } finally {
            setBusy(false);
            e.target.value = "";
          }
        }} />
    </label>
  );
}

/** Resumen de un elemento de lista (se muestra en la cabecera plegada). */
function itemSummary(path: string, item: S, i: number): string {
  if (path === "etapas") {
    const a = Number(item.inicio_seg ?? 0).toFixed(1);
    const b = (Number(item.inicio_seg ?? 0) + Number(item.duracion_seg ?? 0)).toFixed(1);
    return `${i + 1}. ${item.titulo || String(item.tipo).toUpperCase()} · ${item.tipo} · ${a}–${b} s · días ${item.dia_inicio}–${item.dia_fin}`;
  }
  if (path.endsWith("callouts")) return `${i + 1}. ${item.texto || "…"} → ${item.objeto}`;
  if (path.endsWith("lineas")) return `${i + 1}. ${item.texto || "…"}`;
  return `#${i + 1}`;
}

function ArrayField({ n, value, onChange, path, ctx }: { n: S; value: any[]; onChange: (v: any[]) => void; path: string; ctx: FormCtx }) {
  const items = resolve(n.items ?? {}, ctx.defs).node;
  const arr = value ?? [];
  const [open, setOpen] = useState<number | null>(null);
  const max = n.maxItems ?? 99;
  const min = n.minItems ?? 0;
  if (items.type !== "object") {
    // lista de valores simples (p. ej. colores del suelo)
    return (
      <div className="flex flex-wrap gap-2">
        {arr.map((v, i) => (
          <FieldEditor key={i} schema={n.items} value={v} path={`${path}.${i}`} ctx={ctx} bare
            onChange={(nv) => onChange(arr.map((x, j) => (j === i ? nv : x)))} />
        ))}
      </div>
    );
  }
  const move = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= arr.length) return;
    const c = [...arr];
    [c[i], c[j]] = [c[j], c[i]];
    onChange(c);
    setOpen(open === i ? j : open);
  };
  return (
    <div className="space-y-1.5">
      {arr.map((it, i) => {
        const errs = Object.entries(ctx.errorsByPath).filter(([p]) => p === `${path}.${i}` || p.startsWith(`${path}.${i}.`));
        return (
          <div key={i} className={`rounded-md border ${errs.length ? "border-red-500/60" : "border-zinc-800"} bg-zinc-900/60`}>
            <div className="flex items-center gap-1 px-2 py-1">
              <button type="button" className="flex-1 truncate text-left text-sm" onClick={() => setOpen(open === i ? null : i)}>
                <span className="mr-1 text-zinc-500">{open === i ? "▾" : "▸"}</span>
                {itemSummary(path, it, i)}
              </button>
              <button type="button" title="Subir" className="px-1 text-zinc-400 hover:text-white" onClick={() => move(i, -1)}>↑</button>
              <button type="button" title="Bajar" className="px-1 text-zinc-400 hover:text-white" onClick={() => move(i, 1)}>↓</button>
              <button type="button" title="Duplicar" className="px-1 text-zinc-400 hover:text-white" disabled={arr.length >= max}
                onClick={() => onChange([...arr.slice(0, i + 1), structuredClone(it), ...arr.slice(i + 1)])}>⧉</button>
              <button type="button" title="Eliminar" className="px-1 text-red-400 hover:text-red-300" disabled={arr.length <= min}
                onClick={() => onChange(arr.filter((_, j) => j !== i))}>✕</button>
            </div>
            {open === i && (
              <div className="border-t border-zinc-800 px-3 pb-2">
                <ObjectFields n={items} value={it} path={`${path}.${i}`} ctx={ctx}
                  onChange={(nv) => onChange(arr.map((x, j) => (j === i ? nv : x)))} />
              </div>
            )}
          </div>
        );
      })}
      {arr.length < max && (
        <button type="button" className="rounded-md border border-dashed border-zinc-700 px-3 py-1 text-xs text-zinc-300 hover:border-yellow-400"
          onClick={() => {
            const def = defaultFor(items, ctx.defs);
            if (path.endsWith("callouts") && ctx.catalog) {
              const objs = Object.keys(ctx.catalog.interiors[ctx.scene.revelacion?.tipo_interior]?.objetos ?? {});
              def.objeto = objs[0] ?? "";
              def.texto = "NUEVO";
            }
            onChange([...arr, def]);
            setOpen(arr.length);
          }}>
          + Añadir
        </button>
      )}
    </div>
  );
}

function ObjectFields({ n, value, onChange, path, ctx }: { n: S; value: S; onChange: (v: S) => void; path: string; ctx: FormCtx }) {
  const props = n.properties ?? {};
  return (
    <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
      {Object.entries(props).map(([k, sub]) => {
        const r = resolve(sub as S, ctx.defs).node;
        const wide = r.type === "object" || r.type === "array";
        return (
          <div key={k} className={wide ? "md:col-span-2" : ""}>
            <FieldEditor schema={sub as S} value={value?.[k]} path={path ? `${path}.${k}` : k} ctx={ctx} label={humanize(k)}
              onChange={(nv) => onChange({ ...value, [k]: nv })} />
          </div>
        );
      })}
    </div>
  );
}

export function FieldEditor({ schema, value, onChange, path, ctx, label, bare }: {
  schema: S; value: any; onChange: (v: any) => void; path: string; ctx: FormCtx; label?: string; bare?: boolean;
}) {
  const { node: n, nullable } = resolve(schema, ctx.defs);
  const tip = (schema as S).description ?? n.description;
  const errs = ctx.errorsByPath[path];
  const key = path.split(".").pop() ?? "";
  let control: ReactNode;

  // widgets especiales
  if (/^revelacion\.callouts\.\d+\.objeto$/.test(path) && ctx.catalog) {
    const objs = ctx.catalog.interiors[ctx.scene.revelacion?.tipo_interior]?.objetos ?? {};
    control = <Select value={value} onChange={onChange} options={Object.entries(objs).map(([v, l]) => ({ v, label: `${l} (${v})` }))} />;
  } else if (path === "etapas.*" || /^etapas\.\d+\.tipo$/.test(path)) {
    control = <Select value={value} onChange={onChange}
      options={(n.enum ?? []).map((v: string) => ({ v, label: `${v} — ${ctx.catalog?.stage_types[v] ?? ""}`.slice(0, 70) }))} />;
  } else if (path === "tipografia.fuente") {
    const opts = ["Anton", "DejaVu", ...ctx.uploads.fonts];
    control = (
      <div className="flex gap-2">
        <Select value={value} onChange={onChange} options={Array.from(new Set([...opts, value])).map((v) => ({ v, label: v }))} />
        <UploadButton accept=".ttf,.otf,.woff,.woff2" label="Subir .ttf" onUpload={ctx.onUpload} />
      </div>
    );
  } else if (path === "audio.musica_propia") {
    control = (
      <div className="flex flex-wrap items-center gap-2">
        <Select value={value ?? ""} onChange={(v) => onChange(v || null)}
          options={[{ v: "", label: "— música generada —" }, ...Array.from(new Set([...ctx.uploads.music, ...(value ? [value] : [])])).map((v) => ({ v, label: v }))]} />
        <UploadButton accept="audio/*" label="Subir música" onUpload={ctx.onUpload} />
      </div>
    );
  } else if (n.enum) {
    control = <Select value={value} onChange={onChange} options={n.enum.map((v: any) => ({ v, label: String(v) }))} />;
  } else if (n.type === "boolean") {
    control = <Toggle value={!!value} onChange={onChange} />;
  } else if (n.type === "number" || n.type === "integer") {
    control = <NumberField n={n} value={value} onChange={onChange} />;
  } else if (n.type === "string" && n.format === "color") {
    control = <ColorField value={value ?? "#000000"} onChange={onChange} />;
  } else if (n.type === "string") {
    control = <StringField n={n} value={value} onChange={(v) => onChange(nullable && v === "" ? null : v)} />;
  } else if (n.type === "array") {
    control = <ArrayField n={n} value={value} onChange={onChange} path={path} ctx={ctx} />;
  } else if (n.type === "object" && bare) {
    return <ObjectFields n={n} value={value ?? {}} onChange={onChange} path={path} ctx={ctx} />;
  } else if (n.type === "object") {
    return (
      <fieldset className="mt-2 rounded-md border border-zinc-800 px-3 pb-2">
        <legend className="px-1 text-xs font-semibold text-zinc-300">
          {label ?? humanize(key)}
          <Tip text={tip} />
        </legend>
        <ObjectFields n={n} value={value ?? {}} onChange={onChange} path={path} ctx={ctx} />
      </fieldset>
    );
  } else {
    control = <input className={inputCls} value={JSON.stringify(value)} readOnly />;
  }
  if (bare) return <>{control}</>;
  return (
    <Row label={label ?? humanize(key)} tip={tip} errs={errs}>
      {control}
    </Row>
  );
}

export const SECTIONS: [string, string][] = [
  ["general", "1. General"],
  ["gancho", "2. Gancho (intro)"],
  ["etapas", "3. Etapas de construcción"],
  ["contador", "4. Contador y progreso"],
  ["escenario", "5. Escenario"],
  ["personajes", "6. Personajes y maquinaria"],
  ["revelacion", "7. Revelación"],
  ["cta", "8. CTA"],
  ["tipografia", "9. Tipografía y zonas seguras"],
  ["audio", "10. Audio"],
  ["exportacion", "11. Exportación"],
];

export function Section({ title, children, defaultOpen = false, errors = 0, extra }: {
  title: string; children: ReactNode; defaultOpen?: boolean; errors?: number; extra?: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40">
      <div className="flex items-center px-3 py-2">
        <button type="button" onClick={() => setOpen(!open)} className="flex flex-1 items-center gap-2 text-left text-sm font-semibold">
          <span className="text-zinc-500">{open ? "▾" : "▸"}</span>
          {title}
          {errors > 0 && <span className="rounded bg-red-500/20 px-1.5 text-xs text-red-300">{errors} error{errors > 1 ? "es" : ""}</span>}
        </button>
        {extra}
      </div>
      {open && <div className="border-t border-zinc-800 px-3 pb-3">{children}</div>}
    </div>
  );
}
