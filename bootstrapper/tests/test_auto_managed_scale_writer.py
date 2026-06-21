"""Regression: every auto_managed ``*_SCALE`` env var must have a writer.

PR #124 shipped ``CLOUDFLARED_SCALE`` as ``auto_managed: true`` with the
compose fragment reading ``replicas: ${CLOUDFLARED_SCALE:-0}``, but never wired
a writer in ``service_config.py`` — so ``CLOUDFLARED_SOURCE=container`` silently
never started the tunnel (the blank ``.env`` default fell through the ``:-0``
fallback to zero replicas). ``BACKUP_SCALE`` had the same gap (harmless only
because backup is on-demand and pinned to scale 0 for every source).

This is a "no writer at all" bug class. A static guard catches it: any
``auto_managed`` ``*_SCALE`` var declared in a manifest must be assigned
literally somewhere in ``service_config.py``. The two behavioural tests pin the
specific PR #124 fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_parser import ConfigParser
from services.manifests import load_manifests
from services.service_config import ServiceConfig

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICE_CONFIG_SRC = (
    REPO_ROOT / "bootstrapper" / "services" / "service_config.py"
).read_text(encoding="utf-8")


def _auto_managed_scale_vars() -> list[str]:
    vars_ = []
    for manifest in load_manifests(REPO_ROOT / "services"):
        for ev in manifest.env:
            if ev.name.endswith("_SCALE") and ev.auto_managed:
                vars_.append(ev.name)
    return sorted(vars_)


@pytest.mark.parametrize("var", _auto_managed_scale_vars())
def test_auto_managed_scale_var_has_writer(var):
    """Every auto-managed scale var must be assigned in service_config.py.

    The compose fragments read ``replicas: ${VAR:-N}``; if the bootstrapper
    never writes ``VAR``, it stays at its blank ``.env`` default and the
    service can never scale up from the fallback.
    """
    assert (f"'{var}'" in SERVICE_CONFIG_SRC) or (
        f'"{var}"' in SERVICE_CONFIG_SRC
    ), (
        f"{var} is declared auto_managed in a manifest but is never assigned in "
        f"service_config.py. Its compose ${{{var}:-N}} fallback will leave it at "
        f"the blank .env default, so the service never scales up. Add a writer "
        f"(see _generate_other_services_config)."
    )


def test_cloudflared_scale_follows_source():
    """CLOUDFLARED_SCALE must be 1 for container, 0 for disabled (the PR #124 bug)."""
    sc = ServiceConfig(ConfigParser())
    assert sc.load_config()

    sc.service_sources = {"CLOUDFLARED_SOURCE": "container"}
    assert sc._generate_other_services_config()["CLOUDFLARED_SCALE"] == "1"

    sc.service_sources = {"CLOUDFLARED_SOURCE": "disabled"}
    assert sc._generate_other_services_config()["CLOUDFLARED_SCALE"] == "0"


def test_backup_scale_always_zero():
    """BACKUP_SCALE is 0 for every source — backup is an on-demand runner."""
    sc = ServiceConfig(ConfigParser())
    assert sc.load_config()
    for src in ("container", "disabled"):
        sc.service_sources = {"BACKUP_SOURCE": src}
        assert sc._generate_other_services_config()["BACKUP_SCALE"] == "0"
