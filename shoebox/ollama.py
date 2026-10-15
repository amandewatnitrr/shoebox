"""Minimal Ollama client on the standard library. Talks only to your own machine by default."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import List, Optional


class OllamaError(RuntimeError):
    pass


def default_host() -> str:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").strip()
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host.rstrip("/")


def _request(host: str, path: str, payload: Optional[dict], timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        host + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise OllamaError(
            f"Cannot reach Ollama at {host}. Is `ollama serve` running? ({exc})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama sent a response that is not JSON.") from exc


def list_models(host: str, timeout: float = 10) -> List[str]:
    body = _request(host, "/api/tags", None, timeout)
    return [m.get("name", "") for m in body.get("models", [])]


def has_model(installed: List[str], wanted: str) -> bool:
    if ":" in wanted:
        return wanted in installed
    return any(name == wanted or name.startswith(wanted + ":") for name in installed)


def chat(
    host: str,
    model: str,
    system: str,
    user: str,
    images: Optional[List[str]] = None,
    schema: Optional[dict] = None,
    timeout: float = 300,
) -> str:
    """Single non-streaming chat turn. `images` are base64 strings."""
    message = {"role": "user", "content": user}
    if images:
        message["images"] = images
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "system", "content": system}, message],
        "options": {"temperature": 0},
    }
    if schema:
        payload["format"] = schema
    body = _request(host, "/api/chat", payload, timeout)
    try:
        return body["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaError(f"Unexpected Ollama response shape: {str(body)[:200]}") from exc
