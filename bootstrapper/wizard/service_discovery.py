"""
Service discovery for the interactive setup wizard.

Returns the list of user-configurable services with their valid SOURCE
options. Data flows through ``ConfigParser.load_yaml_config()`` which
synthesises the runtime dict from per-service manifests (each
``services/<name>/service.yml`` contributes a ``runtime_sc:`` slice; the
synthesiser at ``bootstrapper/services/sc_synthesizer.py`` concatenates
them). Nothing is hardcoded — service names, options, and metadata all
come from the manifests at startup.
"""

from dataclasses import dataclass
from typing import List

from core.config_parser import ConfigParser
from utils.source_override_manager import SourceOverrideManager


# Cloud LLM provider keys. These are NOT regular source-configurable
# services — they're API credentials routed through LiteLLM (scale: 0,
# no compose service). The wizard collects an API key for each via
# bespoke secret-input steps in ui/textual/integration.py rather than
# the standard "enabled / disabled" tile prompt that auto-discovery
# would emit. Discover() filters these out so they don't appear twice.
CLOUD_PROVIDER_KEYS = frozenset({
    'cloud_openai', 'cloud_anthropic', 'cloud_openrouter',
})

@dataclass
class ServiceInfo:
    """Information about a configurable service for the wizard."""
    key: str
    display_name: str
    description: str
    options: List[str]
    current_value: str
    env_var_name: str


def get_option_hint(option_name: str) -> str:
    """
    Derive a contextual hint from a SOURCE option name.

    Pattern-based — not hardcoded per service. If a new option name follows
    existing patterns, it gets the right hint automatically. Consumed by
    the Textual wizard via ``ui/textual/integration.py``.
    """
    if 'container-gpu' in option_name or option_name.endswith('-gpu'):
        return "requires NVIDIA GPU"
    if 'container-cpu' in option_name or option_name.endswith('-cpu'):
        return "CPU only, works everywhere"
    if 'localhost' in option_name:
        return "uses local installation"
    if 'external' in option_name:
        return "remote instance"
    if option_name == 'enabled':
        return "active in LiteLLM model_list"
    if option_name == 'disabled':
        return "service will not run"
    if option_name == 'none':
        return "no local engine — cloud only"
    if option_name == 'container':
        return "Docker container"
    return ""


class ServiceDiscovery:
    """Discovers user-configurable services from per-service manifests
    (services/<name>/service.yml, assembled into the runtime config dict
    by sc_synthesizer)."""

    def __init__(self, config_parser: ConfigParser):
        self.config_parser = config_parser
        # Get the set of Click parameter keys that have CLI flags
        override_manager = SourceOverrideManager(config_parser)
        self._cli_param_keys = set(override_manager.source_mapping.keys())

    def discover(self) -> List[ServiceInfo]:
        """
        Discover all user-configurable services from per-service manifests.

        A service is included if and only if:
        1. It has a corresponding CLI flag in source_mapping
        2. It has source-style options (sub-keys with 'scale' config, like
           'container', 'disabled', 'container-gpu', etc.)

        Scans both source_configurable and adaptive_services sections, since
        some configurable services (e.g., jupyterhub) are defined under
        adaptive_services with source-style options.

        Returns:
            Ordered list of ServiceInfo for services the wizard should present.
        """
        yaml_config = self.config_parser.load_yaml_config()
        source_configurable = yaml_config.get('source_configurable', {})
        adaptive_services = yaml_config.get('adaptive_services', {})

        env_vars = self.config_parser.parse_env_file()

        # Merge both sections: source_configurable first (preserves YAML order),
        # then adaptive_services entries not already covered
        all_services = {}
        for key, config in source_configurable.items():
            if self._has_source_options(config):
                all_services[key] = config
        for key, config in adaptive_services.items():
            if key not in all_services and self._has_source_options(config):
                all_services[key] = config

        services = []
        for key, config in all_services.items():
            # Only include services that have a corresponding CLI flag
            cli_key = key.replace('-', '_') + '_source'
            if cli_key not in self._cli_param_keys:
                continue
            # Cloud LLM provider toggles are collected via bespoke
            # secret-input steps elsewhere — skip the auto-discovered
            # "enabled / disabled" tile prompt to avoid double-asking.
            if key in CLOUD_PROVIDER_KEYS:
                continue

            # Locked manifests (1 source variant) skip the wizard entirely.
            if not hasattr(self, "_topology_cache"):
                from services.topology import build_topology
                from pathlib import Path
                self._topology_cache = build_topology(
                    Path(__file__).resolve().parent.parent.parent / "services"
                )
            target_source_var = key.upper().replace('-', '_') + '_SOURCE'
            is_locked = False
            for r in self._topology_cache.rows:
                if r.source_var == target_source_var:
                    is_locked = r.locked
                    break
            if is_locked:
                continue

            env_var_name = key.upper().replace('-', '_') + '_SOURCE'
            current_value = env_vars.get(env_var_name, '')
            options = list(config.keys())

            description = ""
            for r in self._topology_cache.rows:
                if r.source_var == target_source_var:
                    description = r.description
                    break

            services.append(ServiceInfo(
                key=key,
                display_name=self._get_display_name(key),
                description=description,
                options=options,
                current_value=current_value,
                env_var_name=env_var_name,
            ))

        return services

    @staticmethod
    def _has_source_options(config: dict) -> bool:
        """
        Check if a service config has source-style options.

        Source options have sub-keys like 'container', 'disabled' whose values
        are dicts containing 'scale'. This distinguishes them from adaptation
        metadata like 'adapts_to', 'environment_adaptation'.
        """
        if not isinstance(config, dict):
            return False
        for value in config.values():
            if isinstance(value, dict) and 'scale' in value:
                return True
        return False

    def _get_display_name(self, key: str) -> str:
        """Get a human-readable display name for a service key via Topology."""
        from services.topology import build_topology
        from pathlib import Path
        services_root = Path(__file__).resolve().parent.parent.parent / "services"
        # Cached at instance level — caller iterates once.
        if not hasattr(self, "_topology_cache"):
            self._topology_cache = build_topology(services_root)
        target_source_var = key.upper().replace('-', '_') + '_SOURCE'
        for r in self._topology_cache.rows:
            if r.source_var == target_source_var:
                return r.display_name
        return key.replace('_', ' ').replace('-', ' ').title()
