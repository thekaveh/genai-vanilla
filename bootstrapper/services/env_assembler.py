"""
Assemble a `.env.example`-shaped text document from a list of service manifests.

The output is a pure function of the manifests (and an optional ordering). It
is deterministic — re-running with the same inputs produces byte-identical
output — so CI can diff against the committed `.env.example`.

Phase A scope: the assembler does NOT yet replace the existing
`.env.example`. It is a standalone library used by tests and (later)
`bootstrapper/tools/validate_fragments.py --check-env-example`. Wiring into
start.py happens in Phase D once all manifests exist.

Output shape (per service):

    # ──────────────────────────────────────────────────────────────────────
    # llm: Ollama (services/ollama/service.yml)
    # ──────────────────────────────────────────────────────────────────────
    # Source: ollama-container-cpu | ollama-container-gpu | ollama-localhost | ...
    LLM_PROVIDER_SOURCE=ollama-container-cpu

    # Image references
    LLM_PROVIDER_IMAGE=ollama/ollama:latest
    OLLAMA_PULL_IMAGE=alpine/curl:latest

    # External Ollama-compatible endpoint.
    LLM_PROVIDER_EXTERNAL_URL=

    # auto-managed (computed from LLM_PROVIDER_SOURCE)
    OLLAMA_SCALE=
    OLLAMA_ENDPOINT=
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable

from services.manifests import EnvVarDecl, Manifest
from services.topology import build_topology


_HEADER = """\
# ============================================================================
# GENERATED FILE — DO NOT EDIT BY HAND
#
# This .env.example is produced by bootstrapper/services/env_assembler.py
# from services/<name>/service.yml manifests. To change a default, edit the
# relevant manifest and re-run `./start.sh` (which regenerates this file)
# or `python -m services.env_assembler` for the regen-only path.
#
# Variables flagged `auto-managed` are computed at runtime by the bootstrapper
# from SOURCE values and are intentionally emitted without a default here.
# ============================================================================
"""


def assemble_env_example(
    manifests: Iterable[Manifest],
    order: list[str] | None = None,
    *,
    services_root: Path | None = None,
) -> str:
    """Render the manifests into .env.example-shaped text.

    Args:
        manifests: Loaded service manifests.
        order: Optional list of manifest names declaring display order.
            Manifests not mentioned are appended alphabetically after the
            ordered ones. If None, all manifests are sorted alphabetically.
        services_root: Path to the services/ directory used to build the
            Topology (for port_defaults). If None, resolved from this file's
            location (i.e. <repo_root>/services).
    """
    manifests = list(manifests)

    _services_root = services_root or (
        Path(__file__).resolve().parent.parent.parent / "services"
    )
    port_defaults: dict[str, int]
    try:
        _topology = build_topology(_services_root)
        port_defaults = dict(_topology.port_defaults)
    except (FileNotFoundError, NotADirectoryError):
        # Synthetic test trees with no services/ dir on disk — fall back
        # to manifest-declared defaults silently. This is the supported
        # "stand-alone library" path used by env_assembler unit tests.
        port_defaults = {}
    except Exception as exc:
        # Real services/ tree present but topology failed (e.g. cycle,
        # unknown category, slot overflow). Warn so the failure surfaces
        # in the test log and CI, then degrade gracefully to manifest
        # defaults. Re-raising would block the assembler entirely; we
        # prefer a noisy fallback over silent breakage.
        warnings.warn(
            f"build_topology failed; port defaults will be empty: {exc}",
            stacklevel=2,
        )
        port_defaults = {}

    ordered = _apply_order(manifests, order)

    parts: list[str] = [_HEADER]
    for m in ordered:
        parts.append(_render_manifest(m, port_defaults))
    return "\n".join(parts).rstrip() + "\n"


# ────────────────────────────────────────────────────────────────────────────
# Ordering
# ────────────────────────────────────────────────────────────────────────────


def _apply_order(manifests: list[Manifest], order: list[str] | None) -> list[Manifest]:
    by_name = {m.name: m for m in manifests}
    if order is None:
        return sorted(manifests, key=lambda m: m.name)

    ordered: list[Manifest] = []
    seen: set[str] = set()
    for name in order:
        if name in by_name and name not in seen:
            ordered.append(by_name[name])
            seen.add(name)
    # Append any manifests not mentioned in `order`, alphabetically.
    for m in sorted(manifests, key=lambda m: m.name):
        if m.name not in seen:
            ordered.append(m)
    return ordered


# ────────────────────────────────────────────────────────────────────────────
# Rendering
# ────────────────────────────────────────────────────────────────────────────


def _render_manifest(m: Manifest, port_defaults: dict[str, int]) -> str:
    lines: list[str] = []
    lines.append("# " + "─" * 74)
    lines.append(f"# {m.category}: {m.label}  (services/{m.name}/service.yml)")
    lines.append("# " + "─" * 74)

    # Source var, if any, goes first — it's the most prominent dial.
    if m.sources is not None:
        option_ids = " | ".join(opt.id for opt in m.sources.options)
        lines.append(f"# Source variant. Options: {option_ids}")
        lines.append(f"{m.sources.var}={m.sources.default}")
        lines.append("")

    # Image references, if any.
    if m.images:
        lines.append("# Image references")
        for img in m.images:
            if img.notes:
                lines.append(f"# {img.notes}")
            lines.append(f"{img.var}={img.default}")
        lines.append("")

    # env[] entries. Order preserved as written in the manifest, except the
    # SOURCE var (already emitted above) is skipped here to avoid duplication.
    source_var = m.sources.var if m.sources else None
    for entry in m.env:
        if entry.name == source_var:
            continue  # already emitted at the top of this block
        lines.append(_render_env_entry(entry, port_defaults))

    lines.append("")  # blank line between services
    return "\n".join(lines)


def _render_env_entry(entry: EnvVarDecl, port_defaults: dict[str, int]) -> str:
    """Render one env line plus any preceding comment line(s)."""
    out: list[str] = []
    if entry.description:
        for line in entry.description.rstrip().splitlines():
            out.append(f"# {line}")
    flags: list[str] = []
    if entry.auto_managed:
        flags.append("auto-managed")
    if entry.secret:
        flags.append("secret")
    if flags:
        out.append(f"# ({', '.join(flags)})")

    if entry.auto_managed:
        out.append(f"{entry.name}=")
    elif entry.secret:
        # Never echo a secret default into the example; user provides it.
        out.append(f"{entry.name}=")
    else:
        # Port vars: topology slot-allocator is the single source of truth.
        if entry.name in port_defaults:
            value: object = port_defaults[entry.name]
        else:
            value = entry.default
        out.append(f"{entry.name}={_format_default(value)}")
    return "\n".join(out)


def _format_default(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


if __name__ == "__main__":
    import sys

    from services.manifests import load_manifests

    project_root = Path(__file__).resolve().parent.parent.parent
    services_dir = project_root / "services"
    env_example_path = project_root / ".env.example"

    manifests = load_manifests(services_dir)
    output = assemble_env_example(manifests)
    env_example_path.write_text(output)
    print(f"Wrote {env_example_path} ({output.count(chr(10))} lines)", file=sys.stderr)
