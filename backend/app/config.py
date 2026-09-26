"""Configuración leída de .env / variables de entorno."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[2]
if load_dotenv:
    load_dotenv(ROOT / ".env")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
PROJECTS_DIR = Path(os.environ.get("TF_PROJECTS_DIR", ROOT / "projects"))
WORKERS = int(os.environ.get("TF_WORKERS", "0")) or max(1, (os.cpu_count() or 2) - 1)
# Por defecto se usa la sesión de Claude Code (`claude login`), no una API key.
ALLOW_API_KEY = os.environ.get("TF_ALLOW_API_KEY", "0") == "1"
LLM_TIMEOUT = float(os.environ.get("TF_LLM_TIMEOUT", "300"))
