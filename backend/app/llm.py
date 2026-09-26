"""Cliente LLM basado en el Claude Agent SDK (usa la sesión de Claude Code, no una API key).

Toda salida se pide como JSON estructurado (output_format=json_schema generado desde Pydantic) y
se valida con Pydantic. Si falla, se reintenta una vez pasando los errores a Claude."""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from typing import Callable, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from backend.app import config
from engine.schema import llm_schema

log = logging.getLogger("tf.llm")
T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    def __init__(self, message: str, code: str = "llm_error", details: Optional[list] = None):
        super().__init__(message)
        self.code = code
        self.details = details or []


def claude_available() -> dict:
    try:
        import claude_agent_sdk  # noqa: F401
    except Exception as e:  # pragma: no cover
        return {"ok": False, "detail": f"claude-agent-sdk no instalado: {e}"}
    cli = shutil.which("claude")
    bundled = False
    try:
        from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport  # noqa: F401

        import claude_agent_sdk as sdk
        from pathlib import Path

        bundled = any(Path(sdk.__file__).parent.glob("_bundled/claude*"))
    except Exception:
        pass
    ok = bool(cli or bundled)
    return {"ok": ok, "cli": cli, "bundled": bundled,
            "detail": "" if ok else "No se encontró Claude Code. Instálalo (npm i -g @anthropic-ai/claude-code) y ejecuta `claude login`."}


async def _query_json(system: str, prompt: str, schema: dict, model: Optional[str]) -> dict:
    from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, CLINotFoundError, ProcessError,
                                  ResultMessage, TextBlock, query)

    env = {} if config.ALLOW_API_KEY else {"ANTHROPIC_API_KEY": ""}
    opts = ClaudeAgentOptions(
        system_prompt=system,
        model=model or config.CLAUDE_MODEL,
        tools=[],
        allowed_tools=[],
        setting_sources=[],
        max_turns=4,
        cwd=tempfile.gettempdir(),
        env=env,
        output_format={"type": "json_schema", "schema": schema},
    )
    result: Optional[ResultMessage] = None
    texts: list[str] = []
    try:
        async for msg in query(prompt=prompt, options=opts):
            if isinstance(msg, ResultMessage):
                result = msg
            elif isinstance(msg, AssistantMessage):
                texts += [b.text for b in msg.content if isinstance(b, TextBlock)]
    except CLINotFoundError as e:
        raise LLMError("No se encontró Claude Code. Instálalo y ejecuta `claude login`.", "claude_missing") from e
    except ProcessError as e:
        raise LLMError(f"Claude Code falló (¿sesión iniciada con `claude login`?): {e}", "claude_process") from e
    if result is None:
        raise LLMError("Claude no devolvió resultado.")
    if result.is_error:
        txt = (result.result or "") + " " + " ".join(result.errors or [] if isinstance(result.errors, list) else [])
        low = txt.lower()
        if any(k in low for k in ("login", "auth", "api key", "401", "credential")):
            raise LLMError("Claude Code no está autenticado. Ejecuta `claude login` en esta máquina.", "claude_auth")
        raise LLMError(f"Error de Claude: {txt.strip() or result.subtype}")
    if result.structured_output is not None:
        return result.structured_output
    # último recurso: JSON en el texto
    raw = (result.result or "") or "\n".join(texts)
    try:
        start = raw.index("{")
        return json.loads(raw[start: raw.rindex("}") + 1])
    except Exception as e:
        raise LLMError("Claude no devolvió JSON válido.") from e


def _errors(e: Exception) -> list[str]:
    if isinstance(e, ValidationError):
        return [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:40]]
    return [str(e)]


async def structured(system: str, prompt: str, model_cls: type[T], *,
                     prepare: Optional[Callable[[dict], dict]] = None, model: Optional[str] = None) -> T:
    """Pide a Claude un objeto `model_cls`. Valida; si falla reintenta una vez con los errores."""
    schema = llm_schema(model_cls)
    last: list[str] = []
    for attempt in range(2):
        p = prompt
        if attempt == 1:
            p = (prompt + "\n\nTu respuesta anterior NO pasó la validación. Corrige exactamente estos errores "
                 "y devuelve el objeto completo:\n- " + "\n- ".join(last))
        data = await asyncio.wait_for(_query_json(system, p, schema, model), timeout=config.LLM_TIMEOUT)
        try:
            if prepare:
                data = prepare(data)
            return model_cls.model_validate(data)
        except (ValidationError, ValueError) as e:
            last = _errors(e)
            log.warning("validación fallida (intento %s): %s", attempt + 1, last)
    raise LLMError("La respuesta de Claude no pasó la validación tras reintentar.", "validation", last)
