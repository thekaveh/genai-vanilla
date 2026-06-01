"""
Ollama upstream discovery — query ``/api/tags`` for the list of
locally-pulled models.

Used by the wizard step builder when ``LLM_PROVIDER_SOURCE`` resolves
to ``ollama-localhost``: instead of guessing from the curated catalog,
we ask the live upstream what's actually available so the user picks
from real options.

For ``ollama-container-cpu`` / ``ollama-container-gpu``, the container
isn't running yet at wizard time — the caller falls back to the
curated catalog there.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request


def list_pulled_models(upstream_url: str, timeout: float = 2.0) -> list[str]:
    """GET ``{upstream_url}/api/tags`` and return the model names.

    Returns an empty list on any failure (connection refused, timeout,
    bad JSON, server unreachable). The caller should treat an empty
    return as "discovery failed; fall back."
    """
    if not upstream_url:
        return []
    base = upstream_url.rstrip("/")
    url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError):
        return []
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return []
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    out: list[str] = []
    for entry in models:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("model")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out
