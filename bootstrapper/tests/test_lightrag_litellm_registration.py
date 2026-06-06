"""Tests for lightrag_model_entry()."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_PY = REPO_ROOT / "services/litellm/init/scripts/init.py"


def _load_init_module():
    spec = importlib.util.spec_from_file_location("litellm_init", INIT_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["litellm_init"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_returns_none_when_disabled(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_SOURCE", "disabled")
    mod = _load_init_module()
    assert mod.lightrag_model_entry() is None


def test_returns_entry_when_enabled(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_SOURCE", "container")
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_API_KEY", "sk-lightrag-test")
    mod = _load_init_module()
    entry = mod.lightrag_model_entry()
    assert entry is not None
    assert entry["model_name"] == "lightrag"
    assert entry["litellm_params"]["api_base"] == "http://lightrag:9621/api"
    assert entry["litellm_params"]["api_key"] == "sk-lightrag-test"


def test_adapter_is_openai_not_ollama_chat(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_SOURCE", "container")
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_API_KEY", "sk-lightrag-test")
    mod = _load_init_module()
    entry = mod.lightrag_model_entry()
    assert entry["litellm_params"]["model"].startswith("openai/")
    assert "ollama_chat" not in entry["litellm_params"]["model"]
