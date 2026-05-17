"""Manifest-graph resolver.

For a given focus service, walks every manifest under services/ and builds
a DepGraph describing:
  - upstream edges (services this one depends on, classified as required /
    adaptive / optional)
  - downstream edges (services that depend on this one)
  - bidirectional loops (A → B and B → A collapsed)
  - init containers (recorded but excluded from edges per spec A.3 rule #7)

The resolver is byte-deterministic for the same manifest state. It is the
sole input to deps_section_writer and diagram_renderer.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.manifests import Manifest, load_manifests  # noqa: E402


EdgeKind = Literal["required", "optional", "adaptive"]
EdgeDirection = Literal["upstream", "downstream"]


@dataclass(frozen=True, order=True)
class DepEdge:
    """One edge on the focus service's dependency graph.

    Ordered tuple-comparable so (kind, other) sorts stably across runs.

    `other_category` carries the OTHER service's category so the renderer
    can stroke each box with its own category color without reloading
    manifests.
    """

    other: str
    kind: EdgeKind
    direction: EdgeDirection
    mechanism: str = ""
    failure_mode: str | None = None
    bidirectional: bool = False
    other_category: str = "external"


@dataclass(frozen=True)
class DepGraph:
    focus: str
    category: str
    port_var: str | None
    source: str
    upstream: tuple[DepEdge, ...] = ()
    downstream: tuple[DepEdge, ...] = ()
    init_containers: tuple[str, ...] = ()


# ─────────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────────


def build_graph(focus: str, services_root: Path) -> DepGraph:
    """Build the DepGraph for a single service."""

    manifests_by_name = {m.name: m for m in load_manifests(services_root)}
    if focus not in manifests_by_name:
        raise KeyError(f"no manifest for service '{focus}' under {services_root}")

    me = manifests_by_name[focus]

    upstream: list[DepEdge] = []
    upstream.extend(_required_upstream(me, manifests_by_name))
    upstream.extend(_adaptive_upstream(me, manifests_by_name))
    upstream.extend(_optional_upstream(me, manifests_by_name))

    downstream: list[DepEdge] = []
    for other_name, other_m in manifests_by_name.items():
        if other_name == focus:
            continue
        # Inverse-pass: does `other_m` declare focus as a dep?
        downstream.extend(_inverse_required(focus, other_m, manifests_by_name))
        downstream.extend(_inverse_adaptive(focus, other_m, manifests_by_name))
        downstream.extend(_inverse_optional(focus, other_m, manifests_by_name))
        # Inverse extra_consumers: if `other` lists focus in its
        # doc_extras.diagram.extra_consumers, then `other` registers focus
        # as one of its consumers — from focus's POV that's a downstream
        # tie back to `other` (runtime registration / reverse wiring not
        # expressible via depends_on; e.g. litellm-init registering
        # hermes as the `hermes-agent` model).
        other_extras = other_m.doc_extras.get("diagram", {}).get("extra_consumers", [])
        if focus in other_extras:
            downstream.append(DepEdge(
                other=other_name,
                kind="optional",
                direction="downstream",
                mechanism=f"{other_name} registers {focus} as a consumer "
                          f"(doc_extras.diagram.extra_consumers escape hatch)",
                other_category=_cat(manifests_by_name, other_name),
            ))

    # doc_extras.diagram.extra_consumers — manual escape hatch (focus side)
    extras = me.doc_extras.get("diagram", {}).get("extra_consumers", [])
    for ex in extras:
        if ex in manifests_by_name and ex != focus:
            downstream.append(
                DepEdge(other=ex, kind="optional", direction="downstream",
                        mechanism="manual escape hatch (doc_extras.diagram.extra_consumers)",
                        other_category=_cat(manifests_by_name, ex))
            )

    # Bidirectional collapse
    upstream_names = {e.other for e in upstream}
    downstream_names = {e.other for e in downstream}
    both = upstream_names & downstream_names
    upstream = [
        DepEdge(**{**e.__dict__, "bidirectional": True}) if e.other in both else e
        for e in upstream
    ]
    downstream = [
        DepEdge(**{**e.__dict__, "bidirectional": True}) if e.other in both else e
        for e in downstream
    ]

    # Init containers: anything in containers that ends with "-init"
    init_containers = tuple(c for c in me.containers if c.endswith("-init"))

    # Identify the primary source variant for the focus box label
    source_label = me.sources.default if me.sources else "single"

    # Port (use the first port-bearing env var that exists)
    port_var = None
    for env in me.env:
        if env.name.endswith("_PORT") or env.name.endswith("_API_PORT"):
            port_var = env.name
            break

    return DepGraph(
        focus=focus,
        category=me.category,
        port_var=port_var,
        source=source_label,
        upstream=tuple(sorted(set(upstream), key=_edge_sort_key)),
        downstream=tuple(sorted(set(downstream), key=_edge_sort_key)),
        init_containers=init_containers,
    )


# Category ordering matches services.topology.CATEGORY_ORDER so lane sort
# is consistent with the wizard's grouping.
_CATEGORY_RANK = {"infra": 0, "data": 1, "llm": 2, "media": 3, "agents": 4, "apps": 5, "external": 6}


def _edge_sort_key(e: DepEdge) -> tuple[int, str]:
    """Stable sort within a tier (spec A.3 rule #5): by category, then alphabetically."""
    return (_CATEGORY_RANK.get(e.other_category, 99), e.other)


# ─────────────────────────────────────────────────────────────────────────
# Edge extraction helpers
# ─────────────────────────────────────────────────────────────────────────


def _cat(all_m: dict[str, Manifest], name: str) -> str:
    return all_m[name].category if name in all_m else "external"


def _required_upstream(me: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    edges: list[DepEdge] = []
    for dep in me.depends_on.required:
        if dep in all_m:
            edges.append(DepEdge(
                other=dep,
                kind="required",
                direction="upstream",
                mechanism=_extract_mechanism(me, dep, all_m),
                failure_mode=_extract_failure_mode(me, dep),
                other_category=_cat(all_m, dep),
            ))
    return edges


def _adaptive_upstream(me: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    edges: list[DepEdge] = []
    seen: set[str] = set()
    for container, block in (me.runtime_adaptive or {}).items():
        adapts_to = block.get("adapts_to", []) or []
        # Tolerate scalar string form (some manifests use `adapts_to: llm_provider`)
        if isinstance(adapts_to, str):
            adapts_to = [adapts_to]
        fm = block.get("failure_mode")
        for target in adapts_to:
            if target in seen:
                continue
            seen.add(target)
            edges.append(DepEdge(
                other=target,
                kind="adaptive",
                direction="upstream",
                mechanism=_extract_adaptive_mechanism(block, target),
                failure_mode=fm,
                other_category=_cat(all_m, target),
            ))
    return edges


def _optional_upstream(me: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    edges: list[DepEdge] = []
    for container, block in (me.runtime_deps or {}).items():
        for dep in block.get("optional", []) or []:
            if dep in all_m and dep != me.name:
                edges.append(DepEdge(
                    other=dep,
                    kind="optional",
                    direction="upstream",
                    mechanism="(optional — wired conditionally; see manifest)",
                    other_category=_cat(all_m, dep),
                ))
    return edges


def _inverse_required(focus: str, other: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    if focus in other.depends_on.required:
        return [DepEdge(other=other.name, kind="required", direction="downstream",
                        mechanism=f"{other.name} declares {focus} in depends_on.required",
                        other_category=_cat(all_m, other.name))]
    return []


def _inverse_adaptive(focus: str, other: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    for container, block in (other.runtime_adaptive or {}).items():
        adapts = block.get("adapts_to") or []
        if isinstance(adapts, str):
            adapts = [adapts]
        if focus in adapts:
            return [DepEdge(other=other.name, kind="adaptive", direction="downstream",
                            mechanism=f"{other.name} adapts_to {focus}",
                            other_category=_cat(all_m, other.name))]
    return []


def _inverse_optional(focus: str, other: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    for container, block in (other.runtime_deps or {}).items():
        if focus in (block.get("optional") or []):
            return [DepEdge(other=other.name, kind="optional", direction="downstream",
                            mechanism=f"{other.name} lists {focus} as optional dep",
                            other_category=_cat(all_m, other.name))]
    return []


def _extract_mechanism(me: Manifest, dep: str, all_m: dict[str, Manifest]) -> str:
    """Best-effort mechanism string from env defaults."""
    # First: look for <DEP>_LOCALHOST_URL or <DEP>_ENDPOINT in the focus manifest's env
    for env in me.env:
        if env.name.startswith(dep.upper()) and (
            env.name.endswith("_LOCALHOST_URL") or env.name.endswith("_ENDPOINT")
        ):
            return str(env.default) or f"http://{dep}:<port>"
    # Fallback: container DNS
    return f"http://{dep}:<port>"


def _extract_adaptive_mechanism(block: dict, target: str) -> str:
    env_adapt = block.get("environment_adaptation") or {}
    for k, v in env_adapt.items():
        if target.split("_")[0].lower() in k.lower():
            return f"{k}={v}"
    if env_adapt:
        return next(iter(f"{k}={v}" for k, v in env_adapt.items()))
    return f"(adaptive; see manifest's runtime_adaptive block)"


def _extract_failure_mode(me: Manifest, dep: str) -> str | None:
    """If the focus declares a runtime_adaptive block where this dep appears as
    a required upstream, surface the failure_mode. Otherwise None for now;
    Task 7 + Phase C will broaden coverage."""
    for container, block in (me.runtime_adaptive or {}).items():
        adapts_to = block.get("adapts_to") or []
        if isinstance(adapts_to, str):
            adapts_to = [adapts_to]
        if "llm_provider" in adapts_to and dep == "litellm":
            return block.get("failure_mode")
    return None
