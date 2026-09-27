export class ApiError extends Error {
  code: string;
  details: string[];
  constructor(message: string, code = "error", details: string[] = []) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("No se pudo conectar con el backend. ¿Está corriendo en el puerto 8000?", "network");
  }
  const txt = await res.text();
  let data: any = null;
  try {
    data = txt ? JSON.parse(txt) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    const e = data?.error;
    if (e) throw new ApiError(e.message, e.code, e.details || []);
    if (Array.isArray(data?.detail))
      throw new ApiError("Petición inválida", "invalid", data.detail.map((d: any) => `${(d.loc || []).join(".")}: ${d.msg}`));
    throw new ApiError(`Error ${res.status}: ${txt.slice(0, 300)}`);
  }
  return data as T;
}

export const api = {
  get: <T>(u: string) => req<T>("GET", u),
  post: <T>(u: string, b?: unknown) => req<T>("POST", u, b ?? {}),
  put: <T>(u: string, b?: unknown) => req<T>("PUT", u, b ?? {}),
  del: <T>(u: string) => req<T>("DELETE", u),
  upload: <T>(u: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<T>("POST", u, fd);
  },
};

export type Scene = Record<string, any>;

export interface Idea {
  titulo: string;
  gancho: string;
  proyecto: string;
  revelacion: string;
  tono: string;
  por_que_funciona: string;
  estilo_visual: string;
}

export interface Catalog {
  stage_types: Record<string, string>;
  poses: Record<string, string>;
  machines: Record<string, string>;
  tones: string[];
  interiors: Record<string, { descripcion: string; objetos: Record<string, string> }>;
}

export interface Job {
  id: string;
  project_id: string;
  borrador: boolean;
  status: "en_cola" | "renderizando" | "listo" | "error" | "cancelado";
  progress: number;
  message: string;
  result: any;
  error: string;
}

export interface Publicacion {
  descripcion: string;
  hashtags: string[];
  etiqueta_ia: boolean;
  nota_etiqueta_ia: string;
}

export interface Project {
  id: string;
  titulo: string;
  tema?: string;
  has_scene: boolean;
  outputs: string[];
  history: number;
  updated?: number;
  ideas?: Idea[];
  idea?: Idea | null;
  descripcion_md?: string;
  scene?: Scene | null;
  history_list?: { version: number; note: string; time: number }[];
  duracion_seg?: number;
  idioma?: string;
  publicacion?: Publicacion | null;
}

/** Recalcula inicio_seg encadenando las duraciones (igual que engine.schema.chain_starts). */
export function chainStarts(scene: Scene): Scene {
  const s = structuredClone(scene);
  let t = Number(s.gancho?.duracion_seg ?? 2.5);
  for (const e of s.etapas ?? []) {
    e.inicio_seg = Math.round(t * 1000) / 1000;
    t += Number(e.duracion_seg || 0);
  }
  return s;
}
