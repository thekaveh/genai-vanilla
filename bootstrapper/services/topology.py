"""
Topology engine — single source of truth for service ordering, categorization,
port slot allocation, box rows, and alias list.

Replaces:
  * bootstrapper/ui/state_builder.py::_SERVICES
  * bootstrapper/ui/state_builder.py::_HOST_ALIAS
  * bootstrapper/wizard/service_discovery.py::DISPLAY_NAME_OVERRIDES
  * bootstrapper/wizard/service_discovery.py::SERVICE_DESCRIPTIONS
  * bootstrapper/wizard/service_discovery.py::LOCKED_SERVICES
  * bootstrapper/utils/endpoint_vars.py::LOCALHOST_ENDPOINT_VARS
  * bootstrapper/utils/hosts_manager.py::HostsManager.GENAI_HOSTS

Every downstream consumer imports Topology from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from services.manifests import Manifest, load_manifests


# Display order top-to-bottom. Apps last because Open WebUI consumes Hermes
# Agent as a model (Apps depend on Agents).
CATEGORY_ORDER: tuple[str, ...] = (
    "infra", "data", "llm", "media", "agents", "apps",
)


# Slot allocator: per-category port block. (base_offset, block_size).
# Block sizes give ~2x headroom over today's ~33 used slots.
CATEGORY_SLOTS: dict[str, tuple[int, int]] = {
    "infra":  (0,  10),
    "data":   (10, 20),
    "llm":    (30, 10),
    "media":  (40, 20),
    "agents": (60, 20),
    "apps":   (80, 20),
}


@dataclass(frozen=True)
class Row:
    """A single box row. Resolved from a manifest's rows[] entry plus category metadata."""

    manifest: str
    display_name: str
    source_var: str
    port_var: Optional[str]
    scale_var: Optional[str]
    alias: Optional[str]
    description: str
    localhost_endpoint_var: Optional[str]
    category: str
    locked: bool


@dataclass(frozen=True)
class Topology:
    """The single object consumed by every downstream module."""

    canonical_order: list[str]
    category_of: dict[str, str]
    port_defaults: dict[str, int]
    rows: list[Row]
    aliases: list[str]


class TopologyError(Exception):
    """Topology cannot be computed (cycle, unknown dep, overflow)."""


def build_topology(services_root: Path, base_port: int = 63000) -> Topology:
    """Top-level entry point — loads manifests then computes the topology."""
    manifests = load_manifests(Path(services_root))
    return _build_from_manifests(manifests, base_port)


def _topo_sort(manifests: list[Manifest]) -> list[str]:
    """Kahn's algorithm with lexicographic tiebreaker.

    Returns manifest names in topological order. Manifests with no deps sort
    alphabetically among themselves; same for any other tier of equal rank.
    """
    from collections import defaultdict
    import heapq

    names = {m.name for m in manifests}
    in_degree: dict[str, int] = {m.name: 0 for m in manifests}
    forward: dict[str, list[str]] = defaultdict(list)

    for m in manifests:
        for dep in m.depends_on.required:
            if dep in names:
                forward[dep].append(m.name)
                in_degree[m.name] += 1

    ready: list[str] = [n for n, d in in_degree.items() if d == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        n = heapq.heappop(ready)
        order.append(n)
        for child in forward[n]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                heapq.heappush(ready, child)

    if len(order) != len(manifests):
        unresolved = sorted(n for n, d in in_degree.items() if d > 0)
        raise TopologyError(
            f"dependency cycle among: {unresolved}. "
            f"Each remaining manifest has at least one inbound dep that was "
            f"never resolved — pick any to start tracing."
        )
    return order


def _canonical_order(manifests: list[Manifest], topo: list[str]) -> list[str]:
    """Partition the topo order by category, concatenate in CATEGORY_ORDER.

    Within a category, manifests stay in their topo-derived order. Between
    categories, the global category sequence wins (infra → data → llm → media
    → agents → apps).
    """
    category_of = {m.name: m.category for m in manifests}
    buckets: dict[str, list[str]] = {c: [] for c in CATEGORY_ORDER}
    for name in topo:
        cat = category_of.get(name)
        if cat in buckets:
            buckets[cat].append(name)
    result: list[str] = []
    for cat in CATEGORY_ORDER:
        result.extend(buckets[cat])
    return result


def _allocate_slots(
    manifests: list[Manifest],
    canonical: list[str],
    base_port: int,
) -> dict[str, int]:
    """Assign port_var → default port for every *_PORT env var declared.

    Each category has a block (base_offset, block_size). For each manifest in
    canonical order, every env var ending in `_PORT` consumes the next slot in
    its category's block. Multi-port manifests get a contiguous run.
    """
    by_name = {m.name: m for m in manifests}
    next_slot: dict[str, int] = {c: base_offset for c, (base_offset, _) in CATEGORY_SLOTS.items()}
    defaults: dict[str, int] = {}

    for name in canonical:
        m = by_name[name]
        cat = m.category
        if cat not in CATEGORY_SLOTS:
            continue
        base_offset, block_size = CATEGORY_SLOTS[cat]
        block_end = base_offset + block_size
        for env in m.env:
            if not env.name.endswith("_PORT"):
                continue
            if next_slot[cat] >= block_end:
                raise TopologyError(
                    f"{cat} block full (size {block_size}); cannot allocate "
                    f"{env.name} for manifest {m.name}. Increase block size in "
                    f"CATEGORY_SLOTS or move some manifests to a different category."
                )
            defaults[env.name] = base_port + next_slot[cat]
            next_slot[cat] += 1

    return defaults


def _build_from_manifests(manifests: list[Manifest], base_port: int) -> Topology:
    """Internal — splits manifest loading from computation for unit-test ergonomics."""
    topo = _topo_sort(manifests)
    canonical = _canonical_order(manifests, topo)
    port_defaults = _allocate_slots(manifests, canonical, base_port)

    by_name = {m.name: m for m in manifests}
    locked_by_name = {m.name: _is_locked(m) for m in manifests}

    rows: list[Row] = []
    aliases: list[str] = []
    for name in canonical:
        m = by_name[name]
        for r in m.rows:
            rows.append(Row(
                manifest=m.name,
                display_name=r.display_name,
                source_var=r.source_var,
                port_var=r.port_var or None,
                scale_var=r.scale_var or None,
                alias=r.alias or None,
                description=r.description,
                localhost_endpoint_var=r.localhost_endpoint_var or None,
                category=m.category,
                locked=locked_by_name[m.name],
            ))
            if r.alias:
                aliases.append(r.alias)

    return Topology(
        canonical_order=canonical,
        category_of={m.name: m.category for m in manifests},
        port_defaults=port_defaults,
        rows=rows,
        aliases=aliases,
    )


def _is_locked(m: Manifest) -> bool:
    """A manifest is locked when there is no source choice for the user.

    Locked = sources block absent OR sources.options has only one entry.
    """
    if m.sources is None:
        return True
    return len(m.sources.options) <= 1
