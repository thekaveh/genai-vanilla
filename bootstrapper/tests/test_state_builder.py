"""Unit tests for ui.state_builder.resolve_port — focuses on the
localhost path which now reads PORT vars directly instead of regex-
extracting from a URL var (the URL vars are gone)."""

from __future__ import annotations

import pytest

from ui.state_builder import resolve_port


@pytest.mark.parametrize("display_name,source,port_env_var,port_value", [
    ("ComfyUI", "localhost", "COMFYUI_LOCALHOST_PORT", "9000"),
    ("Document Processor", "docling-localhost", "DOCLING_LOCALHOST_PORT", "63099"),
    ("LLM Engine", "ollama-localhost", "OLLAMA_LOCALHOST_PORT", "11500"),
])
def test_resolve_port_for_localhost_reads_port_var(
    display_name, source, port_env_var, port_value
):
    """For a localhost-source row, the displayed port is the value of
    the row's localhost_port_var in env (formatted as ``:<port>``)."""
    env = {port_env_var: port_value}
    result = resolve_port(display_name, source=source, port_var=None, env=env)
    assert result == f":{port_value}", (
        f"resolve_port should return :{port_value}; got {result!r}"
    )


def test_resolve_port_for_localhost_returns_none_when_var_unset():
    """An empty PORT var falls back to nothing — wizard's pending row
    state will surface the manifest default via .env.example backfill
    before the next read."""
    result = resolve_port("ComfyUI", source="localhost", port_var=None, env={})
    assert result is None


def test_resolve_port_for_disabled_returns_none():
    """Disabled rows show no port (existing baseline)."""
    assert resolve_port("ComfyUI", "disabled", None, {}) is None


def test_resolve_port_for_container_source_uses_port_var():
    """Container source falls through to the port_var path (no change
    from baseline behaviour)."""
    env = {"COMFYUI_PORT": "63010"}
    result = resolve_port("ComfyUI", source="container-cpu", port_var="COMFYUI_PORT", env=env)
    assert result == ":63010"
