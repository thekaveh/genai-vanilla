"""
Service discovery for the interactive setup wizard.

Reads service-configs.yml and returns the list of user-configurable services
with their valid SOURCE options. Nothing is hardcoded — all service names,
options, and metadata are derived from the YAML at runtime.
"""

from dataclasses import dataclass
from typing import List

from core.config_parser import ConfigParser
from utils.source_override_manager import SourceOverrideManager


# Display name overrides for services with acronyms or special casing
DISPLAY_NAME_OVERRIDES = {
    'llm_provider': 'LLM Provider',
    'stt_provider': 'STT Provider',
    'tts_provider': 'TTS Provider',
    'doc_processor': 'Document Processor',
    'comfyui': 'ComfyUI',
    'n8n': 'n8n',
    'searxng': 'SearxNG',
    'jupyterhub': 'JupyterHub',
    'neo4j-graph-db': 'Neo4j Graph DB',
    'multi2vec-clip': 'Multi2Vec CLIP',
    'openclaw': 'OpenClaw',
    'weaviate': 'Weaviate',
}

# One-line descriptions for each service (used in wizard prompts)
SERVICE_DESCRIPTIONS = {
    'llm_provider': 'powers chat, code generation & reasoning',
    'comfyui': 'AI image generation & workflows',
    'weaviate': 'vector database for semantic search & RAG',
    'multi2vec-clip': 'CLIP embeddings for multi-modal search',
    'stt_provider': 'speech-to-text transcription',
    'tts_provider': 'text-to-speech synthesis',
    'doc_processor': 'document parsing & extraction',
    'openclaw': 'AI agent for messaging platforms',
    'n8n': 'workflow automation & integrations',
    'searxng': 'privacy-focused search engine',
    'neo4j-graph-db': 'graph database for knowledge graphs',
    'jupyterhub': 'data science IDE with notebooks',
}

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
    the wizard's Live select widget (`ui/select_widget.py`, driven by
    `wizard/tui_wizard.py`).
    """
    if 'container-gpu' in option_name or option_name.endswith('-gpu'):
        return "requires NVIDIA GPU"
    if 'container-cpu' in option_name or option_name.endswith('-cpu'):
        return "CPU only, works everywhere"
    if 'localhost' in option_name:
        return "uses local installation"
    if 'external' in option_name:
        return "remote instance"
    if option_name == 'api':
        return "cloud API (OpenAI/Anthropic)"
    if option_name == 'disabled':
        return "service will not run"
    if option_name == 'container':
        return "Docker container"
    return ""


class ServiceDiscovery:
    """Discovers user-configurable services from service-configs.yml."""

    def __init__(self, config_parser: ConfigParser):
        self.config_parser = config_parser
        # Get the set of Click parameter keys that have CLI flags
        override_manager = SourceOverrideManager(config_parser)
        self._cli_param_keys = set(override_manager.source_mapping.keys())

    def discover(self) -> List[ServiceInfo]:
        """
        Discover all user-configurable services from service-configs.yml.

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

            env_var_name = key.upper().replace('-', '_') + '_SOURCE'
            current_value = env_vars.get(env_var_name, '')
            options = list(config.keys())

            services.append(ServiceInfo(
                key=key,
                display_name=self._get_display_name(key),
                description=SERVICE_DESCRIPTIONS.get(key, ''),
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
        """Get a human-readable display name for a service key."""
        if key in DISPLAY_NAME_OVERRIDES:
            return DISPLAY_NAME_OVERRIDES[key]
        return key.replace('_', ' ').replace('-', ' ').title()
