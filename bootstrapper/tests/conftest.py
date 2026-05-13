"""
Shared pytest fixtures for bootstrapper tests.

A `manifest_factory` helper writes valid/invalid service.yml files into a tmp
directory mirroring the services/<name>/ shape. Tests use it to construct
arbitrary fixture trees on the fly without committing YAML files to the repo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def services_root(tmp_path: Path) -> Path:
    """An empty services/ root inside tmp_path."""
    root = tmp_path / "services"
    root.mkdir()
    return root


@pytest.fixture
def write_manifest(services_root: Path):
    """Factory: write a services/<name>/service.yml from a Python dict."""

    def _write(name: str, data: dict[str, Any], *, folder_name: str | None = None) -> Path:
        folder = services_root / (folder_name or name)
        folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / "service.yml"
        manifest_path.write_text(yaml.safe_dump(data, sort_keys=False))
        return manifest_path

    return _write


@pytest.fixture
def minimal_manifest_dict():
    """A minimal-but-valid manifest dict (used as a base in tests)."""

    def _make(name: str = "redis") -> dict[str, Any]:
        return {
            "name": name,
            "label": f"{name.capitalize()} service",
            "category": "data",
            "containers": [name],
            "env": [
                {"name": f"{name.upper()}_PORT", "default": 6379, "description": "Host port."},
            ],
        }

    return _make


@pytest.fixture
def full_manifest_dict():
    """A manifest exercising every optional field."""

    def _make(name: str = "ollama") -> dict[str, Any]:
        return {
            "name": name,
            "label": "Ollama (local LLM engine)",
            "category": "llm",
            "docs": f"docs/services/{name}.md",
            "containers": ["ollama", "ollama-pull"],
            "images": [
                {
                    "var": "LLM_PROVIDER_IMAGE",
                    "default": "ollama/ollama:latest",
                    "container": "ollama",
                    "notes": "Used for container-cpu and container-gpu sources.",
                },
                {
                    "var": "OLLAMA_PULL_IMAGE",
                    "default": "alpine/curl:latest",
                    "container": "ollama-pull",
                },
            ],
            "sources": {
                "var": "LLM_PROVIDER_SOURCE",
                "default": "ollama-container-cpu",
                "options": [
                    {
                        "id": "ollama-container-cpu",
                        "label": "Container (CPU)",
                        "effects": {
                            "OLLAMA_SCALE": 1,
                            "OLLAMA_ENDPOINT": "http://ollama:11434",
                        },
                    },
                    {
                        "id": "ollama-external",
                        "label": "External",
                        "requires": ["LLM_PROVIDER_EXTERNAL_URL"],
                        "effects": {
                            "OLLAMA_SCALE": 0,
                            "OLLAMA_ENDPOINT": "${LLM_PROVIDER_EXTERNAL_URL}",
                        },
                    },
                ],
            },
            "env": [
                {"name": "LLM_PROVIDER_SOURCE", "default": "ollama-container-cpu"},
                {"name": "LLM_PROVIDER_EXTERNAL_URL", "default": "", "description": "External URL."},
                {"name": "OLLAMA_SCALE", "auto_managed": True, "description": "Computed."},
                {"name": "OLLAMA_ENDPOINT", "auto_managed": True},
            ],
            "depends_on": {
                "required": [],
                "optional": [],
            },
            "exports": [
                {"name": "OLLAMA_ENDPOINT", "consumers": ["litellm", "weaviate"]},
            ],
        }

    return _make
