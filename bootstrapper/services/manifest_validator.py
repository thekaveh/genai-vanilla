"""
Cross-manifest validator.

Per-file/per-manifest checks live in services.manifests (loader). This module
runs the checks that need to see ALL manifests together — global uniqueness,
dependency closure, the source/export/effect declaration contract.

Phase A scope: validations that need only the manifest set. Validations that
need the compose.yml fragments (volume namespacing, depends_on closure across
container graph, healthcheck rule, env-example freshness vs. assembled
.env.example) will land alongside the fragments themselves in later phases.

Design notes:
- Functions return a list of ValidationIssue records rather than raising.
  Callers (CI lint, start.py) decide whether to abort.
- Issues are sorted (kind, manifest, message) for deterministic test output.
- Every issue carries the offending manifest name so users can locate it fast.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from services.manifests import Manifest


# ────────────────────────────────────────────────────────────────────────────
# Public result type
# ────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationIssue:
    """A single cross-manifest validation failure."""

    kind: str
    manifest: str
    message: str

    # `kind` values currently in use (kept here for grep-ability):
    #   duplicate_env_var          — same env var declared by ≥2 manifests
    #   duplicate_container        — same container name in ≥2 manifests
    #   unknown_dependency         — depends_on.required/optional → unknown manifest
    #   undeclared_export          — exports[].name not in env[] and not produced by runtime_sc environment
    #   undeclared_source_var      — sources.var not declared in env[]
    #   unknown_consumer           — exports[].consumers entry → unknown manifest
    #   fragment_container_drift   — manifest containers[] ≠ compose.yml services keys
    #   missing_fragment           — non-virtual manifest has no compose.yml
    #   unexpected_fragment        — virtual: true manifest has a compose.yml
    #   undeclared_tier_member     — runtime_dependency_tiers entry not a known container


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────


def validate_manifests(
    manifests: Iterable[Manifest],
    services_root: Path | None = None,
) -> list[ValidationIssue]:
    """Run every cross-manifest check and return the aggregated issue list.

    Args:
        manifests: The manifest set under test.
        services_root: Optional path to the services/ tree. When provided, the
            validator also reads each manifest's sibling compose.yml and runs
            fragment-level cross-checks (containers[] ↔ services keys 1:1,
            missing/unexpected fragment file). When None, only manifest-only
            checks run — used by unit tests that build manifest objects in
            memory without on-disk fragments.
    """
    manifests = list(manifests)
    issues: list[ValidationIssue] = []

    issues.extend(_check_unique_env_vars(manifests))
    issues.extend(_check_unique_containers(manifests))
    issues.extend(_check_dependency_closure(manifests))
    issues.extend(_check_export_consumer_closure(manifests))
    issues.extend(_check_per_manifest_contract(manifests))
    issues.extend(_check_tier_members(manifests))
    if services_root is not None:
        issues.extend(_check_fragment_containers(manifests, services_root))

    issues.sort(key=lambda i: (i.kind, i.manifest, i.message))
    return issues


# ────────────────────────────────────────────────────────────────────────────
# Individual rules
# ────────────────────────────────────────────────────────────────────────────


def _check_unique_env_vars(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Every env-var name must have exactly one owning manifest."""
    owners: dict[str, list[str]] = {}
    for m in manifests:
        for entry in m.env:
            owners.setdefault(entry.name, []).append(m.name)

    issues: list[ValidationIssue] = []
    for var, names in owners.items():
        if len(names) > 1:
            sorted_names = sorted(names)
            for name in sorted_names:
                issues.append(
                    ValidationIssue(
                        kind="duplicate_env_var",
                        manifest=name,
                        message=(
                            f"env var '{var}' is declared by multiple manifests: "
                            f"{sorted_names}. Each variable must have exactly one owner."
                        ),
                    )
                )
    return issues


def _check_unique_containers(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Every container name must appear in exactly one manifest."""
    owners: dict[str, list[str]] = {}
    for m in manifests:
        for c in m.containers:
            owners.setdefault(c, []).append(m.name)

    issues: list[ValidationIssue] = []
    for container, names in owners.items():
        if len(names) > 1:
            sorted_names = sorted(names)
            for name in sorted_names:
                issues.append(
                    ValidationIssue(
                        kind="duplicate_container",
                        manifest=name,
                        message=(
                            f"container '{container}' is claimed by multiple manifests: "
                            f"{sorted_names}."
                        ),
                    )
                )
    return issues


def _check_dependency_closure(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Every depends_on entry must reference an existing manifest."""
    known = {m.name for m in manifests}
    issues: list[ValidationIssue] = []
    for m in manifests:
        for dep in m.depends_on.required:
            if dep not in known:
                issues.append(
                    ValidationIssue(
                        kind="unknown_dependency",
                        manifest=m.name,
                        message=f"depends_on.required references unknown manifest '{dep}'",
                    )
                )
        for dep in m.depends_on.optional:
            if dep not in known:
                issues.append(
                    ValidationIssue(
                        kind="unknown_dependency",
                        manifest=m.name,
                        message=f"depends_on.optional references unknown manifest '{dep}'",
                    )
                )
    return issues


def _check_export_consumer_closure(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Every exports[].consumers entry must name a known manifest."""
    known = {m.name for m in manifests}
    issues: list[ValidationIssue] = []
    for m in manifests:
        for exp in m.exports:
            for consumer in exp.consumers:
                if consumer not in known:
                    issues.append(
                        ValidationIssue(
                            kind="unknown_consumer",
                            manifest=m.name,
                            message=(
                                f"exports[].name='{exp.name}' lists unknown consumer "
                                f"'{consumer}'"
                            ),
                        )
                    )
    return issues


def _check_tier_members(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Every name in runtime_dependency_tiers must be a declared container.

    Globals owns `runtime_dependency_tiers:` (data_tier, init_tier, core_services,
    app_tier). Each entry there must match some manifest's containers[] — otherwise
    the dependency manager will silently skip a dangling tier member (which was
    the actual XTTS retirement bug post-Tier-3 move).
    """
    known_containers: set[str] = set()
    for m in manifests:
        known_containers.update(m.containers)

    issues: list[ValidationIssue] = []
    for m in manifests:
        if not m.runtime_dependency_tiers:
            continue
        for tier_name, members in m.runtime_dependency_tiers.items():
            if not isinstance(members, list):
                continue
            for member in members:
                if member not in known_containers:
                    issues.append(
                        ValidationIssue(
                            kind="undeclared_tier_member",
                            manifest=m.name,
                            message=(
                                f"runtime_dependency_tiers.{tier_name} entry "
                                f"'{member}' is not a container declared by any "
                                f"manifest's containers[]."
                            ),
                        )
                    )
    return issues


def _check_fragment_containers(
    manifests: list[Manifest], services_root: Path
) -> list[ValidationIssue]:
    """Each non-virtual manifest's containers[] must equal its compose.yml's
    services keys 1:1 (no extras either way).

    Virtual manifests (cloud-providers, globals) MUST NOT have a compose.yml.
    """
    issues: list[ValidationIssue] = []
    for m in manifests:
        fragment_path = services_root / m.name / "compose.yml"

        if m.virtual:
            if fragment_path.is_file():
                issues.append(
                    ValidationIssue(
                        kind="unexpected_fragment",
                        manifest=m.name,
                        message=(
                            f"virtual: true manifest has a sibling compose.yml at "
                            f"{fragment_path}. Virtual manifests MUST NOT ship a "
                            f"Compose fragment."
                        ),
                    )
                )
            continue

        if not fragment_path.is_file():
            issues.append(
                ValidationIssue(
                    kind="missing_fragment",
                    manifest=m.name,
                    message=(
                        f"non-virtual manifest has no compose.yml at {fragment_path}."
                    ),
                )
            )
            continue

        try:
            fragment = yaml.safe_load(fragment_path.read_text()) or {}
        except yaml.YAMLError as e:
            issues.append(
                ValidationIssue(
                    kind="fragment_container_drift",
                    manifest=m.name,
                    message=f"compose.yml could not be parsed: {e}",
                )
            )
            continue

        fragment_services = list((fragment.get("services") or {}).keys())
        manifest_containers = list(m.containers)

        extra_in_manifest = sorted(set(manifest_containers) - set(fragment_services))
        extra_in_fragment = sorted(set(fragment_services) - set(manifest_containers))

        if extra_in_manifest:
            issues.append(
                ValidationIssue(
                    kind="fragment_container_drift",
                    manifest=m.name,
                    message=(
                        f"manifest containers[] lists {extra_in_manifest!r} but "
                        f"compose.yml has no matching `services:` entry."
                    ),
                )
            )
        if extra_in_fragment:
            issues.append(
                ValidationIssue(
                    kind="fragment_container_drift",
                    manifest=m.name,
                    message=(
                        f"compose.yml `services:` keys include {extra_in_fragment!r} "
                        f"that the manifest's containers[] does not declare."
                    ),
                )
            )
    return issues


def _check_per_manifest_contract(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Within a single manifest, sources/exports must reference declared env vars."""
    issues: list[ValidationIssue] = []
    for m in manifests:
        declared_env = {e.name for e in m.env}

        # 1. Source var declared as env
        if m.sources is not None and m.sources.var not in declared_env:
            issues.append(
                ValidationIssue(
                    kind="undeclared_source_var",
                    manifest=m.name,
                    message=(
                        f"sources.var='{m.sources.var}' must also appear as an entry in env[]"
                    ),
                )
            )

        # 2. Every runtime_sc.<key>.<source>.environment key must be declared
        # in this manifest's env[] OR in some other manifest's env[]. The
        # latter is OK because runtime values cross service boundaries
        # (e.g. ollama's runtime_sc writes LITELLM_OLLAMA_UPSTREAM, which is
        # owned by litellm's manifest). This rule catches typo'd env vars.
        # Note: collected across ALL manifests, so cross-manifest writes are
        # allowed as long as some manifest declares the var.

        # 3. Every export name must be either a declared env var OR produced
        # by this manifest's runtime_sc.
        produced_by_runtime: set[str] = set()
        for sc_block in m.runtime_sc.values():
            if not isinstance(sc_block, dict):
                continue
            for source_block in sc_block.values():
                if not isinstance(source_block, dict):
                    continue
                env_block = source_block.get("environment") or {}
                if isinstance(env_block, dict):
                    produced_by_runtime.update(env_block.keys())
        producible = declared_env | produced_by_runtime
        for exp in m.exports:
            if exp.name not in producible:
                issues.append(
                    ValidationIssue(
                        kind="undeclared_export",
                        manifest=m.name,
                        message=(
                            f"exports[].name='{exp.name}' is not declared in this manifest's "
                            f"env[] and is not produced by any runtime_sc environment"
                        ),
                    )
                )

    return issues
