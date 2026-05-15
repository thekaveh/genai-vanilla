"""Topology engine unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_manifest(services_root: Path, name: str, body: str) -> None:
    (services_root / name).mkdir(parents=True, exist_ok=True)
    (services_root / name / "service.yml").write_text(body)


def test_topology_dataclass_shape():
    """Topology exposes canonical_order, category_of, port_defaults, rows, aliases."""
    from services.topology import Topology
    t = Topology(canonical_order=[], category_of={}, port_defaults={}, rows=[], aliases=[])
    assert t.canonical_order == []
    assert t.category_of == {}
    assert t.port_defaults == {}
    assert t.rows == []
    assert t.aliases == []
