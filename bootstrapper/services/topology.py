"""
Topology engine — single source of truth for service ordering, categorization,
port slot allocation, box rows, alias list, category labels, and category
colors.

Historical replacements (these modules no longer exist; topology.py is now
the canonical source):

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

import functools
from dataclasses import dataclass
from pathlib import Path

from services.manifests import Manifest, load_manifests


# Display order top-to-bottom. Apps last because Open WebUI consumes Hermes
# Agent as a model (Apps depend on Agents).
CATEGORY_ORDER: tuple[str, ...] = (
    "infra", "data", "llm", "media", "agents", "apps",
)


# Human-readable labels for each category slug. Single source of truth —
# legend widgets, README generator, dot generator, and the pre-launch
# Rich summary all consume this dict instead of redefining the mapping.
CATEGORY_LABELS: dict[str, str] = {
    "infra":  "Infrastructure",
    "data":   "Data",
    "llm":    "LLM Core",
    "media":  "Media",
    "agents": "Agents & Workflows",
    "apps":   "Apps & UIs",
}


# Canonical category color tokens. The Textual palette re-exports these
# as ``CAT_*`` named tokens (kept for ``style=P.CAT_INFRA`` syntax) and
# the architecture-diagram generator imports the dict directly.
# Pastel palette picked from Catppuccin Mocha and ordered so that each
# adjacent pair in CATEGORY_ORDER lands on near-complementary hues — the
# previous slate/sky/periwinkle/sage set was visually too clustered in
# the cool half of the wheel. Hue diffs between every adjacent pair here
# exceed 120°, which is what gives the bar its at-a-glance distinction.
CATEGORY_COLORS: dict[str, str] = {
    "infra":  "#f38ba8",  # red/rose
    "data":   "#a6e3a1",  # sage green
    "llm":    "#cba6f7",  # mauve / lavender
    "media":  "#f9e2af",  # cream yellow
    "agents": "#89b4fa",  # blue
    "apps":   "#fab387",  # peach
}


# Per-category port slot blocks (base_offset, block_size).
#
# Each category gets a contiguous range relative to BASE_PORT:
#   infra:  BASE_PORT + 0..9      (Kong: HTTP+HTTPS take slots 0-1; 8 free)
#   data:   BASE_PORT + 10..29    (Supabase 7 + MinIO 2 + Neo4j 2 + Redis 1 +
#                                  Weaviate 2 = 14; 6 free)
#   llm:    BASE_PORT + 30..39    (LiteLLM: 1; 9 free)
#   media:  BASE_PORT + 40..59    (ComfyUI/STT/TTS/Doc/Searx/Speaches/
#                                  Chatterbox; ~7; 13 free)
#   agents: BASE_PORT + 60..79    (Hermes 2 + n8n + OpenClaw 2 = 5; 15 free)
#   apps:   BASE_PORT + 80..99    (Backend + Open WebUI + JupyterHub + LDR = 4;
#                                  16 free)
#
# Reserve generously — adding a new service inside a category shifts
# everything after it in lex order, but only within that category block.
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
    port_var: str | None
    scale_var: str | None
    alias: str | None
    description: str
    localhost_endpoint_var: str | None
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
    """Top-level entry point — loads manifests then computes the topology.

    Prefer ``get_topology()`` for app code — it caches the result so the
    manifests are only read from disk once per process.
    """
    manifests = load_manifests(Path(services_root))
    return _build_from_manifests(manifests, base_port)


@functools.lru_cache(maxsize=8)
def _cached_topology(services_root_str: str, base_port: int) -> "Topology":
    return build_topology(Path(services_root_str), base_port=base_port)


def get_topology(
    services_root: Path | None = None, base_port: int = 63000
) -> "Topology":
    """Cached topology accessor — single canonical entry point for app code.

    Replaces the assortment of per-module caches (``_topology_singleton``,
    ``_topology_cache``, ``_aliases_cache``, per-call ``build_topology``
    invocations) with one process-wide LRU. Tests that mutate the on-disk
    services/ tree can clear the cache via ``invalidate_cache()``.

    Args:
        services_root: Path to ``services/``. Defaults to the repo's
            top-level ``services/`` resolved relative to this file.
        base_port: Anchor for the slot allocator. Almost always 63000.
    """
    if services_root is None:
        services_root = Path(__file__).resolve().parent.parent.parent / "services"
    return _cached_topology(str(Path(services_root).resolve()), base_port)


def invalidate_cache() -> None:
    """Test hook — clear the topology LRU. Call after mutating manifests."""
    _cached_topology.cache_clear()


def validate_acyclic(manifests: list[Manifest]) -> None:
    """Public wrapper around the topo-sort cycle check.

    Raises ``TopologyError`` if the combined depends_on graph has a cycle.
    ``manifest_validator`` calls this; the underlying ``_topo_sort`` stays
    private.
    """
    _topo_sort(manifests)


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

    Raises ``TopologyError`` for any manifest whose category is not in
    ``CATEGORY_ORDER`` — silent exclusion would let an unknown-category
    manifest disappear from every downstream consumer.
    """
    category_of = {m.name: m.category for m in manifests}
    unknown = [
        name for name, cat in category_of.items() if cat not in CATEGORY_ORDER
    ]
    if unknown:
        raise TopologyError(
            f"unknown category for manifest(s): {sorted(unknown)}. "
            f"Valid categories: {list(CATEGORY_ORDER)}."
        )
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
            if env.name == "BASE_PORT":
                # BASE_PORT is the allocator's anchor, not an allocatable slot.
                # If it slipped into a manifest's env list, skip it so the
                # category's first real port (e.g. KONG_HTTP_PORT) lands at
                # slot 0 of the infra block.
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
