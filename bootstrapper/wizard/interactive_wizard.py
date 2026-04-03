"""
Interactive setup wizard orchestrator for GenAI Vanilla Stack.

Walks the user through configuring all services step-by-step using
InquirerPy prompts, with a Rich-rendered UI including progress bar,
command preview, and confirmation summary.

Collects all selections in memory and returns them as a dict of
source overrides compatible with the existing apply_source_overrides() flow.
No .env modifications happen during the wizard — only on confirmation.
"""

import sys
from typing import Dict, Tuple

from rich.console import Console
from rich.text import Text

from core.config_parser import ConfigParser
from utils.system import is_elevated
from wizard.service_discovery import ServiceDiscovery
from wizard.ui_renderer import UIRenderer

# Must match DEFAULT_BASE_PORT in start.py
DEFAULT_BASE_PORT = 63000


class InteractiveWizard:
    """Orchestrates the interactive setup wizard flow."""

    def __init__(self, config_parser: ConfigParser):
        self.config_parser = config_parser
        self.service_discovery = ServiceDiscovery(config_parser)
        self.ui = UIRenderer()
        self.console = Console()
        self.selections = {}  # service_key -> selected SOURCE value

    def run(self) -> Tuple[Dict[str, str], dict]:
        """
        Run the interactive wizard.

        Supports restart (clears selections, starts over) and quit at any step.

        Returns:
            Tuple of (source_args, stack_options):
            - source_args: dict keyed by Click parameter names
              (e.g. 'llm_provider_source': 'ollama-localhost')
            - stack_options: dict with base_port, cold, setup_hosts, skip_hosts
        """
        from wizard import prompts

        while True:  # Restart loop — Escape on any prompt restarts
            try:
                self.selections = {}

                services = self.service_discovery.discover()
                env_vars = self.config_parser.parse_env_file()
                current_base_port = int(env_vars.get('SUPABASE_DB_PORT', DEFAULT_BASE_PORT))

                # Total steps = services + 3 stack options (base port, cold start, hosts)
                num_services = len(services)
                total = num_services + 3
                restart = False

                # Service configuration steps
                for i, service in enumerate(services):
                    self.ui.render_service_screen(i + 1, total, self.selections, env_vars)
                    selected = prompts.prompt_service_source(service)

                    if selected is None:  # Escape pressed
                        restart = True
                        break

                    self.selections[service.key] = selected
                    self._check_dependencies(service.key, selected, services, prompts)

                if restart:
                    continue

                # Base port step
                self.ui.render_stack_options_screen(
                    self.selections, num_services + 1, total, env_vars)
                base_port = prompts.prompt_base_port(current_base_port)
                if base_port is None:
                    continue

                # Cold start step
                self.ui.render_stack_options_screen(
                    self.selections, num_services + 2, total, env_vars)
                cold = prompts.prompt_cold_start()
                if cold is None:
                    continue

                # Hosts configuration step
                self.ui.render_stack_options_screen(
                    self.selections, num_services + 3, total, env_vars)
                hosts_config = prompts.prompt_hosts_setup()
                if hosts_config is None:
                    continue

                # Show completed progress bar (100% green)
                self.ui.render_completed_screen(total, self.selections, env_vars)

                # Early sudo check if setup_hosts was selected
                if hosts_config['setup_hosts']:
                    if not is_elevated():
                        self.console.print("  [bright_yellow]⚠️  Setting up hosts requires admin privileges.[/bright_yellow]")
                        self.console.print("  [bright_white]Please restart with:[/bright_white] [bright_cyan]sudo ./start.sh[/bright_cyan]")
                        self.console.print()
                        sys.exit(1)

                return self._build_source_args(), {
                    'base_port': base_port,
                    'cold': cold,
                    'setup_hosts': hosts_config['setup_hosts'],
                    'skip_hosts': hosts_config['skip_hosts'],
                }

            except KeyboardInterrupt:
                self.console.print("\n\n  [color(245)]Setup cancelled.[/color(245)]")
                sys.exit(0)

    def _check_dependencies(
        self,
        service_key: str,
        selected_value: str,
        services: list,
        prompts,
    ) -> None:
        """
        Check and resolve dependency conflicts after a service selection.

        Handles two directions:
        1. A service was disabled that others require
        2. A service was enabled that requires a disabled dependency
        """
        yaml_config = self.config_parser.load_yaml_config()
        deps = yaml_config.get('service_dependencies', {})

        # Build a map of service_key -> canonical name used in dependency config
        # The dependency config uses docker service names (e.g., 'weaviate', 'n8n')
        # while source_configurable uses keys like 'weaviate', 'n8n'

        # Direction 1: Check if disabling this service breaks others
        if selected_value == 'disabled':
            for dep_service, dep_config in deps.items():
                requires = dep_config.get('requires', [])
                # Map dependency names back to service keys
                for req in requires:
                    req_key = self._dep_name_to_service_key(req)
                    if req_key == service_key:
                        # Something requires this service — check if it's selected as enabled
                        dependent_key = self._dep_name_to_service_key(dep_service)
                        dependent_value = self.selections.get(dependent_key)
                        if dependent_value and dependent_value != 'disabled':
                            error_msg = dep_config.get(
                                'error_message',
                                f"{dep_service} requires {req}"
                            )
                            resolution = prompts.prompt_dependency_resolution(
                                service_name=dep_service,
                                dependency_name=service_key,
                                error_message=error_msg,
                            )
                            if resolution == 'enable_dependency':
                                # Re-enable this service
                                self.selections[service_key] = 'container'
                            else:
                                # Disable the dependent service
                                self.selections[dependent_key] = 'disabled'

        # Direction 2: Check if enabling this service requires a disabled dependency
        dep_config = deps.get(service_key, {})
        if not dep_config:
            # Also try with hyphens replaced
            for dep_name, config in deps.items():
                if self._dep_name_to_service_key(dep_name) == service_key:
                    dep_config = config
                    break

        if dep_config and selected_value != 'disabled':
            requires = dep_config.get('requires', [])
            for req in requires:
                req_key = self._dep_name_to_service_key(req)
                req_value = self.selections.get(req_key)
                if req_value == 'disabled':
                    error_msg = dep_config.get(
                        'error_message',
                        f"{service_key} requires {req}"
                    )
                    resolution = prompts.prompt_dependency_resolution(
                        service_name=service_key,
                        dependency_name=req_key,
                        error_message=error_msg,
                    )
                    if resolution == 'enable_dependency':
                        self.selections[req_key] = 'container'
                    else:
                        self.selections[service_key] = 'disabled'

    @staticmethod
    def _dep_name_to_service_key(dep_name: str) -> str:
        """
        Map a dependency name from service_dependencies to a service key
        in source_configurable.

        In service_dependencies, names like 'parakeet' map to 'stt_provider',
        'xtts' maps to 'tts_provider', etc. Most match directly.
        """
        # Direct mappings for services where dep name differs from config key
        dep_to_key = {
            'parakeet': 'stt_provider',
            'xtts': 'tts_provider',
            'docling': 'doc_processor',
            'ollama': 'llm_provider',
            'openclaw-gateway': 'openclaw',
        }
        return dep_to_key.get(dep_name, dep_name)

    def _build_source_args(self) -> Dict[str, str]:
        """
        Convert wizard selections to Click parameter-style keys.

        Transforms service keys (e.g., 'neo4j-graph-db') to Click parameter
        names (e.g., 'neo4j_graph_db_source') matching what
        apply_source_overrides() expects.
        """
        source_args = {}
        for key, value in self.selections.items():
            cli_key = key.replace('-', '_') + '_source'
            source_args[cli_key] = value
        return source_args
