# TimelapseForge

Generador local de videos verticales (9:16) de **timelapse de construcción animados** para TikTok, del estilo
«construí un búnker en mi patio → la revelación final es un cuarto gamer».

```
1. Ideas  →  2. Guion  →  3. Editor  →  4. Render
```

1. **Ideas**: escribes un tema (opcional) y Claude propone 5 ideas (título, gancho de ≤ 8 palabras, qué se construye, revelación, tono, por qué funciona).
2. **Guion**: eliges una idea; Claude escribe la descripción detallada (Markdown editable) y el **JSON de escena** validado. Puedes pedir cambios en texto libre («haz la excavación más larga», «cambia la revelación a un cine»).
3. **Editor**: todos los campos del JSON como formulario (secciones plegables, colores, deslizadores, listas reordenables), validación en vivo, vista previa con barra de tiempo, miniaturas por etapa, «Reescalar tiempos», deshacer por versiones y «Borrador rápido» (540×960, 15 fps).
4. **Render**: MP4 final con música y efectos originales, progreso en tiempo real (SSE), cancelación, y descarga del video, la portada PNG y el texto de publicación.

## Principio de arquitectura

- **El LLM nunca escribe código de render.** Solo produce o edita un JSON que cumple el esquema estricto de `engine/schema.py`.
- **El motor es determinista y guiado por datos**: mismo JSON + misma `seed` ⇒ mismo video (texturas, audio y animaciones salen de la semilla).
- Toda salida de Claude se valida con Pydantic. Si falla, se reintenta **una vez** pasándole a Claude los errores; si vuelve a fallar, el error se muestra en la interfaz.

## Requisitos

- Python 3.11+
- Node.js 18+ (para el frontend)
- **ffmpeg** (con `ffprobe`)
- **Claude Code** con la sesión iniciada (`claude login`). La app usa el **Claude Agent SDK** (`claude-agent-sdk`), que habla con Claude a través de Claude Code y tu suscripción/sesión: **no necesitas `ANTHROPIC_API_KEY`**.

### Instalar ffmpeg

| Sistema | Comando |
|---|---|
| macOS (Homebrew) | `brew install ffmpeg` |
| Ubuntu / Debian | `sudo apt update && sudo apt install -y ffmpeg` |
| Fedora | `sudo dnf install -y ffmpeg` (habilita RPM Fusion) |
| Arch | `sudo pacman -S ffmpeg` |
| Windows | `winget install Gyan.FFmpeg` o `choco install ffmpeg`, y abre una terminal nueva |

Comprueba con `ffmpeg -version` y `ffprobe -version`.

### Claude Code

```bash
npm install -g @anthropic-ai/claude-code   # opcional: el SDK de Python ya trae un CLI empaquetado
claude login                               # inicia sesión una vez
```

## Instalación y arranque

```bash
python3 -m venv .venv && source .venv/bin/activate   # opcional (run.sh lo detecta)
make install          # pip install -r requirements.txt + npm install en frontend/
cp .env.example .env  # opcional: modelo, núcleos…
make dev              # o ./run.sh
```

- Frontend: http://localhost:5173
- API: http://127.0.0.1:8000 (el frontend la usa por proxy en `/api`)

`make build` compila el frontend a `frontend/dist`; si existe, el backend también lo sirve en http://127.0.0.1:8000.

### Configuración (`.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `CLAUDE_MODEL` | `claude-sonnet-5` | Modelo usado por el Agent SDK |
| `TF_WORKERS` | nº CPUs − 1 | Núcleos del pool de render |
| `TF_PROJECTS_DIR` | `./projects` | Dónde se guardan los proyectos |
| `TF_ALLOW_API_KEY` | `0` | Con `0` se fuerza la sesión de Claude Code aunque haya `ANTHROPIC_API_KEY` en el entorno |
| `TF_LLM_TIMEOUT` | `300` | Segundos máximos por llamada a Claude |

## Línea de comandos

```bash
python -m engine.render examples/bunker_gamer.json            # 1080×1920, 30 fps → output/bunker_gamer.mp4
python -m engine.render examples/bunker_gamer.json --draft    # borrador 540×960, 15 fps
python -m engine.render examples/bunker_gamer.json --cover --workers 4 -o salida.mp4
make test                                                     # pytest
```

`examples/bunker_gamer.json` reproduce el video de referencia de 62 s (búnker → cuarto gamer).
Referencia de rendimiento medida en 4 núcleos: 1860 fotogramas 1080×1920 en ~144 s ≈ **0,31 s por fotograma y núcleo** (incluye audio y codificación).

## Estructura

```
engine/                 motor determinista guiado por JSON
  schema.py             esquema Pydantic (11 secciones), validación de coherencia, reescalado
  catalog.py            tipos de etapa, poses, máquinas, interiores (se pasa a los prompts)
  defaults.py           etapas por defecto (video de referencia)
  world.py              geometría metros→px (escala coherente con la altura de los obreros), utilidades
  assets.py             texturas procedurales cacheadas en disco por hash (.cache/assets)
  actors.py             obreros por poses, excavadora con cinemática inversa, manguera de concreto
  stages/*.py           una clase por tipo de etapa: draw(canvas, t_local, ctx) y sfx_events(t0, t1)
  interiors/*.py        un interior por tipo de revelación; OBJECTS con coordenadas para los callouts
  camera.py ui.py grade.py   cámara, textos/contador/barra/callouts/CTA, día/noche + viñeta + flash
  audio.py              música (yunque + marimba → drop electrónico/chiptune), SFX, LUFS (BS.1770)
  frame.py              compone un fotograma: mundo a 2× → recorte de cámara → cielo, gradación, UI
  render.py             pool multiproceso → pipe a ffmpeg (libx264, yuv420p, +faststart) + audio; CLI
backend/app/            FastAPI: ideas, escena, edición, vista previa, cola de render con SSE, proyectos
frontend/               React + Vite + TypeScript + Tailwind (asistente de 4 pasos)
examples/bunker_gamer.json
tests/                  pytest
projects/<id>/          scene.json, ideas.json, idea.json, descripcion.md, history/, previews/, uploads/, output/
```

### Técnica de render

- El mundo se dibuja a 2× el tamaño de salida y la cámara recorta/redimensiona (supermuestreo). El borrador usa 1×.
- Las texturas son del tamaño del mundo y se pegan por rectángulos/polígonos (crop + paste) alineadas al mundo.
- Las etapas terminadas se cachean en una capa por proceso; en cada fotograma solo se dibuja la etapa activa, los actores y el montón de tierra.
- Día/noche con `Image.blend` (cielos de día/atardecer/noche y tinte nocturno del mundo).
- Los trabajadores del pool reciben bloques de fotogramas contiguos para aprovechar la caché.

### Catálogo del motor (v1)

Etapas: `marcado`, `excavacion`, `grava_acero`, `losa`, `muros` (encofrado → vaciado → desencofrado),
`techo` (puntales → acero → vaciado → ducto de escotilla), `impermeabilizacion`, `relleno`,
`acabados` (pasto en rollos, ventilación, escotilla), `terminado`, `pregunta`, `revelacion`, `cierre`.

Interiores: `gamer`, `cine`, `gimnasio`, `spa`, `bodega_snacks`, `streaming`, `oficina`.

Estilo visual: `corte_lateral` (el campo `estilo_visual` queda listo para estilos futuros).

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado de ffmpeg y Claude Code |
| GET | `/api/schema`, `/api/catalog`, `/api/defaults` | Esquema JSON, catálogo, escena por defecto |
| POST | `/api/ideas` | `{tema, duracion_seg, tono, idioma}` → 5 ideas |
| POST | `/api/scene` | `{project_id, idea, duracion_seg}` → `descripcion_md` + `scene` |
| POST | `/api/scene/edit` | `{project_id, instruccion}` → escena modificada |
| POST | `/api/validate`, `/api/rescale` | Validación en vivo y reescalado de tiempos |
| POST | `/api/preview` | `{scene, times[]}` → PNG 540×960 (data URLs) |
| POST | `/api/render` | `{project_id, borrador}` → trabajo |
| GET | `/api/jobs/{id}/events` | Progreso por SSE |
| POST | `/api/jobs/{id}/cancel` | Cancelar |
| PUT/POST | `/api/projects/{id}/scene`, `/undo`, `/upload`, `/post-text` | Guardar versión, deshacer, subir fuente/música, texto de publicación |

## Notas

- La guía de zonas seguras (lo que tapa la interfaz de TikTok a la derecha y abajo) solo aparece en la vista previa, nunca en el render.
- «Tamaño máximo» limita el bitrate (`-maxrate`) según la duración; si aun así se pasa, se reencoda con bitrate fijo.
- El texto de publicación incluye 5–8 hashtags y la recomendación de marcar la etiqueta de «contenido generado por IA».
- Las texturas se cachean en `.cache/assets`; bórrala con `make clean` si cambias el motor.
