#!/usr/bin/env bash
# Arranca backend (FastAPI :8000) y frontend (Vite :5173) con un solo comando.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ -d .venv ]; then PY=.venv/bin/python; fi

command -v ffmpeg >/dev/null || echo "⚠️  ffmpeg no está instalado: el render fallará (ver README)."
command -v claude >/dev/null || $PY -c "import claude_agent_sdk" 2>/dev/null || echo "⚠️  Claude Code no encontrado: instala el SDK y ejecuta 'claude login'."

if [ ! -d frontend/node_modules ]; then (cd frontend && npm install); fi

$PY -m uvicorn backend.app.main:app --host 127.0.0.1 --port "${TF_PORT:-8000}" &
BACK=$!
trap 'kill $BACK 2>/dev/null || true' EXIT INT TERM
echo "▶ Backend en http://127.0.0.1:${TF_PORT:-8000}  ·  Frontend en http://localhost:5173"
cd frontend && npx vite --port 5173
