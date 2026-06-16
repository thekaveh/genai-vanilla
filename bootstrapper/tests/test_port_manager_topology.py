"""Regression tests for PortManager — must derive its mapping from the
live topology, never a hard-coded snapshot.

Background: PortManager used to carry a frozen PORT_MAPPING dict whose
offsets shadowed the manifest-driven Topology.port_defaults. When the
topology rework moved Hermes / Agents into a 60-block, that map went
stale and ``update_env_ports(default_base)`` started clobbering the
just-migrated .env on every run. These tests pin the contract that
PortManager NEVER rewrites a port to a value that disagrees with
``Topology.port_defaults``.
"""

from __future__ import annotations

from pathlib import Path
import os

import pytest


def _real_root() -> Path:
    """Repo root (parent of bootstrapper/)."""
    return Path(__file__).resolve().parent.parent.parent


def test_port_offsets_match_topology(monkeypatch):
    """PortManager.port_offsets() == Topology.port_defaults shifted to
    DEFAULT_BASE_PORT. Pinned so a future hardcoded fallback can't
    silently re-introduce drift."""
    from core.port_manager import PortManager
    from core.config_parser import DEFAULT_BASE_PORT
    from services.topology import build_topology

    pm = PortManager(str(_real_root()))
    offsets = pm.port_offsets()
    topology = build_topology(_real_root() / "services", base_port=DEFAULT_BASE_PORT)
    assert offsets == {
        var: port - DEFAULT_BASE_PORT for var, port in topology.port_defaults.items()
    }


def test_handle_port_configuration_with_default_base_does_not_clobber_topology(
    tmp_path, monkeypatch,
):
    """C1 regression: calling ``update_env_ports(DEFAULT_BASE_PORT)`` on
    a .env whose port values already match ``topology.port_defaults``
    must leave the file byte-identical. Otherwise the v0→v1 migration
    is undone immediately by the very next pipeline step.
    """
    from core.port_manager import PortManager
    from core.config_parser import DEFAULT_BASE_PORT
    from services.topology import build_topology

    real_root = _real_root()
    topology = build_topology(real_root / "services", base_port=DEFAULT_BASE_PORT)

    # Build a fixture .env at exactly the topology defaults — plus the
    # BASE_PORT line plus an unrelated key — so update_env_ports has
    # something to compare against.
    env_lines = [f"BASE_PORT={DEFAULT_BASE_PORT}\n", "UNRELATED_KEY=hello\n"]
    for var, port in topology.port_defaults.items():
        env_lines.append(f"{var}={port}\n")
    fixture_env = tmp_path / ".env"
    fixture_env.write_text("".join(env_lines))
    original = fixture_env.read_text()

    monkeypatch.setenv("ATLAS_ENV_FILE", str(fixture_env))
    pm = PortManager(str(real_root))
    assert pm.update_env_ports(DEFAULT_BASE_PORT, create_backup=False) is True
    assert fixture_env.read_text() == original


def test_update_env_ports_preserves_inline_comments(tmp_path, monkeypatch):
    """``LITELLM_PORT=63030  # label`` must keep its trailing label
    even when the port itself stays unchanged (the regex must not eat
    the comment tail)."""
    from core.port_manager import PortManager
    from core.config_parser import DEFAULT_BASE_PORT
    from services.topology import build_topology

    real_root = _real_root()
    topology = build_topology(real_root / "services", base_port=DEFAULT_BASE_PORT)
    litellm = topology.port_defaults["LITELLM_PORT"]

    fixture_env = tmp_path / ".env"
    fixture_env.write_text(
        f"BASE_PORT={DEFAULT_BASE_PORT}\n"
        f"LITELLM_PORT={litellm}  # custom label\n"
    )
    monkeypatch.setenv("ATLAS_ENV_FILE", str(fixture_env))
    pm = PortManager(str(real_root))
    assert pm.update_env_ports(DEFAULT_BASE_PORT, create_backup=False) is True
    assert "LITELLM_PORT" in fixture_env.read_text()
    assert "# custom label" in fixture_env.read_text()


def test_validate_base_port_uses_topology_max_offset():
    """``validate_base_port`` clamps against the largest topology slot,
    not a stale hardcoded offset (was 48 = JUPYTERHUB_PORT in v0)."""
    from core.port_manager import PortManager
    from services.topology import build_topology
    from core.config_parser import DEFAULT_BASE_PORT

    real_root = _real_root()
    topology = build_topology(real_root / "services", base_port=DEFAULT_BASE_PORT)
    max_offset = max(p - DEFAULT_BASE_PORT for p in topology.port_defaults.values())
    pm = PortManager(str(real_root))
    assert pm.validate_base_port(65535 - max_offset) is True
    assert pm.validate_base_port(65535 - max_offset + 1) is False
def test_update_env_ports_rewrites_trailing_whitespace_lines(tmp_path, monkeypatch):
    """``VAR=63002␣`` (trailing space, no comment) must still be
    rewritten — the pre-fix regex required a `#` after the spaces and
    silently no-oped on such lines."""
    from core.port_manager import PortManager
    from core.config_parser import DEFAULT_BASE_PORT
    from services.topology import build_topology

    real_root = _real_root()
    new_base = DEFAULT_BASE_PORT + 1000
    topology = build_topology(real_root / "services", base_port=new_base)
    var, want = next(iter(topology.port_defaults.items()))

    fixture_env = tmp_path / ".env"
    fixture_env.write_text(
        f"BASE_PORT={DEFAULT_BASE_PORT}\n{var}=12345 \n"
    )
    monkeypatch.setenv("ATLAS_ENV_FILE", str(fixture_env))
    pm = PortManager(str(real_root))
    assert pm.update_env_ports(new_base, create_backup=False) is True
    assert f"{var}={want}" in fixture_env.read_text()
