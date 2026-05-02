"""
Build AppState from the existing config — port assignments, SOURCE values,
hosts entries, brand metadata — so the renderable layer doesn't need to
know anything about .env, service-configs.yml, or the bootstrapper
internals.

Module-level helpers (`resolve_port`, `alias_for`, `lookup_service_meta`)
are also exposed so the wizard can mutate AppState in-place when the user
picks a new SOURCE for a service.
"""

from __future__ import annotations

import re
from typing import Optional

from core.config_parser import ConfigParser
from utils.hosts_manager import HostsManager
from ui.state import AppState, ServiceEntry


# Service definitions. Tuple shape: (display_name, source_var, port_var, scale_var)
# scale_var=None means "always-on", treated as scale=1.
_SERVICES = [
    # Always-on infrastructure
    ("Supabase DB",        "SUPABASE_DB_SOURCE",        "SUPABASE_DB_PORT",        None),
    ("Supabase Studio",    "SUPABASE_STUDIO_SOURCE",    "SUPABASE_STUDIO_PORT",    None),
    ("Redis",              "REDIS_SOURCE",              "REDIS_PORT",              None),
    ("Kong API Gateway",   "KONG_API_GATEWAY_SOURCE",   "KONG_HTTP_PORT",          None),
    # Configurable
    ("LLM Provider",       "LLM_PROVIDER_SOURCE",       "LLM_PROVIDER_PORT",       "OLLAMA_SCALE"),
    ("ComfyUI",            "COMFYUI_SOURCE",            "COMFYUI_PORT",            "COMFYUI_SCALE"),
    ("Weaviate",           "WEAVIATE_SOURCE",           "WEAVIATE_PORT",           "WEAVIATE_SCALE"),
    ("Multi2Vec CLIP",     "MULTI2VEC_CLIP_SOURCE",     None,                      "CLIP_SCALE"),
    ("Neo4j Graph DB",     "NEO4J_GRAPH_DB_SOURCE",     "GRAPH_DB_DASHBOARD_PORT", "NEO4J_SCALE"),
    ("STT Provider",       "STT_PROVIDER_SOURCE",       "STT_PROVIDER_PORT",       "PARAKEET_GPU_SCALE"),
    ("TTS Provider",       "TTS_PROVIDER_SOURCE",       "TTS_PROVIDER_PORT",       "XTTS_GPU_SCALE"),
    ("Document Processor", "DOC_PROCESSOR_SOURCE",      "DOC_PROCESSOR_PORT",      "DOCLING_GPU_SCALE"),
    ("OpenClaw",           "OPENCLAW_SOURCE",           "OPENCLAW_GATEWAY_PORT",   "OPENCLAW_SCALE"),
    ("n8n",                "N8N_SOURCE",                "N8N_PORT",                "N8N_SCALE"),
    ("SearxNG",            "SEARXNG_SOURCE",            "SEARXNG_PORT",            "SEARXNG_SCALE"),
    ("JupyterHub",         "JUPYTERHUB_SOURCE",         "JUPYTERHUB_PORT",         "JUPYTERHUB_SCALE"),
    ("Open WebUI",         "OPEN_WEB_UI_SOURCE",        "OPEN_WEB_UI_PORT",        "OPEN_WEB_UI_SCALE"),
    ("Backend API",        "BACKEND_SOURCE",            "BACKEND_PORT",            "BACKEND_SCALE"),
    ("Local Deep Researcher", "LOCAL_DEEP_RESEARCHER_SOURCE", "LOCAL_DEEP_RESEARCHER_PORT", "LOCAL_DEEP_RESEARCHER_SCALE"),
]

# Display name → hosts.localhost alias. Single source of truth — also
# consumed by start.py::build_pre_launch_summary_table via alias_for().
_HOST_ALIAS = {
    "n8n": "n8n.localhost",
    "Open WebUI": "chat.localhost",
    "Backend API": "api.localhost",
    "SearxNG": "search.localhost",
    "ComfyUI": "comfyui.localhost",
    "JupyterHub": "jupyter.localhost",
    "OpenClaw": "openclaw.localhost",
}

# Endpoint env vars used by localhost services. Mirror of
# GenAIStackStarter._get_localhost_port (start.py).
_LOCALHOST_ENDPOINT_VARS = {
    "LLM Provider": "OLLAMA_ENDPOINT",
    "ComfyUI": "COMFYUI_ENDPOINT",
    "Weaviate": "WEAVIATE_URL",
    "Neo4j Graph DB": "NEO4J_URI",
    "STT Provider": "PARAKEET_ENDPOINT",
    "TTS Provider": "XTTS_ENDPOINT",
    "Document Processor": "DOCLING_ENDPOINT",
    "OpenClaw": "OPENCLAW_ENDPOINT",
}

# Cached lookup: display name → service definition tuple. Built once at
# import time. Used by `apply_wizard_selection` to find the metadata for
# a given service when re-deriving its port after a user changes its source.
_LOOKUP_BY_NAME = {tup[0]: tup for tup in _SERVICES}


def lookup_service_meta(name: str) -> Optional[dict]:
    """
    Return {'name','source_var','port_var','scale_var'} for the given
    service display name, or None if the service isn't in the canonical
    list.
    """
    tup = _LOOKUP_BY_NAME.get(name)
    if tup is None:
        return None
    return {
        "name": tup[0],
        "source_var": tup[1],
        "port_var": tup[2],
        "scale_var": tup[3],
    }


def resolve_port(name: str, source: str, port_var: Optional[str], env: dict) -> Optional[str]:
    """
    Compute the displayed port for a service given its current SOURCE,
    its port env var, and the parsed .env. Mirrors
    `GenAIStackStarter._get_localhost_port` plus the regular port lookup.
    """
    if source == "disabled":
        return None
    if "localhost" in source:
        endpoint_var = _LOCALHOST_ENDPOINT_VARS.get(name)
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
    """Hosts alias for a service, or None if it doesn't have one."""
    return _HOST_ALIAS.get(name)


def all_services():
    """
    Iterate the canonical service definitions: yields
    (display_name, source_var, port_var, scale_var) tuples in the order
    they're defined in `_SERVICES`. Consumed by both the TUI box
    rendering (via `build_app_state`) and the legacy non-TUI summary
    table (via `start.py::build_pre_launch_summary_table`) so both
    render paths share a single source of truth.
    """
    return tuple(_SERVICES)


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
    """Build a fresh AppState snapshot from .env + service-configs.yml."""
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
    license_str = _brand_field(env, "BRAND_LICENSE", defaults.license)
    repo_url = _brand_field(env, "BRAND_REPO_URL", defaults.repo_url)

    services = []
    for name, source_var, port_var, scale_var in _SERVICES:
        source = service_sources.get(source_var, env.get(source_var, "container"))
        services.append(ServiceEntry(
            name=name,
            port=resolve_port(name, source, port_var, env),
            source=source,
            alias=alias_for(name),
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
        license=license_str,
        repo_url=repo_url,
        services=services,
        hosts_configured=hosts_configured,
        kong_port=env.get("KONG_HTTP_PORT", "63002"),
        env_file_path=env_file_path,
        box_mode=box_mode,
    )
