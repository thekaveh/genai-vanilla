"""Guard against nested file/dir bind-mounts into a read-only parent mount.

Regression test for the litellm-init mount bug: mounting a file at
``/catalog/ollama-models.yaml`` while ``/catalog`` is itself a ``:ro`` bind
mount makes runc fail at container init ("make mountpoint ... read-only file
system") on Docker 29.x / macOS, aborting ``docker compose up``.

The invariant: within a single compose service, no volume target may be nested
under another volume target that is mounted read-only. (A writable parent is
fine — the runtime can create the mountpoint; a fresh, non-bind-mounted parent
dir is also fine.)
"""
from __future__ import annotations

import pathlib

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
COMPOSE_FILES = sorted((REPO_ROOT / "services").glob("*/compose.yml"))

# Compose short-volume mode tokens that mean "read-only".
_RO_TOKENS = {"ro"}


def _parse_short_volume(vol: str) -> tuple[str, bool] | None:
    """Return (container_target, is_read_only) for a short-form volume string.

    Handles ``SOURCE:TARGET[:MODE]``. The target is the first ``/``-rooted
    segment after the source. Returns None when no absolute target is found
    (e.g. env-substituted or malformed entries we don't reason about).
    """
    parts = vol.split(":")
    # Find the container target: the first segment (index >= 1) starting with "/".
    target_idx = next(
        (i for i in range(1, len(parts)) if parts[i].startswith("/")), None
    )
    if target_idx is None:
        return None
    target = parts[target_idx].rstrip("/") or "/"
    mode_tokens = set()
    for seg in parts[target_idx + 1:]:
        mode_tokens.update(seg.split(","))
    return target, bool(_RO_TOKENS & mode_tokens)


def _service_volume_targets(service: dict) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for vol in service.get("volumes", []) or []:
        if isinstance(vol, str):
            parsed = _parse_short_volume(vol)
            if parsed:
                out.append(parsed)
        elif isinstance(vol, dict):  # long form
            target = vol.get("target")
            if isinstance(target, str) and target.startswith("/"):
                out.append((target.rstrip("/") or "/", bool(vol.get("read_only"))))
    return out


@pytest.mark.parametrize("compose_path", COMPOSE_FILES, ids=lambda p: p.parent.name)
def test_no_mount_nested_under_readonly_parent(compose_path):
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    services = data.get("services", {}) or {}
    violations: list[str] = []
    for svc_name, svc in services.items():
        targets = _service_volume_targets(svc)
        for parent, parent_ro in targets:
            if not parent_ro:
                continue
            for child, _ in targets:
                if child != parent and child.startswith(parent + "/"):
                    violations.append(
                        f"{compose_path.relative_to(REPO_ROOT)} :: service '{svc_name}': "
                        f"'{child}' is mounted INSIDE read-only mount '{parent}' — "
                        f"runc cannot create the mountpoint in a :ro bind mount. "
                        f"Mount it outside '{parent}' (a separate dir) instead."
                    )
    assert not violations, "Nested-into-:ro bind mount(s):\n" + "\n".join(violations)
