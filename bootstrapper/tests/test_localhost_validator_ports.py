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


def test_hosts_presence_check_ignores_commented_and_hyphenated_lines(tmp_path):
    """Presence check: a commented-out `# 127.0.0.1 alias` must NOT count
    as present, and a user's `my-n8n.localhost` must not satisfy
    `n8n.localhost` (regressions from passes 29/30)."""
    from utils.hosts_manager import HostsManager

    hosts = tmp_path / "hosts"
    hosts.write_text(
        "# 127.0.0.1 n8n.localhost\n"
        "127.0.0.1 my-api.localhost\n"
        "127.0.0.1 chat.localhost extra.localhost\n",
        encoding="utf-8",
    )
    hm = HostsManager()
    hm.hosts_file_path = hosts
    missing = hm.check_missing_hosts()
    assert "n8n.localhost" in missing      # commented ⇒ missing
    assert "api.localhost" in missing      # my-api ≠ api
    assert "chat.localhost" not in missing # multi-host line counts


def test_hosts_removal_spares_commented_and_hyphenated_lines(tmp_path):
    """Removal must delete real stack entries while sparing commented-out
    lines and the user's own hyphenated lookalikes (mirrors the
    presence-check semantics)."""
    from utils.hosts_manager import HostsManager

    hosts = tmp_path / "hosts"
    hosts.write_text(
        "# GenAI Stack subdomains\n"
        "127.0.0.1 n8n.localhost\n"
        "# 127.0.0.1 chat.localhost\n"
        "127.0.0.1 my-n8n.localhost\n"
        "127.0.0.1 unrelated.example\n",
        encoding="utf-8",
    )
    hm = HostsManager()
    assert hm.remove_hosts_entries_silent(str(hosts)) is True
    text = hosts.read_text(encoding="utf-8")
    assert "127.0.0.1 n8n.localhost\n" not in text       # real entry removed
    assert "# 127.0.0.1 chat.localhost" in text          # comment spared
    assert "127.0.0.1 my-n8n.localhost" in text          # lookalike spared
    assert "unrelated.example" in text
