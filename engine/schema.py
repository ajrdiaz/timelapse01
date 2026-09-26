"""Esquema de escena (Pydantic v2). Es el único contrato entre el LLM, el editor y el motor.

Todos los campos tienen valor por defecto, validación y descripción (tooltip en español).
"""
from __future__ import annotations

import copy
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.catalog import INTERIOR_TYPES, MACHINES, POSES, STAGE_TYPES

TOL = 0.05  # tolerancia en segundos para la coherencia temporal

Color = Annotated[
    str,
    Field(pattern=r"^#[0-9A-Fa-f]{6}$", json_schema_extra={"format": "color"}),
]
StageType = Literal[tuple(STAGE_TYPES)]  # type: ignore[valid-type]
Pose = Literal[tuple(POSES)]  # type: ignore[valid-type]
Machine = Literal[tuple(MACHINES)]  # type: ignore[valid-type]
InteriorType = Literal[tuple(INTERIOR_TYPES)]  # type: ignore[valid-type]


def F(default: Any = ..., desc: str = "", **kw: Any) -> Any:
    return Field(default, description=desc, **kw)


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=False)


# 1. General ------------------------------------------------------------------
class General(_M):
    model_config = ConfigDict(extra="forbid", title="General")
    titulo: str = F("Construí un búnker en mi patio", "Título interno del proyecto.", max_length=60)
    duracion_seg: float = F(
        62.0,
        "Duración total del video en segundos. TikTok exige más de 60 s para monetizar.",
        ge=15, le=180,
    )
    fps: Literal[24, 30, 60] = F(30, "Fotogramas por segundo.")
    resolucion: Literal["1080x1920", "720x1280"] = F(
        "1080x1920", "Resolución final. 720×1280 sirve como borrador."
    )
    idioma: str = F("es", "Idioma de los textos (código ISO, p. ej. es, en, pt).", max_length=8)
    seed: int = F(7, "Semilla: el mismo JSON con la misma semilla produce el mismo video.", ge=0, le=2**31 - 1)
    estilo_visual: Literal["corte_lateral"] = F("corte_lateral", "Estilo visual (v1: solo corte lateral).")

    @property
    def size(self) -> tuple[int, int]:
        w, h = self.resolucion.split("x")
        return int(w), int(h)


# 2. Gancho -------------------------------------------------------------------
class LineaTexto(_M):
    texto: str = F("", "Texto de la línea.", max_length=40)
    color: Color = F("#FFFFFF", "Color de la línea.")


class Gancho(_M):
    model_config = ConfigDict(extra="forbid", title="Gancho (intro)")
    lineas: list[LineaTexto] = F(
        default_factory=lambda: [
            LineaTexto(texto="CONSTRUÍ UN BÚNKER", color="#FFFFFF"),
            LineaTexto(texto="EN MI PATIO", color="#FFD400"),
        ],
        desc="1 a 3 líneas de texto de apertura (máx. 8 palabras en total recomendado).",
        min_length=1, max_length=3,
    )
    duracion_seg: float = F(2.5, "Duración del gancho antes de la primera etapa.", ge=0.5, le=8)
    zoom_out: bool = F(True, "Zoom-out inicial de la cámara.")
    zoom_intensidad: float = F(1.35, "Zoom inicial (1 = sin zoom).", ge=1.0, le=2.5)


# 3. Etapas -------------------------------------------------------------------
class Etapa(_M):
    tipo: StageType = F("excavacion", "Tipo de etapa del catálogo del motor.")
    titulo: str = F("", "Título en pantalla.", max_length=28)
    subtitulo: str = F("", "Subtítulo humorístico.", max_length=48)
    inicio_seg: float = F(0.0, "Segundo en que empieza la etapa (se encadena con la anterior).", ge=0, le=180)
    duracion_seg: float = F(4.0, "Duración de la etapa en segundos.", ge=0.3, le=90)
    dia_inicio: int = F(1, "Día mostrado al empezar la etapa.", ge=0, le=999)
    dia_fin: int = F(1, "Día mostrado al terminar la etapa.", ge=0, le=999)
    obreros: int = F(2, "Número de obreros en escena.", ge=0, le=6)
    pose: Pose = F("pala", "Pose/animación de los obreros.")
    maquina: Machine = F("ninguna", "Máquina presente durante la etapa.")
    sfx: bool = F(True, "Activar efectos de sonido de esta etapa.")

    @property
    def fin_seg(self) -> float:
        return self.inicio_seg + self.duracion_seg


# 4. Contador -----------------------------------------------------------------
class Contador(_M):
    model_config = ConfigDict(extra="forbid", title="Contador y progreso")
    mostrar: bool = F(True, "Mostrar el contador de días.")
    prefijo: str = F("DÍA", "Prefijo del contador.", max_length=10)
    dias_totales: int = F(60, "Total de días de la obra (la barra llega al 100 % aquí).", ge=1, le=999)
    barra: bool = F(True, "Mostrar barra de progreso.")
    color_barra: Color = F("#FFD400", "Color de la barra de progreso.")


# 5. Escenario ----------------------------------------------------------------
class Fondo(_M):
    cerca: bool = F(True, "Cerca de madera al fondo.")
    arbol: bool = F(True, "Árbol al fondo.")
    casa_vecino: bool = F(True, "Casa del vecino al fondo.")


class DiaNoche(_M):
    activo: bool = F(True, "Activar ciclo día/noche durante la obra.")
    ciclos: int = F(4, "Número de noches durante la construcción.", ge=0, le=12)
    intensidad: float = F(0.65, "Oscuridad de la noche (0–1).", ge=0, le=1)


class Escenario(_M):
    model_config = ConfigDict(extra="forbid", title="Escenario")
    ancho_m: float = F(6.0, "Ancho interior del recinto en metros.", ge=3, le=9)
    alto_m: float = F(2.6, "Alto interior del recinto en metros.", ge=2, le=4)
    profundidad_m: float = F(1.0, "Tierra sobre el techo en metros.", ge=0.3, le=2.5)
    colores_suelo: list[Color] = F(
        default_factory=lambda: ["#7A5234", "#6A4529", "#58391F"],
        desc="Colores de las capas de suelo (superficie → fondo).", min_length=3, max_length=3,
    )
    densidad_piedras: float = F(0.5, "Densidad de piedras en el suelo (0–1).", ge=0, le=1)
    fondo: Fondo = F(default_factory=Fondo, desc="Elementos del fondo.")
    dia_noche: DiaNoche = F(default_factory=DiaNoche, desc="Ciclo día/noche.")
    nubes: bool = F(True, "Nubes en movimiento.")
    vineta: float = F(0.35, "Intensidad de la viñeta (0–1).", ge=0, le=1)


# 6. Personajes ---------------------------------------------------------------
class Excavadora(_M):
    activa: bool = F(True, "Mostrar la excavadora en las etapas que la usan.")
    color: Color = F("#F2B705", "Color de la excavadora.")
    entrada_salida: bool = F(True, "Animar la entrada y salida de la excavadora.")


class Personajes(_M):
    model_config = ConfigDict(extra="forbid", title="Personajes y maquinaria")
    color_chaleco: Color = F("#FF7A00", "Color del chaleco.")
    color_casco: Color = F("#FFD400", "Color del casco.")
    color_pantalon: Color = F("#2C3E66", "Color del pantalón.")
    excavadora: Excavadora = F(default_factory=Excavadora, desc="Excavadora.")
    ocultar_obreros_noche: bool = F(True, "Los obreros se van a casa de noche.")


# 7. Revelación ---------------------------------------------------------------
class Callout(_M):
    texto: str = F("", "Texto del callout.", max_length=24)
    objeto: str = F("", "Objeto del interior al que apunta.", max_length=32)
    aparicion_seg: float = F(1.0, "Segundos desde el inicio de la etapa 'revelacion'.", ge=0, le=60)


class Revelacion(_M):
    model_config = ConfigDict(extra="forbid", title="Revelación")
    tipo_interior: InteriorType = F("gamer", "Qué hay dentro del búnker.")
    color_acento: Color = F("#8A2BE2", "Color de acento del interior.")
    color_leds: Color = F("#00E5FF", "Color de las tiras LED.")
    texto_pregunta: str = F("¿Y POR DENTRO?", "Pregunta antes de revelar.", max_length=30)
    texto_falsa_expectativa: str = F("¿REFUGIO PARA EL APOCALIPSIS?", "Falsa expectativa.", max_length=40)
    remate_1: str = F("NO.", "Primera parte del remate.", max_length=14)
    remate_2: str = F("ES MI CUARTO GAMER", "Segunda parte del remate.", max_length=30)
    flash_offset_seg: float = F(0.0, "Momento del flash, en segundos desde el inicio de 'revelacion'.", ge=0, le=10)
    zoom_camara: float = F(1.45, "Zoom de la cámara sobre el interior.", ge=1.0, le=2.5)
    callouts: list[Callout] = F(
        default_factory=list, desc="Hasta 5 flechas con texto apuntando a objetos.", max_length=5
    )


# 8. CTA ----------------------------------------------------------------------
class CTAFinal(_M):
    texto: str = F("SÍGUEME PARA LA PARTE 2", "Texto del CTA final.", max_length=32)
    color_fondo: Color = F("#FF2D55", "Color de fondo del CTA.")
    color_texto: Color = F("#FFFFFF", "Color del texto del CTA.")
    aparicion_seg: float = F(59.3, "Segundo (absoluto) en que aparece.", ge=0, le=180)
    posicion: Literal["arriba", "centro", "abajo"] = F("arriba", "Posición vertical.")
    animacion: Literal["pop", "deslizar"] = F("pop", "Animación de entrada.")


class CTAIntermedio(_M):
    activo: bool = F(False, "Mostrar un CTA a mitad del video.")
    texto: str = F("COMENTA QUÉ LE PONDRÍAS", "Texto del CTA intermedio.", max_length=32)
    aparicion_seg: float = F(30.0, "Segundo (absoluto) en que aparece.", ge=0, le=180)
    duracion_seg: float = F(3.0, "Cuánto tiempo se muestra.", ge=0.5, le=10)
    color_fondo: Color = F("#FFFFFF", "Color de fondo.")
    color_texto: Color = F("#111111", "Color del texto.")


class CTA(_M):
    model_config = ConfigDict(extra="forbid", title="CTA")
    final: CTAFinal = F(default_factory=CTAFinal, desc="CTA final.")
    intermedio: CTAIntermedio = F(default_factory=CTAIntermedio, desc="CTA intermedio opcional.")
    texto_cierre: str = F("Y NO PIENSO SALIR", "Texto de cierre.", max_length=32)


# 9. Tipografía ---------------------------------------------------------------
class Tamanos(_M):
    titulo: int = F(92, "Tamaño del título (px a 1080 de ancho).", ge=30, le=180)
    subtitulo: int = F(52, "Tamaño del subtítulo.", ge=20, le=120)
    contador: int = F(78, "Tamaño del contador.", ge=20, le=160)
    callout: int = F(46, "Tamaño de los callouts.", ge=16, le=100)


class Tipografia(_M):
    model_config = ConfigDict(extra="forbid", title="Tipografía y zonas seguras")
    fuente: str = F("Anton", "Fuente: 'Anton', 'DejaVu' o el nombre de un .ttf subido.", max_length=80)
    tamanos: Tamanos = F(default_factory=Tamanos, desc="Tamaños de texto.")
    contorno: int = F(7, "Grosor del contorno del texto (px).", ge=0, le=20)
    margen_superior: int = F(150, "Margen superior de los textos (px a 1920 de alto).", ge=0, le=600)
    guia_zonas_seguras: bool = F(True, "Mostrar en la vista previa las zonas que tapa la interfaz de TikTok.")


# 10. Audio -------------------------------------------------------------------
class Audio(_M):
    model_config = ConfigDict(extra="forbid", title="Audio")
    musica: bool = F(True, "Generar música.")
    bpm: int = F(112, "Tempo de la música.", ge=90, le=140)
    progresion: Literal["A menor: Am-F-C-G", "E menor: Em-C-G-D", "D menor: Dm-Bb-F-C"] = F(
        "A menor: Am-F-C-G", "Tonalidad / progresión de acordes."
    )
    estilo_obra: Literal["yunque_marimba"] = F("yunque_marimba", "Estilo de la sección de obra.")
    estilo_drop: Literal["electronico", "chiptune"] = F("electronico", "Estilo del drop de la revelación.")
    volumen_musica: float = F(0.8, "Volumen de la música (0–1).", ge=0, le=1)
    volumen_sfx: float = F(0.9, "Volumen de los efectos (0–1).", ge=0, le=1)
    drop_sincronizado: bool = F(True, "El drop cae exactamente en el flash.")
    lufs_objetivo: float = F(-14.0, "Loudness integrado objetivo (LUFS).", ge=-24, le=-8)
    musica_propia: Optional[str] = F(None, "Archivo de música subido (reemplaza la generada).", max_length=200)


# 11. Exportación -------------------------------------------------------------
class Portada(_M):
    generar: bool = F(True, "Generar portada PNG.")
    tiempo_seg: float = F(-1.0, "Fotograma de la portada (-1 = automático, en la revelación).", ge=-1, le=180)


class Exportacion(_M):
    model_config = ConfigDict(extra="forbid", title="Exportación")
    crf: int = F(20, "Calidad x264 (menor = mejor).", ge=14, le=35)
    preset: Literal["ultrafast", "veryfast", "faster", "fast", "medium", "slow"] = F("medium", "Preset x264.")
    max_mb: float = F(50.0, "Tamaño máximo del MP4 en MB.", ge=2, le=287)
    portada: Portada = F(default_factory=Portada, desc="Portada.")
    texto_publicacion: bool = F(True, "Generar texto de publicación con Claude.")


# Escena ----------------------------------------------------------------------
def _default_stages() -> list[Etapa]:
    from engine.defaults import default_stages

    return default_stages()


class Scene(_M):
    model_config = ConfigDict(extra="forbid", title="Escena")
    version: int = F(1, "Versión del esquema.")
    general: General = F(default_factory=General, desc="General")
    gancho: Gancho = F(default_factory=Gancho, desc="Gancho")
    etapas: list[Etapa] = F(default_factory=_default_stages, desc="Etapas de construcción", min_length=1, max_length=30)
    contador: Contador = F(default_factory=Contador, desc="Contador")
    escenario: Escenario = F(default_factory=Escenario, desc="Escenario")
    personajes: Personajes = F(default_factory=Personajes, desc="Personajes")
    revelacion: Revelacion = F(default_factory=Revelacion, desc="Revelación")
    cta: CTA = F(default_factory=CTA, desc="CTA")
    tipografia: Tipografia = F(default_factory=Tipografia, desc="Tipografía")
    audio: Audio = F(default_factory=Audio, desc="Audio")
    exportacion: Exportacion = F(default_factory=Exportacion, desc="Exportación")

    @model_validator(mode="after")
    def _coherencia(self) -> "Scene":
        errs = coherence_errors(self)
        if errs:
            raise ValueError("Incoherencias: " + " | ".join(errs))
        return self

    # utilidades ------------------------------------------------------------
    def stage_at(self, t: float) -> tuple[int, float]:
        """Índice de la etapa activa en t y su progreso local 0..1 (-1 durante el gancho)."""
        if t < self.etapas[0].inicio_seg:
            return -1, 0.0
        for i, e in enumerate(self.etapas):
            if t < e.fin_seg or i == len(self.etapas) - 1:
                return i, max(0.0, min(1.0, (t - e.inicio_seg) / e.duracion_seg))
        return len(self.etapas) - 1, 1.0

    def first_stage(self, tipo: str) -> Optional[Etapa]:
        return next((e for e in self.etapas if e.tipo == tipo), None)

    @property
    def flash_time(self) -> Optional[float]:
        e = self.first_stage("revelacion")
        return None if e is None else e.inicio_seg + self.revelacion.flash_offset_seg


def coherence_errors(s: Scene) -> list[str]:
    """Reglas de coherencia que un JSON Schema no puede expresar."""
    from engine.interiors import INTERIORS

    errs: list[str] = []
    dur = s.general.duracion_seg
    et = s.etapas
    if abs(et[0].inicio_seg - s.gancho.duracion_seg) > TOL:
        errs.append(
            f"etapas[0].inicio_seg ({et[0].inicio_seg}) debe ser igual a gancho.duracion_seg ({s.gancho.duracion_seg})"
        )
    for i in range(1, len(et)):
        prev_end = et[i - 1].fin_seg
        if et[i].inicio_seg < prev_end - TOL:
            errs.append(f"etapas[{i}] se solapa con la anterior ({et[i].inicio_seg:.2f} < {prev_end:.2f})")
        elif et[i].inicio_seg > prev_end + TOL:
            errs.append(f"hueco entre etapas[{i-1}] y etapas[{i}] ({prev_end:.2f} → {et[i].inicio_seg:.2f})")
    if abs(et[-1].fin_seg - dur) > TOL:
        errs.append(f"las etapas terminan en {et[-1].fin_seg:.2f}s pero la duración es {dur:.2f}s")
    for i, e in enumerate(et):
        if e.dia_fin < e.dia_inicio:
            errs.append(f"etapas[{i}]: dia_fin < dia_inicio")
        if i and e.dia_inicio < et[i - 1].dia_fin:
            errs.append(f"etapas[{i}]: el conteo de días retrocede ({et[i-1].dia_fin} → {e.dia_inicio})")
        if e.dia_fin > s.contador.dias_totales:
            errs.append(f"etapas[{i}]: dia_fin {e.dia_fin} supera contador.dias_totales {s.contador.dias_totales}")
    rev = s.first_stage("revelacion")
    r = s.revelacion
    if rev is not None:
        if r.flash_offset_seg > rev.duracion_seg:
            errs.append("revelacion.flash_offset_seg cae fuera de la etapa 'revelacion'")
        objs = INTERIORS[r.tipo_interior].OBJECTS
        for j, c in enumerate(r.callouts):
            if c.objeto not in objs:
                errs.append(
                    f"revelacion.callouts[{j}].objeto '{c.objeto}' no existe en '{r.tipo_interior}' "
                    f"(opciones: {', '.join(objs)})"
                )
            if rev.inicio_seg + c.aparicion_seg > dur:
                errs.append(f"revelacion.callouts[{j}] aparece después del final del video")
    if s.cta.final.aparicion_seg > dur:
        errs.append("cta.final.aparicion_seg supera la duración")
    if s.cta.intermedio.activo and s.cta.intermedio.aparicion_seg + s.cta.intermedio.duracion_seg > dur:
        errs.append("cta.intermedio termina después del final del video")
    if s.exportacion.portada.tiempo_seg > dur:
        errs.append("exportacion.portada.tiempo_seg supera la duración")
    return errs


# Reescalado ------------------------------------------------------------------
def rescale_times(data: dict, duracion: Optional[float] = None) -> dict:
    """Reparte proporcionalmente las duraciones de las etapas para llenar la duración total,
    encadena los inicios y ajusta los tiempos absolutos (CTA, portada). Opera sobre un dict
    (puede ser inválido) y devuelve uno nuevo."""
    d = copy.deepcopy(data)
    g = d.setdefault("general", {})
    old_total = float(g.get("duracion_seg", 62.0))
    total = float(duracion if duracion is not None else old_total)
    g["duracion_seg"] = total
    hook = float(d.get("gancho", {}).get("duracion_seg", 2.5))
    etapas = d.get("etapas") or []
    if not etapas:
        return d
    avail = max(0.3 * len(etapas), total - hook)
    durs = [max(0.05, float(e.get("duracion_seg", 1.0))) for e in etapas]
    k = avail / sum(durs)
    durs = [round(x * k, 3) for x in durs]
    durs[-1] = round(avail - sum(durs[:-1]), 3)
    t = hook
    for e, x in zip(etapas, durs):
        e["inicio_seg"] = round(t, 3)
        e["duracion_seg"] = x
        t += x
    ratio = total / old_total if old_total else 1.0
    cta = d.get("cta", {})
    for key in ("final", "intermedio"):
        c = cta.get(key)
        if c and "aparicion_seg" in c:
            c["aparicion_seg"] = round(min(total - 0.5, float(c["aparicion_seg"]) * ratio), 3)
    # el CTA final nunca antes del cierre si existe
    cierre = next((e for e in etapas if e.get("tipo") == "cierre"), None)
    if cierre and cta.get("final"):
        cta["final"]["aparicion_seg"] = round(max(cta["final"]["aparicion_seg"], cierre["inicio_seg"]), 3)
    inter = cta.get("intermedio")
    if inter:
        inter["aparicion_seg"] = round(
            min(inter["aparicion_seg"], total - float(inter.get("duracion_seg", 3.0))), 3
        )
    port = d.get("exportacion", {}).get("portada")
    if port and float(port.get("tiempo_seg", -1)) > 0:
        port["tiempo_seg"] = round(min(total, float(port["tiempo_seg"]) * ratio), 3)
    rev = next((e for e in etapas if e.get("tipo") == "revelacion"), None)
    if rev and d.get("revelacion"):
        r = d["revelacion"]
        r["flash_offset_seg"] = round(min(float(r.get("flash_offset_seg", 0)), rev["duracion_seg"]), 3)
        for c in r.get("callouts", []):
            c["aparicion_seg"] = round(min(float(c.get("aparicion_seg", 0)), rev["duracion_seg"] - 0.3), 3)
    return d


def chain_starts(data: dict) -> dict:
    """Recalcula inicio_seg encadenando las duraciones (sin reescalar)."""
    d = copy.deepcopy(data)
    t = float(d.get("gancho", {}).get("duracion_seg", 2.5))
    for e in d.get("etapas", []):
        e["inicio_seg"] = round(t, 3)
        t += float(e.get("duracion_seg", 1))
    return d


def scene_json_schema() -> dict:
    return Scene.model_json_schema()


_UNSUPPORTED = {"pattern", "format", "minLength", "maxLength", "minimum", "maximum",
                "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems", "default", "title"}


def llm_schema(model: type[BaseModel]) -> dict:
    """JSON Schema apto para salida estructurada: las restricciones numéricas/longitudes se pasan a
    la descripción (Pydantic las valida después)."""

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            extra = []
            for k in ("minimum", "maximum", "maxLength", "minItems", "maxItems", "pattern"):
                if k in node:
                    extra.append(f"{k}={node[k]}")
            out = {k: walk(v) for k, v in node.items() if k not in _UNSUPPORTED or k == "properties"}
            if "properties" in node:
                out["properties"] = {k: walk(v) for k, v in node["properties"].items()}
                out["required"] = list(node["properties"].keys())
                out["additionalProperties"] = False
            if extra:
                out["description"] = (out.get("description", "") + f" [{', '.join(extra)}]").strip()
            return out
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(model.model_json_schema())
