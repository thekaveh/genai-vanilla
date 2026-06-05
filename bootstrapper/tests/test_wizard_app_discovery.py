"""
Regression tests for ServiceDiscovery — the wizard's source of truth for
which services need a user answer.

Locks down the post-merge audit finding C3: Open WebUI, JupyterHub, and
Local Deep Researcher were rendered in the box as CFG (configurable) but
were skipped by the wizard because:

  * ``open_web_ui_source`` and ``local_deep_researcher_source`` were
    missing from ``SourceOverrideManager.source_mapping`` (so they had
    no CLI flag and the wizard filtered them out).
  * ``jupyterhub`` only had ``runtime_adaptive`` (not ``runtime_sc``),
    so ``_has_source_options`` returned False and the service never
    reached the CLI-flag check.

The tests below pin the discovery contract so any future regression
(removed manifest slice, dropped source_mapping entry) fails the build.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_parser import ConfigParser
from wizard.service_discovery import ServiceDiscovery


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# Services the wizard MUST present to the user (configurable, unlocked,
# have CLI flags). Keyed by ServiceInfo.display_name so the test fails
# loudly if a Topology rename drops one.
EXPECTED_DISCOVERED = frozenset({
    "LLM Engine",
    "ComfyUI",
    "Document Processor",
    "MinIO Console",
    "n8n",
    "Neo4j Graph DB",
    "OpenClaw",
    "STT Provider",
    "SearxNG",
    "TTS Provider",
    "Weaviate",
    "Multi2Vec CLIP",
    "Hermes Agent",
    # The three that audit C3 unblocked:
    "Open WebUI",
    "JupyterHub",
    "Local Deep Researcher",
    # Ray (added 2026-05-24) — distributed-compute substrate. Wizard
    # discovery requires `ray_source` in SourceOverrideManager.source_mapping.
    "Ray",
    # Observability bundle (added 2026-05-31).
    "Prometheus",
    "Grafana",
    # Spark (added 2026-06-04) — standalone cluster, distinct from Ray.
    # Wizard discovery requires `spark_master_source` shim in
    # SourceOverrideManager.source_mapping (multi-container family).
    "Apache Spark",
    # Zeppelin (added 2026-06-04) — Spark-first notebook UI, hard-gated
    # on Spark. Single-container family so no shim needed; wired via
    # 'zeppelin_source' in source_mapping.
    "Apache Zeppelin",
    # Airflow (added 2026-06-04) — code-defined DAG orchestrator.
    # Multi-container family (webserver + scheduler + init), so wizard
    # discovery uses the `airflow_webserver_source` shim in
    # SourceOverrideManager.source_mapping (same pattern as Ray's
    # ray_head_source / Spark's spark_master_source).
    "Apache Airflow",
})


# Services that MUST NOT be in the discovered list: locked (single
# source variant, no user choice), cloud-provider toggles (collected
# via bespoke secret-input steps), or pure virtual / infra.
EXPECTED_NOT_DISCOVERED = frozenset({
    "LiteLLM",
    "Kong API Gateway",
    "Supabase DB",
    "Supabase Meta",
    "Supabase Storage",
    "Supabase Auth",
    "Supabase API",
    "Supabase Realtime",
    "Supabase Studio",
    "Redis",
    "Backend API",
})


@pytest.fixture
def discovery() -> ServiceDiscovery:
    """ServiceDiscovery wired to the real repo manifests."""
    cp = ConfigParser(str(REPO_ROOT))
    return ServiceDiscovery(cp)


def test_discovery_includes_all_configurable_app_services(discovery: ServiceDiscovery) -> None:
    """All 16 configurable services must surface in discover().

    Was a 13-service list pre-C3: Open WebUI, JupyterHub, and Local
    Deep Researcher were missing because of CLI-flag / runtime_sc gaps.
    """
    discovered_names = {svc.display_name for svc in discovery.discover()}

    missing = EXPECTED_DISCOVERED - discovered_names
    assert not missing, (
        f"Wizard discovery is missing services that should be configurable: {sorted(missing)}. "
        f"Got: {sorted(discovered_names)}"
    )


def test_discovery_excludes_locked_and_virtual_services(discovery: ServiceDiscovery) -> None:
    """Locked services (LiteLLM, Kong, Supabase, Redis, Backend) and
    cloud-provider toggles must not appear in the wizard's configurable
    list.
    """
    discovered_names = {svc.display_name for svc in discovery.discover()}

    leaked = EXPECTED_NOT_DISCOVERED & discovered_names
    assert not leaked, (
        f"Wizard discovery is leaking locked/virtual services that should be skipped: "
        f"{sorted(leaked)}"
    )


def test_discovery_count_matches_expected(discovery: ServiceDiscovery) -> None:
    """Pin the exact discovered count so silent additions/removals trip
    the test. Bump this number deliberately when adding a new
    configurable service.
    """
    discovered = discovery.discover()
    assert len(discovered) == len(EXPECTED_DISCOVERED), (
        f"Expected {len(EXPECTED_DISCOVERED)} discovered services, got {len(discovered)}: "
        f"{sorted(s.display_name for s in discovered)}"
    )


def test_open_web_ui_has_container_and_disabled_options(discovery: ServiceDiscovery) -> None:
    """Lock the option list for Open WebUI — regression guard for the
    runtime_sc slice in services/open-webui/service.yml.
    """
    discovered = {svc.key: svc for svc in discovery.discover()}
    assert "open-web-ui" in discovered, "Open WebUI missing from wizard discovery"
    assert set(discovered["open-web-ui"].options) == {"container", "disabled"}


def test_jupyterhub_has_container_and_disabled_options(discovery: ServiceDiscovery) -> None:
    """Lock the option list for JupyterHub — regression guard for the
    runtime_sc slice in services/jupyterhub/service.yml. Without it
    _has_source_options() returns False and the service vanishes.
    """
    discovered = {svc.key: svc for svc in discovery.discover()}
    assert "jupyterhub" in discovered, "JupyterHub missing from wizard discovery"
    assert set(discovered["jupyterhub"].options) == {"container", "disabled"}


def test_local_deep_researcher_has_container_and_disabled_options(
    discovery: ServiceDiscovery,
) -> None:
    """Lock the option list for Local Deep Researcher."""
    discovered = {svc.key: svc for svc in discovery.discover()}
    assert "local-deep-researcher" in discovered, (
        "Local Deep Researcher missing from wizard discovery"
    )
    assert set(discovered["local-deep-researcher"].options) == {"container", "disabled"}


def test_source_mapping_includes_app_service_flags() -> None:
    """SourceOverrideManager.source_mapping must carry the CLI keys for
    the three app services; otherwise the wizard's discover() filter
    drops them.
    """
    from utils.source_override_manager import SourceOverrideManager

    cp = ConfigParser(str(REPO_ROOT))
    mgr = SourceOverrideManager(cp)
    for cli_key in (
        "open_web_ui_source",
        "jupyterhub_source",
        "local_deep_researcher_source",
        "ray_source",
        "prometheus_source",
        "grafana_source",
    ):
        assert cli_key in mgr.source_mapping, (
            f"{cli_key} missing from SourceOverrideManager.source_mapping — "
            f"wizard discover() will silently filter the service out."
        )
