"""Modelos de respuesta del LLM y prompts de sistema."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class SceneResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion_md: str = Field(description="Documento Markdown legible con toda la descripción del video")
    scene: Scene


class SceneOnly(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: Scene
    cambios: str = Field(description="Resumen breve de los cambios hechos", max_length=500)


class PostText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: str = Field(description="Descripción/caption para TikTok", max_length=600)
    hashtags: list[str] = Field(min_length=5, max_length=8, description="Entre 5 y 8 hashtags con #")
    etiqueta_ia: bool = Field(description="Recomendación de marcar la etiqueta 'contenido generado por IA'")
    nota_etiqueta_ia: str = Field(max_length=300)


BASE = """Eres guionista experto en videos virales de TikTok del formato "timelapse de construcción animado":
una vista en corte lateral de un patio donde obreros construyen algo bajo tierra durante semanas
(con contador de días), y al final una revelación sorpresa del interior. El video es vertical 9:16.

El motor de render es determinista y SOLO sabe dibujar lo siguiente (no inventes otros tipos):
{catalog}
"""

IDEAS_SYSTEM = BASE + """
Tarea: proponer exactamente 5 ideas de video.
Reglas:
- Deben poder construirse con los tipos de etapa y de interior de arriba. El campo `revelacion`
  debe nombrar uno de los tipos de interior (gamer, cine, gimnasio, spa, bodega_snacks, streaming, oficina).
- Las 5 ideas deben ser variadas (distinto proyecto, distinta revelación, distintos ganchos).
- El gancho tiene 8 palabras o menos, en mayúsculas es mejor, y debe generar curiosidad inmediata.
- `estilo_visual` siempre "corte_lateral".
- Escribe en el idioma pedido.
"""

SCENE_SYSTEM = BASE + """
Tarea: a partir de una idea elegida, escribir (1) `descripcion_md`: un documento Markdown legible que
explique qué se construye, la secuencia completa con tiempos (segundo a segundo por etapa), materiales,
personajes y máquinas, los textos de cada momento, la revelación, el CTA y la música; y (2) `scene`:
el JSON de escena completo que cumple el esquema.

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
- Títulos cortos y en mayúsculas; subtítulos con humor. Máquinas: excavadora en excavacion/relleno,
  bomba_concreto en losa/muros/techo.
- Si la duración es > 60 s recuerda que ayuda a monetizar; ajusta duraciones para mantener el ritmo
  (etapas de 2.5–8 s, revelación 6–10 s).
"""

EDIT_SYSTEM = BASE + """
Tarea: modificar un JSON de escena existente siguiendo una instrucción del usuario. Devuelve la escena
completa modificada (no solo los cambios) manteniendo todo lo demás igual y respetando las mismas reglas
de coherencia: etapas encadenadas sin huecos/solapes que terminan en general.duracion_seg, días que no
retroceden, callouts con objetos válidos del interior, longitudes máximas.
"""

POST_SYSTEM = """Eres community manager experto en TikTok. Escribe el texto de publicación para un video
de timelapse de construcción animado: una descripción corta con gancho y pregunta para comentarios,
5 a 8 hashtags relevantes (con #), y recomienda marcar la etiqueta de "contenido generado por IA"
(el video es una animación generada por computadora con guion asistido por IA) explicando por qué en una línea.
Escribe en el idioma indicado."""


def ideas_prompt(tema: str, duracion: float, tono: str, idioma: str) -> str:
    return (f"Tema o nicho: {tema or '(libre, sorpréndeme)'}\nDuración objetivo: {duracion} s\n"
            f"Tono preferido: {tono or 'variado'}\nIdioma: {idioma}\nDevuelve 5 ideas.")


def scene_prompt(idea: dict, duracion: float, idioma: str, defaults: dict) -> str:
    return (f"Idea elegida:\n{json.dumps(idea, ensure_ascii=False, indent=1)}\n\nDuración total: {duracion} s. "
            f"Idioma: {idioma}.\nComo referencia de formato y valores sensatos, este es un JSON de escena válido "
            f"(adáptalo a la idea, cambia textos, etapas, interior, colores, callouts, CTA):\n"
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
    return tmpl.format(catalog=catalog_text())
