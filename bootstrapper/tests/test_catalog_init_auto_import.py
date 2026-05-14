"""
Unit tests for the Ollama auto-import helper in
``services/litellm/catalog-init/scripts/sync-catalog.py``.

The catalog-init script normally runs inside its own Docker container
with ``psycopg2`` installed; we want to exercise the new helper from
the bootstrapper test suite without spinning up the container or
Postgres. Two pieces have to be set up:

  1. ``psycopg2`` is stubbed in ``sys.modules`` BEFORE the script's
     module-level ``import psycopg2`` executes — otherwise import
     fails with ModuleNotFoundError.
  2. The script is loaded via ``importlib.util.spec_from_file_location``
     since it lives outside any Python package and isn't importable
     by name.

After load, ``_fetch_ollama_tags`` is callable like any other
function and we monkeypatch ``urllib.request.urlopen`` to control
what /api/tags "returns" without making real HTTP calls.

This covers the new code path added in the auto-import fix:
when ``LLM_PROVIDER_SOURCE=ollama-localhost`` and
``OLLAMA_AUTO_IMPORT_LOCAL_MODELS=true``, the catalog-init queries
the host upstream and unions the result into ``OLLAMA_USER_MODELS``.
``_fetch_ollama_tags`` is the wire-level building block; if it
mis-parses or mis-fails, every downstream behaviour breaks.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / "services" / "litellm" / "catalog-init" / "scripts" / "sync-catalog.py"
)


@pytest.fixture(scope="module")
def sync_catalog():
    """Load ``sync-catalog.py`` as a module with ``psycopg2`` stubbed.

    Module-scoped so we don't re-stub-and-reload on every test. The
    stub only needs to be present in ``sys.modules`` during import;
    once loaded, the script's top-level references are bound and
    we can remove the stub without affecting the loaded module.
    """
    # Build the psycopg2 stub. Only the attributes referenced by the
    # script's top-level code need to exist; everything else can be
    # a MagicMock for safety.
    psycopg2_stub = MagicMock()
    psycopg2_extras_stub = MagicMock()
    sys.modules.setdefault("psycopg2", psycopg2_stub)
    sys.modules.setdefault("psycopg2.extras", psycopg2_extras_stub)

    spec = importlib.util.spec_from_file_location(
        "sync_catalog_for_test", SCRIPT_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ────────────────────────────────────────────────────────────────────────────
# _fetch_ollama_tags — the wire-level helper
# ────────────────────────────────────────────────────────────────────────────


class _FakeResponse:
    """Minimal context-manager that mimics ``http.client.HTTPResponse``
    enough for ``json.loads(resp.read().decode())`` to succeed."""

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def _stub_urlopen_returns(monkeypatch, body: bytes | str):
    """Patch ``urllib.request.urlopen`` to return a fake response
    serving ``body`` regardless of the requested URL or timeout."""
    if isinstance(body, str):
        body = body.encode("utf-8")

    def _fake(req, timeout=None):
        return _FakeResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", _fake)


def _stub_urlopen_raises(monkeypatch, exc):
    def _fake(req, timeout=None):
        raise exc

    monkeypatch.setattr(urllib.request, "urlopen", _fake)


def test_fetch_returns_every_model_name_from_well_formed_response(
    sync_catalog, monkeypatch,
):
    """Happy path: /api/tags returns the standard {"models": [{"name": ...}]}
    shape and the helper returns the names in order."""
    payload = {
        "models": [
            {"name": "qwen3.6:latest"},
            {"name": "qwen3.6:35b-a3b-coding-mxfp8"},
            {"name": "gemma4:31b"},
            {"name": "nomic-embed-text:latest"},
        ]
    }
    _stub_urlopen_returns(monkeypatch, json.dumps(payload))
    result = sync_catalog._fetch_ollama_tags("http://example.invalid:11434")
    assert result == [
        "qwen3.6:latest",
        "qwen3.6:35b-a3b-coding-mxfp8",
        "gemma4:31b",
        "nomic-embed-text:latest",
    ]


def test_fetch_handles_alternate_model_field(sync_catalog, monkeypatch):
    """Ollama versions have published both ``name`` and ``model`` for
    the same field. The helper accepts either."""
    payload = {
        "models": [
            {"model": "phi3:14b"},  # alternate key
            {"name": "qwen3.6:latest"},
        ]
    }
    _stub_urlopen_returns(monkeypatch, json.dumps(payload))
    result = sync_catalog._fetch_ollama_tags("http://example.invalid:11434")
    assert result == ["phi3:14b", "qwen3.6:latest"]


def test_fetch_returns_empty_list_on_empty_upstream(sync_catalog, monkeypatch):
    """Empty Ollama (no models pulled) ⇒ empty list, NOT an error."""
    _stub_urlopen_returns(monkeypatch, json.dumps({"models": []}))
    assert sync_catalog._fetch_ollama_tags("http://example.invalid:11434") == []


def test_fetch_treats_unreachable_upstream_as_empty_not_error(
    sync_catalog, monkeypatch, capsys,
):
    """Network failure path: the helper must return ``[]`` and log
    a warning — never raise. This keeps llm-catalog-init's startup
    flow robust when the operator's host Ollama isn't running yet."""
    _stub_urlopen_raises(
        monkeypatch, urllib.error.URLError("connection refused"),
    )
    result = sync_catalog._fetch_ollama_tags("http://example.invalid:11434")
    assert result == []
    captured = capsys.readouterr().out
    assert "/api/tags fetch" in captured, (
        "Failure must surface a warning so operators can debug; "
        f"got stdout: {captured!r}"
    )


def test_fetch_treats_malformed_json_as_empty_not_error(
    sync_catalog, monkeypatch, capsys,
):
    """If Ollama (or some HTTP middleman) returns non-JSON the helper
    degrades gracefully to ``[]`` with a warning."""
    _stub_urlopen_returns(monkeypatch, "<html>not json</html>")
    result = sync_catalog._fetch_ollama_tags("http://example.invalid:11434")
    assert result == []
    captured = capsys.readouterr().out
    assert "not valid JSON" in captured


def test_fetch_returns_empty_when_url_is_empty(sync_catalog):
    """Caller passes ``""`` when LITELLM_OLLAMA_UPSTREAM is unset (the
    LLM_PROVIDER_SOURCE=none path). Helper must short-circuit without
    even attempting an HTTP call."""
    assert sync_catalog._fetch_ollama_tags("") == []


def test_fetch_tolerates_models_list_with_garbage_entries(
    sync_catalog, monkeypatch,
):
    """If the upstream returns a malformed entry mid-list, the helper
    must skip it and keep the rest — not bail on the whole response."""
    payload = {
        "models": [
            {"name": "good-model:latest"},
            "not-a-dict",          # garbage
            {"name": ""},          # empty name
            {"unrelated": "key"},  # no name field
            {"name": "another-good:7b"},
        ]
    }
    _stub_urlopen_returns(monkeypatch, json.dumps(payload))
    result = sync_catalog._fetch_ollama_tags("http://example.invalid:11434")
    assert result == ["good-model:latest", "another-good:7b"]
