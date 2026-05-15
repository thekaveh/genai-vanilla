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


from services.manifests import Manifest, DependsOn, Row as ManifestRow


def _manifest(name, category, requires=None, rows=None):
    """Helper: build a minimal Manifest for unit tests."""
    return Manifest(
        name=name,
        label=name,
        category=category,
        env=[],
        depends_on=DependsOn(required=list(requires or []), optional=[]),
        rows=list(rows or []),
    )


def test_topo_sort_lex_tiebreaker():
    """Equal-rank manifests sort alphabetically."""
    from services.topology import _topo_sort
    manifests = [
        _manifest("zulu", "data"),
        _manifest("alpha", "data"),
        _manifest("mike", "data"),
    ]
    order = _topo_sort(manifests)
    assert order == ["alpha", "mike", "zulu"]


def test_topo_sort_respects_deps():
    """A depends_on B means B comes first."""
    from services.topology import _topo_sort
    manifests = [
        _manifest("alpha", "data", requires=["zulu"]),
        _manifest("zulu", "data"),
    ]
    order = _topo_sort(manifests)
    assert order == ["zulu", "alpha"]


def test_topo_sort_cycle_raises():
    """Cycle in deps triggers TopologyError with cycle path."""
    from services.topology import _topo_sort, TopologyError
    manifests = [
        _manifest("a", "data", requires=["b"]),
        _manifest("b", "data", requires=["a"]),
    ]
    with pytest.raises(TopologyError, match="cycle"):
        _topo_sort(manifests)
