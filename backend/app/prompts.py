"""Modelos de respuesta del LLM y prompts de sistema."""
from __future__ import annotations

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from engine.brand import locked_paths
from engine.catalog import catalog_text
from engine.schema import Scene


class Idea(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str = Field(description="Título del video", max_length=80)
    gancho: str = Field(description="Texto de apertura, 8 palabras o menos", max_length=60)
    proyecto: str = Field(description="Qué se construye (búnker, piscina, sótano, cisterna, túnel…)", max_length=60)
    revelacion: str = Field(description="Giro final; debe ser uno de los tipos de interior del motor", max_length=40)
    tono: Literal["divertido", "serio", "misterioso"]
    por_que_funciona: str = Field(description="Una línea de estrategia de retención", max_length=200)
    estilo_visual: Literal["corte_lateral"] = "corte_lateral"

    @field_validator("gancho")
    @classmethod
    def _max_8_words(cls, v: str) -> str:
        if len(v.split()) > 8:
            raise ValueError(f"el gancho '{v}' tiene más de 8 palabras")
        return v


class IdeasResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ideas: list[Idea] = Field(min_length=5, max_length=5)


MAX_HASHTAGS = 5  # TikTok no deja pegar más de 5 hashtags en la descripción


class PostText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: str = Field(description="Descripción/caption corta para TikTok, sin hashtags", max_length=600)
    hashtags: list[str] = Field(min_length=3, description=f"Exactamente {MAX_HASHTAGS} hashtags con # (máximo de TikTok)")
    etiqueta_ia: bool = Field(description="Recomendación de marcar la etiqueta 'contenido generado por IA'")
    nota_etiqueta_ia: str = Field(max_length=300)

    @field_validator("hashtags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        """'#Mi Patio', 'patio' → '#MiPatio', '#patio' (sin duplicados, máximo MAX_HASHTAGS), listos para pegar."""
        out: list[str] = []
        for tag in v:
            t = "#" + re.sub(r"[\s#]+", "", tag)
            if len(t) > 1 and t.lower() not in (x.lower() for x in out):
                out.append(t)
        if len(out) < 3:
            raise ValueError(f"se necesitan {MAX_HASHTAGS} hashtags distintos")
        return out[:MAX_HASHTAGS]


class SceneResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion_md: str = Field(description="Documento Markdown legible con toda la descripción del video")
    scene: Scene
    publicacion: Optional[PostText] = Field(None, description="Texto de publicación para TikTok")


class SceneOnly(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: Scene
    cambios: str = Field(description="Resumen breve de los cambios hechos", max_length=500)


BASE = """Eres guionista experto en videos virales de TikTok del formato "timelapse de construcción animado":
una vista en corte lateral de un patio donde obreros construyen algo bajo tierra durante semanas
(con contador de días), y al final una revelación sorpresa del interior. El video es vertical 9:16.

El motor de render es determinista y SOLO sabe dibujar lo siguiente (no inventes otros tipos):
{catalog}

ESTILO DEL CANAL: todos los videos del canal comparten el mismo estilo visual y sonoro. Estos campos
están fijados por la plantilla de marca y se sobrescriben automáticamente; no los cambies:
{marca}
Toda la variedad entre videos debe venir del CONTENIDO: qué se construye, etapas y su ritmo, días,
títulos, subtítulos con humor, gancho, pregunta, falsa expectativa, remate, interior revelado con sus
colores de acento/LEDs, callouts, texto de cierre y CTA intermedio.
La música de cada video la definen general.seed (arreglo) y audio.progresion (acordes); se asignan al azar
al crear el video. Mantenlos salvo que se pida explícitamente cambiar la música.
"""

IDEAS_SYSTEM = BASE + """
Tarea: proponer exactamente 5 ideas de video.
Reglas:
- Deben poder construirse con los tipos de etapa y de interior de arriba. El campo `revelacion`
  debe nombrar uno de los tipos de interior (gamer, cine, gimnasio, spa, bodega_snacks, streaming, oficina).
- Las 5 ideas deben ser variadas (distinto proyecto, distinta revelación, distintos ganchos).
- Si se te da una lista de ideas ya usadas en el canal, no las repitas ni hagas variaciones obvias:
  prioriza proyectos, revelaciones y ganchos que el canal aún no ha usado o ha usado menos.
- El gancho tiene 8 palabras o menos, en mayúsculas es mejor, y debe generar curiosidad inmediata.
- `estilo_visual` siempre "corte_lateral".
- Escribe en el idioma pedido.
"""

POST_RULES = """Texto de publicación (se copia y pega tal cual en TikTok):
- `descripcion`: 1 a 3 frases cortas: gancho que despierte curiosidad sin destripar la revelación y una
  pregunta que invite a comentar. Puede llevar 1 o 2 emojis. Sin hashtags dentro de la descripción.
- `hashtags`: exactamente 5 (TikTok no permite más), cada uno con # y sin espacios; mezcla 2 amplios
  (p. ej. #timelapse, #construccion) con 3 específicos del proyecto y de la revelación.
- `etiqueta_ia` = true y `nota_etiqueta_ia`: una línea que explique que conviene marcar la etiqueta de
  "contenido generado por IA" porque el video es una animación generada por computadora con guion asistido por IA.
"""

SCENE_SYSTEM = BASE + """
Tarea: a partir de una idea elegida, escribir (1) `descripcion_md`: un documento Markdown legible que
explique qué se construye, la secuencia completa con tiempos (segundo a segundo por etapa), materiales,
personajes y máquinas, los textos de cada momento, la revelación, el CTA y la música; y (2) `scene`:
el JSON de escena completo que cumple el esquema; y (3) `publicacion`: el texto de publicación del video.

Reglas del JSON (se validan automáticamente):
- etapas en orden lógico; la primera empieza en gancho.duracion_seg; cada etapa empieza donde termina la
  anterior (inicio_seg = inicio anterior + duración anterior); la última termina exactamente en
  general.duracion_seg. Sin huecos ni solapes.
- dia_inicio <= dia_fin; el conteo de días nunca retrocede; dia_fin <= contador.dias_totales.
- Incluye al final las etapas 'terminado', 'pregunta', 'revelacion' y 'cierre' (con obreros=0 en las 3 últimas).
- revelacion.flash_offset_seg <= duración de la etapa revelacion; callouts (máx. 5) con `objeto` elegido
  SOLO de la lista de objetos del tipo de interior elegido; aparicion_seg relativo al inicio de 'revelacion'.
- cta.final.aparicion_seg y cta.intermedio (si activo) dentro de la duración; el CTA final suele ir en 'cierre'.
- Respeta longitudes máximas: titulo de etapa ≤ 28, subtitulo ≤ 48, callout ≤ 24, remate_2 ≤ 30.
- Colores en formato #RRGGBB. general.estilo_visual = "corte_lateral".
- Escribe textos nuevos pensados para esta idea: no copies los títulos, subtítulos ni remates del JSON
  de referencia.
- Títulos cortos y en mayúsculas; subtítulos con humor. Máquinas: excavadora en excavacion/relleno,
  bomba_concreto en losa/muros/techo.
- Si la duración es > 60 s recuerda que ayuda a monetizar; ajusta duraciones para mantener el ritmo
  (etapas de 2.5–8 s, revelación 6–10 s).

""" + POST_RULES

EDIT_SYSTEM = BASE + """
Tarea: modificar un JSON de escena existente siguiendo una instrucción del usuario. Devuelve la escena
completa modificada (no solo los cambios) manteniendo todo lo demás igual y respetando las mismas reglas
de coherencia: etapas encadenadas sin huecos/solapes que terminan en general.duracion_seg, días que no
retroceden, callouts con objetos válidos del interior, longitudes máximas.
Mantén general.duracion_seg igual salvo que la instrucción pida cambiar la duración: si alargas una etapa,
acorta proporcionalmente las demás para que el total no cambie.
Si la instrucción pide cambiar un campo del estilo del canal, no lo cambies y explica en `cambios` que ese
campo es fijo para todos los videos y se cambia en brand.json.
"""

POST_SYSTEM = """Eres community manager experto en TikTok. Escribe el texto de publicación para un video
de timelapse de construcción animado.
""" + POST_RULES + "Escribe en el idioma indicado."


def ideas_prompt(tema: str, duracion: float, tono: str, idioma: str, usadas: list[dict] = ()) -> str:
    prev = ""
    if usadas:
        prev = "\nIdeas ya usadas en el canal (no las repitas):\n" + "\n".join(
            f"- {i.get('titulo', '')} | {i.get('proyecto', '')} → {i.get('revelacion', '')} | gancho: {i.get('gancho', '')}"
            for i in usadas) + "\n"
    return (f"Tema o nicho: {tema or '(libre, sorpréndeme)'}\nDuración objetivo: {duracion} s\n"
            f"Tono preferido: {tono or 'variado'}\nIdioma: {idioma}\n{prev}Devuelve 5 ideas.")


def scene_prompt(idea: dict, duracion: float, idioma: str, defaults: dict) -> str:
    return (f"Idea elegida:\n{json.dumps(idea, ensure_ascii=False, indent=1)}\n\nDuración total: {duracion} s. "
            f"Idioma: {idioma}.\nComo referencia de formato y valores sensatos, este es un JSON de escena válido "
            f"(adáptalo a la idea: cambia textos, etapas, días, interior, callouts y CTA; conserva el estilo del canal):\n"
            f"{json.dumps(defaults, ensure_ascii=False)}")


def edit_prompt(scene: dict, instruccion: str) -> str:
    return f"Instrucción: {instruccion}\n\nJSON actual:\n{json.dumps(scene, ensure_ascii=False)}"


def post_prompt(scene: Scene, descripcion_md: str) -> str:
    r = scene.revelacion
    hook = " ".join(ln.texto for ln in scene.gancho.lineas)
    return (f"Idioma: {scene.general.idioma}\nTítulo: {scene.general.titulo}\nGancho: {hook}\n"
            f"Revelación: {r.tipo_interior} — {r.remate_1} {r.remate_2}\nCTA: {scene.cta.final.texto}\n"
            f"Resumen del guion:\n{descripcion_md[:2500]}")


def system(kind: str) -> str:
    tmpl = {"ideas": IDEAS_SYSTEM, "scene": SCENE_SYSTEM, "edit": EDIT_SYSTEM}[kind]
    marca = "\n".join(f"- {p}" for p in locked_paths()) or "- (ninguno)"
    return tmpl.format(catalog=catalog_text(), marca=marca)
