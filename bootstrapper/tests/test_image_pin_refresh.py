"""Regression tests for _refresh_image_pins_from_manifests.

This guards against the post-merge-stale-image class of bug discovered on
2026-06-07 when a user pulled PR #62's postgres-exporter v0.16→v0.18 bump
but kept running v0.16 because the bootstrapper preserved their existing
.env value.

The fix: on every start.sh, refresh `*_IMAGE` vars from the manifest's
`images[].default`. Override path: shell-export the var.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from core.config_parser import ConfigParser
from services.service_config import ServiceConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


@pytest.fixture
def env_copy(tmp_path):
    """Build a fake-root layout with .env + a symlink to the real services/ tree.

    `_refresh_image_pins_from_manifests` reads `<root>/services/<svc>/service.yml`
    via `load_manifests(root_dir / 'services')`, so we point at a temp dir
    that links the real services/ tree.
    """
    fake_root = tmp_path / "root"
    fake_root.mkdir()
    shutil.copy(ENV_EXAMPLE, fake_root / ".env")
    (fake_root / "services").symlink_to(REPO_ROOT / "services")
    return fake_root


def _make(fake_root):
    cp = ConfigParser(root_dir=str(fake_root))
    sc = ServiceConfig(config_parser=cp)
    sc.localhost_host = "localhost"
    sc.service_sources = {}
    return sc


def test_refresh_picks_postgres_exporter_default(env_copy):
    """Pre-set .env's POSTGRES_EXPORTER_IMAGE to an old tag; refresh should
    overwrite it with the current manifest default (v0.18.1 as of 2026-06-07)."""
    env_path = env_copy / ".env"
    env_text = env_path.read_text(encoding="utf-8")
    env_text = env_text.replace(
        "POSTGRES_EXPORTER_IMAGE=prometheuscommunity/postgres-exporter:v0.18.1",
        "POSTGRES_EXPORTER_IMAGE=prometheuscommunity/postgres-exporter:v0.16.0",
    )
    env_path.write_text(env_text, encoding="utf-8")

    sc = _make(env_copy)
    env = sc._refresh_image_pins_from_manifests()
    # Manifest default should win.
    assert env.get("POSTGRES_EXPORTER_IMAGE", "").endswith(":v0.18.1"), \
        f"expected v0.18.1, got {env.get('POSTGRES_EXPORTER_IMAGE')!r}"


def test_refresh_picks_lightrag_image_default(env_copy):
    """LightRAG image pin should be refreshed from manifest on every launch."""
    sc = _make(env_copy)
    env = sc._refresh_image_pins_from_manifests()
    # Must include LightRAG image var (added in PR #62)
    assert env.get("LIGHTRAG_IMAGE", "").startswith("ghcr.io/hkuds/lightrag:")


def test_shell_export_overrides_refresh(env_copy, monkeypatch):
    """Users who shell-export an image var should NOT be overridden."""
    monkeypatch.setenv("POSTGRES_EXPORTER_IMAGE", "prometheuscommunity/postgres-exporter:custom-pin")
    sc = _make(env_copy)
    env = sc._refresh_image_pins_from_manifests()
    # When shell env has the var, refresh should skip it (preserve user pin)
    assert "POSTGRES_EXPORTER_IMAGE" not in env, \
        "shell-export override must take precedence over manifest default"


def test_refresh_covers_multiple_image_vars_per_service(env_copy):
    """TEI Reranker has 3 image vars (CPU, CPU_ARM64, GPU). All should refresh."""
    sc = _make(env_copy)
    env = sc._refresh_image_pins_from_manifests()
    assert "TEI_RERANKER_CPU_IMAGE" in env
    assert "TEI_RERANKER_CPU_ARM64_IMAGE" in env
    assert "TEI_RERANKER_GPU_IMAGE" in env


def test_refresh_handles_missing_var_or_default_gracefully(env_copy):
    """Manifests with no `images:` block or partial entries shouldn't crash."""
    sc = _make(env_copy)
    # Just call the method — should not raise even if some manifests have
    # no images block, partial entries, etc.
    env = sc._refresh_image_pins_from_manifests()
    assert isinstance(env, dict)
    # Quick sanity: should have at least 10 image vars across the stack
    assert len(env) >= 10, f"expected ≥10 image vars, got {len(env)}"
