"""
Build AppState from the existing config — port assignments, SOURCE values,
hosts entries, brand metadata — so the renderable layer doesn't need to
know anything about .env, the per-service manifests, or the bootstrapper
internals.

Module-level helpers (`resolve_port`, `alias_for`, `lookup_service_meta`)
are also exposed so the wizard can mutate AppState in-place when the user
picks a new SOURCE for a service.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.config_parser import ConfigParser
from utils.hosts_manager import HostsManager
from ui.state import AppState, CloudApiEntry, ServiceEntry
from services.topology import build_topology, Topology


# Topology is built once per process. Refresh by calling _refresh_topology()
# from tests; the wizard does not refresh during a single run.
_topology_singleton: Topology | None = None
_SERVICES_ROOT = Path(__file__).resolve().parent.parent.parent / "services"


def _get_topology() -> Topology:
    global _topology_singleton
    if _topology_singleton is None:
        _topology_singleton = build_topology(_SERVICES_ROOT)
    return _topology_singleton


def _refresh_topology() -> None:
    """Test hook — force rebuild on next access."""
    global _topology_singleton
    _topology_singleton = None


# Cloud LLM providers — API toggles, NOT services. Single source of
# truth in utils/cloud_providers.py. They live behind the LiteLLM
# gateway (no compose service of their own) and render in a dedicated
# "Cloud APIs" sub-section in the overview, not in the services grid.
from utils.cloud_providers import CLOUD_PROVIDERS as _CLOUD_PROVIDERS  # noqa: E402

_CLOUD_APIS = [
    (p.name, p.source_var, p.api_key_var) for p in _CLOUD_PROVIDERS
]


def lookup_service_meta(name: str) -> Optional[dict]:
    """Return {'name', 'source_var', 'port_var', 'scale_var'} for the given
    display name, or None if no row matches."""
    for r in _get_topology().rows:
        if r.display_name == name:
            return {
                "name": r.display_name,
                "source_var": r.source_var,
                "port_var": r.port_var,
                "scale_var": r.scale_var,
            }
    return None


def resolve_port(name: str, source: str, port_var: Optional[str], env: dict) -> Optional[str]:
    """Compute the displayed port for a service given its current SOURCE, its
    port env var, and the parsed .env."""
    if source == "disabled":
        return None
    if "localhost" in source:
        endpoint_var = None
        for r in _get_topology().rows:
            if r.display_name == name:
                endpoint_var = r.localhost_endpoint_var
                break
        if endpoint_var:
            endpoint = env.get(endpoint_var, "")
            match = re.search(r":(\d+)", endpoint)
            if match:
                return f":{match.group(1)}"
        return None
    if port_var:
        port = env.get(port_var, "")
        return f":{port}" if port else None
    return None


def alias_for(name: str) -> Optional[str]:
    """Hosts alias for a service display name, or None if no alias declared."""
    for r in _get_topology().rows:
        if r.display_name == name:
            return r.alias
    return None


def all_services():
    """Iterate canonical service tuples — display order from Topology.

    Yields (display_name, source_var, port_var, scale_var). Kept tuple-shaped
    for back-compat with start.py::build_pre_launch_summary_table.
    """
    return tuple(
        (r.display_name, r.source_var, r.port_var or None, r.scale_var or None)
        for r in _get_topology().rows
    )


def all_cloud_apis():
    """
    Iterate the canonical cloud-API definitions: yields
    (display_name, source_var, api_key_var) tuples. Single source of
    truth for the TUI overview, the no-TUI summary, and the wizard's
    secret-input prompt steps.
    """
    return tuple(_CLOUD_APIS)


def cloud_api_status_text(enabled: bool, key_set: bool) -> str:
    """Canonical display string for a cloud-API row's (enabled, key_set)
    pair. Shared by the Rich pre-launch panel in start.py and the
    Textual ``CloudApisRow`` so both render paths stay in lockstep —
    each renderer applies its own styling on top of the same string.
    """
    if enabled and key_set:
        return "enabled · key set ✓"
    if enabled and not key_set:
        return "enabled · key MISSING ⚠"
    return "disabled"


def _brand_field(env: dict, env_var: str, fallback: str) -> str:
    """Read a brand metadata value from .env, falling back to the canonical default."""
    value = env.get(env_var)
    return value if value else fallback


def build_app_state(
    config_parser: ConfigParser,
    hosts_manager: Optional[HostsManager] = None,
    *,
    box_mode: str = "normal",
) -> AppState:
    """Build a fresh AppState snapshot from .env + per-service manifests."""
    env = config_parser.parse_env_file()
    service_sources = config_parser.parse_service_sources()

    env_file_path = None
    if config_parser.is_using_custom_env_file():
        env_file_path = str(config_parser.env_file_path)

    # Brand metadata — overridable via .env. Defaults match the canonical
    # GenAI Vanilla project values declared on `AppState`.
    defaults = AppState()
    brand_name = _brand_field(env, "BRAND_NAME", defaults.brand_name)
    tagline = _brand_field(env, "BRAND_TAGLINE", defaults.tagline)
    version = _brand_field(env, "BRAND_VERSION", defaults.version)
    creator = _brand_field(env, "BRAND_AUTHOR", defaults.creator)
    creator_email = _brand_field(env, "BRAND_AUTHOR_EMAIL", defaults.creator_email)
    license_str = _brand_field(env, "BRAND_LICENSE", defaults.license)
    repo_url = _brand_field(env, "BRAND_REPO_URL", defaults.repo_url)

    services = []
    for r in _get_topology().rows:
        source = service_sources.get(r.source_var, env.get(r.source_var, "container"))
        services.append(ServiceEntry(
            name=r.display_name,
            port=resolve_port(r.display_name, source, r.port_var, env),
            source=source,
            alias=r.alias,
            category=r.category,
            pending=False,  # initial state; wizard sets True for unanswered rows
        ))

    cloud_apis = []
    for name, source_var, api_key_var in _CLOUD_APIS:
        source = (
            service_sources.get(source_var, env.get(source_var, "disabled")) or ""
        ).strip().lower()
        key_value = (env.get(api_key_var, "") or "").strip()
        cloud_apis.append(CloudApiEntry(
            name=name,
            source_var=source_var,
            api_key_var=api_key_var,
            enabled=(source == "enabled"),
            key_set=bool(key_value),
        ))

    hosts_configured = False
    if hosts_manager is not None:
        try:
            existing_missing = hosts_manager.check_missing_hosts()
            all_hosts = hosts_manager.get_genai_hosts()
            hosts_configured = bool(set(all_hosts) - set(existing_missing))
        except Exception:
            hosts_configured = False

    return AppState(
        brand_name=brand_name,
        tagline=tagline,
        version=version,
        creator=creator,
        creator_email=creator_email,
        license=license_str,
        repo_url=repo_url,
        services=services,
        cloud_apis=cloud_apis,
        hosts_configured=hosts_configured,
        kong_port=env.get("KONG_HTTP_PORT", "63002"),
        env_file_path=env_file_path,
        box_mode=box_mode,
    )
