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


def test_canonical_order_groups_by_category():
    """Topo order is partitioned by category in fixed display order."""
    from services.topology import _canonical_order
    manifests = [
        _manifest("z-app", "apps"),
        _manifest("a-data", "data"),
        _manifest("k-llm", "llm"),
    ]
    topo = ["a-data", "k-llm", "z-app"]
    out = _canonical_order(manifests, topo)
    assert out == ["a-data", "k-llm", "z-app"]  # data → llm → apps


def test_canonical_order_apps_after_agents():
    """Apps category sorts AFTER agents (specs §display order)."""
    from services.topology import _canonical_order
    manifests = [
        _manifest("foo-app", "apps"),
        _manifest("bar-agent", "agents"),
    ]
    topo = ["bar-agent", "foo-app"]
    out = _canonical_order(manifests, topo)
    assert out == ["bar-agent", "foo-app"]


def test_build_topology_end_to_end(tmp_path):
    """A small two-manifest fixture builds a complete Topology."""
    services_root = tmp_path / "services"
    _write_manifest(services_root, "alpha-infra",
        "name: alpha-infra\n"
        "label: A\n"
        "category: infra\n"
        "env:\n"
        "  - name: ALPHA_PORT\n"
        "rows:\n"
        "  - display_name: Alpha\n"
        "    source_var: ALPHA_SOURCE\n"
        "    port_var: ALPHA_PORT\n"
        "    alias: alpha.localhost\n"
    )
    _write_manifest(services_root, "beta-data",
        "name: beta-data\n"
        "label: B\n"
        "category: data\n"
        "env:\n"
        "  - name: BETA_PORT\n"
        "depends_on:\n"
        "  required: [alpha-infra]\n"
        "  optional: []\n"
        "rows:\n"
        "  - display_name: Beta\n"
        "    source_var: BETA_SOURCE\n"
        "    port_var: BETA_PORT\n"
    )

    from services.topology import build_topology
    t = build_topology(services_root, base_port=63000)
    assert t.canonical_order == ["alpha-infra", "beta-data"]
    assert t.category_of["alpha-infra"] == "infra"
    assert t.category_of["beta-data"] == "data"
    assert t.port_defaults == {"ALPHA_PORT": 63000, "BETA_PORT": 63010}
    assert [r.display_name for r in t.rows] == ["Alpha", "Beta"]
    assert t.aliases == ["alpha.localhost"]
