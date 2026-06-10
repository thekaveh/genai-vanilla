"""LocalhostValidator port handling: env-string ports and blank values.

Regression guards: the *_LOCALHOST_PORT conversion fed a STRING port into
socket.connect_ex (TypeError swallowed → Neo4j probe always failed even
with a live listener), and dict.get's default never fires for
present-but-blank values.
"""
from __future__ import annotations

import socket

from core.config_parser import ConfigParser
from utils.localhost_validator import LocalhostValidator


def _validator(tmp_path, env_text: str) -> LocalhostValidator:
    env = tmp_path / ".env"
    env.write_text(env_text, encoding="utf-8")
    cp = ConfigParser(str(tmp_path))
    cp.env_file_path = env
    # Point at the real repo root for manifest loads if needed; the
    # validator only parses env for these paths.
    return LocalhostValidator(config_parser=cp)


def test_tcp_probe_succeeds_with_string_port_from_env(tmp_path):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        v = _validator(tmp_path, f"NEO4J_LOCALHOST_BOLT_PORT={port}\n")
        accessible, messages = v.validate_service(
            "NEO4J_GRAPH_DB_SOURCE", "localhost"
        )
        assert accessible is True, messages
    finally:
        server.close()


def test_tcp_probe_blank_port_falls_back_to_default(tmp_path):
    """Blank var must fall back to the default port (and not crash);
    nothing listens there in the test env, so the probe reports
    not-accessible with the DEFAULT port in the message."""
    v = _validator(tmp_path, "NEO4J_LOCALHOST_BOLT_PORT=\n")
    accessible, messages = v.validate_service(
        "NEO4J_GRAPH_DB_SOURCE", "localhost"
    )
    joined = "\n".join(messages)
    assert "7687" in joined, joined


def test_http_probe_blank_port_falls_back_to_default(tmp_path):
    v = _validator(tmp_path, "COMFYUI_LOCALHOST_PORT=\n")
    accessible, messages = v.validate_service("COMFYUI_SOURCE", "localhost")
    joined = "\n".join(messages)
    assert "localhost:8000" in joined
    assert "localhost:/" not in joined
