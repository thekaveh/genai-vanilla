"""
Ollama library catalog discovery — scrape ``https://ollama.com/library``
for the canonical list of public Ollama models.

Used by the wizard's ``ollama-container-*`` source multi-select to
present a live catalog of models the user can pre-select for
``ollama-pull`` to fetch at startup, instead of our hardcoded
curated subset in ``llm_catalog.py:OLLAMA_DEFAULT_CATALOG``.

For ``ollama-localhost``/``ollama-external``, ``ollama_discovery.py``
already queries the live ``/api/tags`` endpoint of the user's running
upstream — that path stays unchanged.

Why scrape?
  Ollama's registry (``registry.ollama.ai/v2/_catalog``) returns 404,
  no public JSON API exists for the library, and ollamadb.dev returns
  empty. The library web page has a stable structure where each model
  card is rendered as ``<a href="/library/<name>">`` — we extract the
  unique names with a regex. Best-effort + safe fallback.
"""

from __future__ import annotations

import re
import socket
import urllib.error
import urllib.request

_LIBRARY_URL = "https://ollama.com/library"
_LIBRARY_HREF_RE = re.compile(r'href="/library/([a-z0-9._-]+)"')


def list_library_models(timeout: float = 5.0) -> list[str]:
    """Fetch and parse the public Ollama library page.

    Returns a sorted list of unique model names (e.g.
    ``['deepseek-r1', 'gemma3', 'llama3.3', 'nomic-embed-text', ...]``).
    Returns an empty list on any failure (network, timeout, parse) —
    the caller falls back to the curated ``OLLAMA_DEFAULT_CATALOG``.
    """
    try:
        req = urllib.request.Request(
            _LIBRARY_URL,
            headers={
                # Ollama's library page is server-rendered; a regular
                # browser UA gets the same HTML. Setting one avoids
                # potential gating on missing UAs.
                "User-Agent": "genai-vanilla-bootstrapper/1.0 (+wizard catalog fetch)",
                "Accept": "text/html",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError):
        return []
    names = set(_LIBRARY_HREF_RE.findall(html))
    if not names:
        return []
    return sorted(names)
