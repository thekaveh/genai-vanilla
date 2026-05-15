"""
Topology engine — single source of truth for service ordering, categorization,
port slot allocation, box rows, and alias list.

Replaces:
  * services/_order.yml (hand-edited)
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


def _build_from_manifests(manifests: list[Manifest], base_port: int) -> Topology:
    """Internal — splits manifest loading from computation for unit-test ergonomics."""
    raise NotImplementedError  # filled in by Tasks 2.2-2.5
