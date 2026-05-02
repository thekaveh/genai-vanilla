#!/usr/bin/env python3
"""
GenAI Vanilla Stack - Start Script

Python implementation of start.sh with full feature parity.
Cross-platform startup script for the GenAI development environment.
"""

import sys
import os
from pathlib import Path
import click
from typing import Dict, Optional

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from utils.banner import BannerDisplay
from utils.hosts_manager import HostsManager
from utils.key_generator import KeyGenerator
from utils.localhost_validator import LocalhostValidator
from core.config_parser import ConfigParser, DEFAULT_BASE_PORT
from core.docker_manager import DockerManager
from core.port_manager import PortManager
from services.source_validator import SourceValidator
from services.service_config import ServiceConfig
from services.dependency_manager import DependencyManager
from utils.source_override_manager import SourceOverrideManager

class GenAIStackStarter:
    """Main class for starting the GenAI Stack."""
    
    def __init__(self):
        # Set root directory first
        self.root_dir = Path(__file__).resolve().parent.parent
        
        # Initialize all managers with correct root_dir
        self.banner = BannerDisplay()
        self.hosts_manager = HostsManager()
        self.key_generator = KeyGenerator(str(self.root_dir))
        self.config_parser = ConfigParser(str(self.root_dir))
        self.localhost_validator = LocalhostValidator(self.config_parser)
        self.docker_manager = DockerManager(str(self.root_dir))
        self.port_manager = PortManager(str(self.root_dir))
        self.source_validator = SourceValidator(self.config_parser)
        self.service_config = ServiceConfig(self.config_parser)
        self.dependency_manager = DependencyManager(self.config_parser)
        self.source_override_manager = SourceOverrideManager(self.config_parser)


    def show_banner(self):
        """Display the startup banner."""
        self.banner.show_banner()
        
    def show_usage(self):
        """Display usage information."""
        usage_text = """
Usage: python start.py [options]

Options:
  --base-port PORT       Set base port for all services (default: 63000)
  --cold                 Perform cold start with cleanup
  --setup-hosts          Setup hosts file entries (requires admin/sudo)
  --skip-hosts           Skip hosts file checks and setup
  --help                 Show this help message

SOURCE Override Options:
  --llm-provider-source VALUE   Override LLM provider source
                                Values: ollama-container-cpu, ollama-container-gpu,
                                       ollama-localhost, ollama-external, api, disabled

  --comfyui-source VALUE        Override ComfyUI source  
                                Values: container-cpu, container-gpu,
                                       localhost, external, disabled

  --weaviate-source VALUE       Override Weaviate vector database source
                                Values: container, localhost, disabled

  --n8n-source VALUE            Override N8N workflow automation source
                                Values: container, disabled

  --searxng-source VALUE        Override SearxNG privacy search source
                                Values: container, disabled

  --jupyterhub-source VALUE     Override JupyterHub data science IDE source
                                Values: container, disabled

  --stt-provider-source VALUE   Override STT provider source
                                Values: parakeet-container-gpu, parakeet-localhost, disabled

  --tts-provider-source VALUE   Override TTS provider source
                                Values: xtts-container-gpu, xtts-localhost, disabled

  --doc-processor-source VALUE  Override document processor source
                                Values: docling-container-gpu, docling-localhost, disabled

  --openclaw-source VALUE       Override OpenClaw AI agent source
                                Values: container, localhost, disabled

  --neo4j-graph-db-source VALUE Override Neo4j graph database source
                                Values: container, localhost, disabled

  --multi2vec-clip-source VALUE Override Multi2Vec CLIP embeddings source
                                Values: container-cpu, container-gpu, disabled

Examples:
  python start.py                        # Start with defaults from .env
  python start.py --base-port 55666      # Start with custom base port
  python start.py --cold                 # Cold start with cleanup
  python start.py --setup-hosts          # Setup hosts entries
  python start.py --skip-hosts           # Skip hosts setup
  
  # Override SOURCE configurations:
  python start.py --llm-provider-source ollama-localhost --comfyui-source localhost
  python start.py --cold --base-port 55666 --llm-provider-source ollama-container-gpu
  python start.py --weaviate-source localhost --n8n-source disabled

Note: SOURCE overrides are temporary and only apply to the current session.
      The next run without arguments will use values from .env file.
"""
        print(usage_text)
        
    def ensure_dependencies_available(self) -> bool:
        """Ensure all required dependencies are available."""
        self.banner.show_section_header("Checking Dependencies", "🔍")
        
        # Check Docker availability
        if not self.docker_manager.check_docker_available():
            self.banner.show_status_message(
                "Docker is not available. Please install Docker and ensure it's running.", 
                "error"
            )
            return False
            
        # Show detected Docker compose command
        compose_cmd = self.docker_manager.get_compose_command_display()
        self.banner.show_status_message(f"Using Docker Compose command: {compose_cmd}", "info")
        
        # Check docker-compose.yml exists
        compose_file = self.root_dir / "docker-compose.yml"
        if not compose_file.exists():
            self.banner.show_status_message(
                f"Docker Compose file not found: {compose_file}", 
                "error"
            )
            return False
        self.banner.show_status_message(f"Docker Compose file found: {compose_file}", "success")
        
        # Python YAML parsing replaces yq dependency
        self.banner.show_status_message("Using native Python YAML parsing (replaces yq dependency)", "info")
        
        return True
    
    def apply_source_overrides(self, **kwargs) -> bool:
        """
        Apply SOURCE overrides from command-line arguments.
        
        Args:
            **kwargs: Command-line SOURCE override arguments
            
        Returns:
            bool: True if successful
        """
        overrides = self.source_override_manager.collect_overrides(**kwargs)
        if overrides:
            return self.source_override_manager.apply_overrides(overrides)
        return True
        
    def validate_source_configurations(self) -> bool:
        """Validate all SOURCE configurations and scale values against YAML."""
        # Silent on success — errors are shown immediately
        sources_valid = self.source_validator.validate_all_sources()
        if not sources_valid:
            self.source_validator.print_validation_results()
            return False

        scales_valid = self.source_validator.validate_scale_values()
        if not scales_valid:
            self.banner.console.print("[bright_red]❌ Scale validation failed:[/bright_red]")
            for error in self.source_validator.get_validation_errors():
                self.banner.console.print(f"   {error}")
            return False

        return True
        
    def setup_env_file(self, cold_start: bool, base_port: Optional[int] = None) -> bool:
        """
        Setup .env file from .env.example if needed.
        Supports custom .env file paths via GENAI_ENV_FILE environment variable.
        Replicates the .env setup logic from the original start.sh.

        Args:
            cold_start: Whether this is a cold start
            base_port: Optional custom base port

        Returns:
            bool: True if successful
        """
        # Use config_parser paths which respect GENAI_ENV_FILE
        env_file_path = self.config_parser.env_file_path
        env_example_path = self.config_parser.env_example_path

        # Show which env file we're using if custom
        if self.config_parser.is_using_custom_env_file():
            self.banner.show_status_message(
                f"Using custom env file: {env_file_path}",
                "info"
            )

        # Check if .env exists, if not or if cold start is requested, create from .env.example
        if not env_file_path.exists() or cold_start:
            if not env_example_path.exists():
                self.banner.show_status_message(
                    f".env.example file not found: {env_example_path}",
                    "error"
                )
                return False

            self.banner.show_section_header("Setting Up Environment", "📋")

            if cold_start:
                self.banner.show_status_message("Creating new .env file from .env.example (cold start)...", "info")
            else:
                self.banner.show_status_message("Creating new .env file from .env.example", "info")

            try:
                # Ensure parent directory exists (important for custom paths)
                env_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy .env.example to target path (default or custom)
                import shutil
                shutil.copy2(env_example_path, env_file_path)
                self.banner.show_status_message(f"  • Copied {env_example_path}", "info")
                self.banner.show_status_message(f"  •     to {env_file_path}", "info")

                # Unset potentially lingering port environment variables if cold start and custom base port are used
                effective_base_port = base_port if base_port is not None else DEFAULT_BASE_PORT
                if cold_start and effective_base_port != DEFAULT_BASE_PORT:
                    self.unset_port_environment_variables()

                self.banner.show_status_message("Environment file setup completed", "success")
                return True

            except Exception as e:
                self.banner.show_status_message(f"Failed to create .env file: {e}", "error")
                return False

        return True  # .env already exists and not cold start
        
    def unset_port_environment_variables(self) -> None:
        """
        Unset potentially lingering port environment variables.
        Replicates the unset logic from the original start.sh.
        """
        # List of all port environment variables that need to be unset
        # This matches the exact list from the original Bash script
        port_variables = [
            'SUPABASE_DB_PORT',
            'REDIS_PORT',
            'KONG_HTTP_PORT',
            'KONG_HTTPS_PORT',
            'SUPABASE_META_PORT',
            'SUPABASE_STORAGE_PORT',
            'SUPABASE_AUTH_PORT',
            'SUPABASE_API_PORT',
            'SUPABASE_REALTIME_PORT',
            'SUPABASE_STUDIO_PORT',
            'GRAPH_DB_PORT',
            'GRAPH_DB_DASHBOARD_PORT',
            'LLM_PROVIDER_PORT',
            'LOCAL_DEEP_RESEARCHER_PORT',
            'SEARXNG_PORT',
            'OPEN_WEB_UI_PORT',
            'BACKEND_PORT',
            'N8N_PORT',
            'COMFYUI_PORT',
            'WEAVIATE_PORT',
            'WEAVIATE_GRPC_PORT',
            'DOC_PROCESSOR_PORT',
            'STT_PROVIDER_PORT',
            'TTS_PROVIDER_PORT',
            'OPENCLAW_GATEWAY_PORT',
            'OPENCLAW_BRIDGE_PORT',
            'JUPYTERHUB_PORT'
        ]
        
        self.banner.show_status_message("  • Unsetting potentially lingering port environment variables...", "info")
        for var in port_variables:
            if var in os.environ:
                del os.environ[var]
    
    def validate_supabase_keys(self, cold_start: bool = False) -> bool:
        """
        Validate that required Supabase JWT keys are present.
        For cold start, automatically generate new keys if missing.
        Replicates the Supabase key check from the original start.sh.
        
        Args:
            cold_start: Whether this is a cold start (auto-generate keys if needed)
        
        Returns:
            bool: True if all keys are present or generated, False otherwise
        """
        env_vars = self.config_parser.parse_env_file()
        
        # Check for required Supabase keys
        supabase_jwt_secret = env_vars.get('SUPABASE_JWT_SECRET', '').strip()
        supabase_anon_key = env_vars.get('SUPABASE_ANON_KEY', '').strip()
        supabase_service_key = env_vars.get('SUPABASE_SERVICE_KEY', '').strip()
        
        missing_keys = []
        if not supabase_jwt_secret:
            missing_keys.append('SUPABASE_JWT_SECRET')
        if not supabase_anon_key:
            missing_keys.append('SUPABASE_ANON_KEY')
        if not supabase_service_key:
            missing_keys.append('SUPABASE_SERVICE_KEY')
        
        if missing_keys:
            if cold_start:
                # For cold start, automatically generate new Supabase keys
                self.banner.show_section_header("Generating Supabase Keys", "🔐")
                self.banner.show_status_message("Cold start detected - generating fresh Supabase JWT keys...", "info")

                from utils.supabase_keys import SupabaseKeyGenerator
                key_generator = SupabaseKeyGenerator(str(self.root_dir))

                if key_generator.generate_and_update_env():
                    self.banner.show_status_message("Supabase keys generated and applied successfully!", "success")
                    return True
                else:
                    self.banner.show_status_message("Failed to generate Supabase keys", "error")
                    return False
            else:
                # For regular start, show instructions to generate keys manually
                self.banner.show_section_header("Missing Supabase Keys", "⚠️")
                self.banner.show_status_message("Supabase JWT keys are missing!", "warning")
                self.banner.show_status_message("  Missing keys:", "warning")
                for key in missing_keys:
                    self.banner.show_status_message(f"    • {key}", "warning")
                self.banner.show_status_message("  To fix this issue:", "info")
                self.banner.show_status_message("    1. Run: ./bootstrapper/generate_supabase_keys.sh", "info")
                self.banner.show_status_message("    2. Then restart this script", "info")
                self.banner.show_status_message(
                    "  💡 Tip: The generate_supabase_keys.sh script will create secure JWT keys",
                    "info",
                )
                self.banner.show_status_message(
                    "    to generate the required JWT keys for Supabase services.", "info"
                )
                return False
        
        return True
        
    def handle_port_configuration(self, base_port: Optional[int]) -> bool:
        """Handle port configuration and updates."""
        # Use default base port if not specified (matching original Bash behavior)
        if base_port is None:
            base_port = DEFAULT_BASE_PORT
            
        # Validate base port
        if not self.port_manager.validate_base_port(base_port):
            self.banner.show_status_message(
                f"Invalid base port: {base_port}. Must be between 1024 and {65535 - 20}",
                "error"
            )
            return False
            
        # Check for port conflicts
        conflicts = self.port_manager.get_port_conflicts(base_port)
        if conflicts:
            # Check if conflicts are from our own project's containers
            if self.docker_manager.are_project_containers_running():
                self.banner.show_status_message(
                    "Previous instance detected — stopping existing containers...",
                    "info"
                )
                stop_result = self.docker_manager.stop_services(
                    remove_volumes=False, remove_orphans=True
                )
                if stop_result != 0:
                    self.banner.show_status_message(
                        "Failed to stop previous instance", "error"
                    )
                    return False

                self.banner.show_status_message(
                    "Previous instance stopped successfully", "success"
                )

                # Re-check ports after cleanup
                conflicts = self.port_manager.get_port_conflicts(base_port)

            # If conflicts remain, show the original error
            if conflicts:
                self.banner.show_status_message("Port conflicts detected:", "warning")
                for port_var, port in conflicts.items():
                    self.banner.show_status_message(
                        f"  • {port_var}: Port {port} is already in use", "warning"
                    )

                # Suggest alternative base port
                suggested_port = self.port_manager.suggest_available_base_port()
                if suggested_port:
                    self.banner.show_status_message(
                        f"Suggested available base port: {suggested_port}",
                        "info"
                    )
                return False
            
        # Update ports in .env file
        if not self.port_manager.update_env_ports(base_port):
            return False
            
        return True
        
    def generate_service_configuration(self) -> bool:
        """Generate and update service configuration."""
        return self.service_config.generate_and_update_env()
    
    def generate_kong_configuration(self) -> bool:
        """Generate dynamic Kong configuration based on SOURCE values."""
        try:
            from utils.kong_config_generator import KongConfigGenerator
            generator = KongConfigGenerator(self.config_parser)

            kong_config = generator.generate_kong_config()

            errors = generator.validate_config(kong_config)
            if errors:
                self.banner.show_status_message("Kong configuration validation failed:", "error")
                for error in errors:
                    self.banner.console.print(f"  • {error}")
                return False

            config_path = self.root_dir / "volumes/api/kong-dynamic.yml"
            if not generator.write_config(kong_config, config_path):
                return False

            return True

        except Exception as e:
            self.banner.show_status_message(f"Failed to generate Kong configuration: {e}", "error")
            return False
        
    def check_service_dependencies(self) -> bool:
        """Check and enforce service dependencies. Silent on success."""
        dependencies_satisfied = self.dependency_manager.check_service_dependencies()

        if not dependencies_satisfied:
            violations = self.dependency_manager.get_dependency_violations()
            self.banner.show_status_message("Service dependency violations found:", "warning")
            for violation in violations:
                self.banner.console.print(f"   ⚠️  {violation['error_message']}")

            disabled_services = self.dependency_manager.auto_resolve_dependency_violations()
            if disabled_services:
                for service in disabled_services:
                    self.banner.show_status_message(f"Auto-disabled {service} due to missing dependencies", "warning")
                return True
            else:
                self.banner.show_status_message("Could not auto-resolve dependency violations", "error")
                return False

        return True
        
    def handle_hosts_configuration(self, setup_hosts: bool, skip_hosts: bool) -> bool:
        """Handle hosts file configuration. Silent unless setting up or errors."""
        if skip_hosts:
            return True

        if setup_hosts:
            return self.hosts_manager.setup_hosts_entries()

        # Default: silent check, no warnings for missing entries
        return True
            
    def perform_cold_start_cleanup(self) -> bool:
        """Perform cold start cleanup if requested."""
        self.banner.show_section_header("Cold Start Cleanup", "🧹")
        
        self.banner.show_status_message("Performing cold start cleanup...", "info")
        
        # Use the enhanced cold start cleanup
        success = self.docker_manager.perform_cold_start_cleanup()
        
        if not success:
            self.banner.show_status_message("Some issues occurred during cleanup", "warning")
        else:
            self.banner.show_status_message("Cold cleanup completed successfully", "success")
            
        # Add small delay as per original script
        import time
        time.sleep(2)
            
        return True  # Continue even if cleanup had issues
        
    def generate_encryption_keys(self, cold_start: bool = False) -> bool:
        """
        Generate missing encryption keys for services.
        
        BEHAVIORAL DIFFERENCE FROM ORIGINAL BASH:
        - Original: Only generates N8N_ENCRYPTION_KEY on cold start, SearxNG secret only if missing
        - Python: Always generates missing keys, regenerates ALL keys on cold start
        
        This is an IMPROVEMENT as it ensures all required keys are always present.
        
        Args:
            cold_start: If True, regenerate all keys. If False, only generate missing ones.
            
        Returns:
            bool: True if successful
        """
        force_regenerate = cold_start

        try:
            results = self.key_generator.generate_missing_keys(force_regenerate=force_regenerate)

            if all(results.values()):
                return True
            else:
                failed_keys = [key for key, success in results.items() if not success]
                self.banner.show_status_message(
                    f"Failed to generate encryption keys: {', '.join(failed_keys)}",
                    "error"
                )
                return False

        except Exception as e:
            self.banner.show_status_message(f"Error generating encryption keys: {e}", "error")
            return False
    
    def validate_localhost_services(self) -> bool:
        """Validate localhost services are accessible before starting."""
        # Check if any services are configured for localhost
        if not self.localhost_validator.has_localhost_services():
            return True  # No localhost services to validate
            
        self.banner.show_section_header("Validating Localhost Services", "🔍")
        
        try:
            results = self.localhost_validator.validate_all_localhost_services()
            
            if not results:
                return True  # No localhost services found
            
            # Display results
            all_valid = True
            for source_var, (is_valid, messages) in results.items():
                config = self.localhost_validator.SERVICE_CHECKS[source_var]
                service_name = config['service_name']
                level = "info" if is_valid else "warning"

                self.banner.show_status_message(f"  • {service_name}:", level)
                for message in messages:
                    self.banner.show_status_message(f"    {message}", level)

                if not is_valid:
                    all_valid = False

            if all_valid:
                self.banner.show_status_message("All localhost services are accessible", "success")
            else:
                self.banner.show_status_message(
                    "Some localhost services are not accessible (warnings above)",
                    "warning"
                )
                self.banner.show_status_message(
                    "  • The stack will still start, but affected services may not work correctly",
                    "warning",
                )
                self.banner.show_status_message(
                    "  • Please ensure localhost services are running as indicated",
                    "warning",
                )
                
            return True  # Always continue, just show warnings
            
        except Exception as e:
            self.banner.show_status_message(f"Error validating localhost services: {e}", "error")
            return True  # Continue anyway
        
    def start_docker_services(self, cold_start: bool = False) -> bool:
        """Start Docker services with optional fresh build for cold start."""
        self.banner.show_section_header("Starting Services", "🚀")
        
        if cold_start:
            self.banner.show_status_message("Starting containers with fresh build (cold start)...", "info")
            
            # Build images without cache (matching original Bash script behavior)
            print("    - Building images without cache...")
            build_result = self.docker_manager.build_services(no_cache=True, pull=False)
            
            if build_result != 0:
                self.banner.show_status_message("Failed to build some services", "error")
                return False
                
            print("    - Starting containers...")
            # Start with force recreate for cold start 
            result = self.docker_manager.execute_compose_command(['up', '-d', '--force-recreate'])
            
        else:
            self.banner.show_status_message("Starting GenAI Vanilla Stack services...", "info")
            result = self.docker_manager.start_services(detached=True)
        
        if result != 0:
            self.banner.show_status_message("Failed to start some services", "error")
            return False
        else:
            self.banner.show_status_message("All services started successfully", "success")
            return True
            
    def show_pre_launch_summary(self) -> bool:
        """
        Display the combined configuration summary table with access URLs
        and hosted endpoints, then prompt for confirmation.

        Returns:
            bool: True if user confirms, False to cancel.
        """
        table = self.build_pre_launch_summary_table()
        self.banner.console.print(table)
        self.banner.console.print()

        # Confirmation prompt — legacy linear flow only. TUI mode runs the
        # launch confirmation as the wizard's last step; this branch is
        # reached only when --no-tui or non-TTY.
        if sys.stdin.isatty():
            response = self.banner.console.input(
                "  [color(245)]Launch the stack? (Y/n):[/color(245)] "
            ).strip().lower()
            return response in ('', 'y', 'yes')
        return True  # non-TTY: auto-confirm

    def build_pre_launch_summary_table(self):
        """
        Build the configuration summary as a Rich Table renderable —
        used by the legacy non-TUI flow (`show_pre_launch_summary`). The
        TUI mode renders the same configuration via `ui.info_box.render_info_box`
        inside `LogStreamApp` instead of this Rich Table.
        """
        from rich.table import Table
        from rich.text import Text
        from rich.box import HEAVY_HEAD
        from ui.state_builder import all_services, alias_for

        env_vars = self.config_parser.parse_env_file()
        service_sources = self.config_parser.parse_service_sources()
        kong_port = env_vars.get('KONG_HTTP_PORT', '63002')

        # Check if hosts entries are configured (yields the set of hostnames
        # that are PRESENT in /etc/hosts).
        hosts_present = set()
        try:
            existing_missing = self.hosts_manager.check_missing_hosts()
            all_hosts = self.hosts_manager.get_genai_hosts()
            hosts_present = set(all_hosts) - set(existing_missing)
        except Exception:
            pass

        table = Table(
            title="Stack Services Overview",
            title_style="bold bright_white",
            box=HEAVY_HEAD,
            border_style="color(240)",
            header_style="bold bright_white",
            show_lines=True,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("PORT", style="color(248)", justify="left", ratio=1, no_wrap=True)
        table.add_column("SERVICE", style="color(252)", justify="left", ratio=3, no_wrap=True)
        table.add_column("SOURCE", style="color(248)", justify="left", ratio=3, no_wrap=True)
        table.add_column("ALIAS", justify="left", ratio=4, no_wrap=True)
        table.add_column("STATUS", justify="left", ratio=2, no_wrap=True)

        # Service definitions come from state_builder.all_services() — single
        # source of truth shared with the TUI info-box (no more inline list
        # to drift out of sync).
        services = list(all_services())

        # Sort by port number ascending; services with no port go to the end.
        import re as _re

        def _sort_key(svc):
            name, source_var, port_var, _scale_var = svc
            source = service_sources.get(source_var, env_vars.get(source_var, 'container'))
            if source == 'disabled' or not port_var:
                return (2, 99999)
            if 'localhost' in source:
                lp = self._get_localhost_port(name, env_vars)
                match = _re.search(r':(\d+)', lp)
                return (1, int(match.group(1)) if match else 99999)
            try:
                return (0, int(env_vars.get(port_var, '99999')))
            except ValueError:
                return (2, 99999)

        services.sort(key=_sort_key)

        for name, source_var, port_var, scale_var in services:
            source = service_sources.get(source_var, env_vars.get(source_var, 'container'))
            scale = env_vars.get(scale_var, '0') if scale_var else '1'
            status_text, status_style = self._get_service_status(source, scale)
            source_style = "color(243)" if source == "disabled" else "color(248)"

            # PORT column
            if source == 'disabled':
                port_val = "-"
            elif 'localhost' in source:
                port_val = self._get_localhost_port(name, env_vars)
            elif port_var:
                port_val = f":{env_vars.get(port_var, '?')}"
            else:
                port_val = "-"

            # ALIAS column — alias map from state_builder (single source).
            hostname = alias_for(name)
            if hostname and hostname in hosts_present and source != 'disabled':
                alias_text = Text(f"{hostname}:{kong_port}", style="color(75)")
            else:
                alias_text = Text("-", style="color(243)")

            table.add_row(
                port_val,
                name,
                Text(source, style=source_style),
                alias_text,
                Text(status_text, style=status_style),
            )

        return table

    @staticmethod
    def _get_localhost_port(service_name: str, env_vars: dict) -> str:
        """Extract the actual localhost port from the service's endpoint env var."""
        import re
        # Map service display names to their endpoint env variables
        endpoint_vars = {
            'LLM Provider': 'OLLAMA_ENDPOINT',
            'ComfyUI': 'COMFYUI_ENDPOINT',
            'Weaviate': 'WEAVIATE_URL',
            'Neo4j Graph DB': 'NEO4J_URI',
            'STT Provider': 'PARAKEET_ENDPOINT',
            'TTS Provider': 'XTTS_ENDPOINT',
            'Document Processor': 'DOCLING_ENDPOINT',
            'OpenClaw': 'OPENCLAW_ENDPOINT',
        }
        var = endpoint_vars.get(service_name)
        if var:
            endpoint = env_vars.get(var, '')
            match = re.search(r':(\d+)', endpoint)
            if match:
                return f":{match.group(1)}"
        return "-"

    @staticmethod
    def _get_service_status(source: str, scale: str) -> tuple:
        """Get a status label with ● indicator and style for a service."""
        if source == 'disabled':
            return "● off", "color(245)"
        if 'localhost' in source:
            return "● local", "bright_cyan"
        if 'external' in source:
            return "● external", "bright_yellow"
        if source == 'api':
            return "● API", "bright_yellow"
        if 'gpu' in source:
            return "● GPU", "bright_green"
        if scale == '0':
            return "● off", "color(245)"
        return "● on", "bright_green"

    def check_comfyui_models(self):
        """Check ComfyUI local models."""
        self.service_config.check_comfyui_local_models()
        
    def show_container_status_and_verify_ports(self, on_line=None):
        """
        Show container status and verify actual vs expected ports.
        Replicates the verification logic from original start.sh.

        When `on_line` is provided (TUI mode), the redundant `docker compose ps`
        text dump is dropped and per-service results route through `on_line`
        with a level keyword ("ok"/"warn"/"error"). When `on_line` is None
        (legacy mode), behavior is unchanged from the original implementation.
        """
        # Get expected ports from .env (used by both branches)
        env_vars = self.config_parser.parse_env_file()

        # Service definitions matching original Bash script
        services_to_check = [
            ("supabase-db", "5432", env_vars.get("SUPABASE_DB_PORT", "")),
            ("redis", "6379", env_vars.get("REDIS_PORT", "")),
            ("supabase-meta", "8080", env_vars.get("SUPABASE_META_PORT", "")),
            ("supabase-storage", "5000", env_vars.get("SUPABASE_STORAGE_PORT", "")),
            ("supabase-auth", "9999", env_vars.get("SUPABASE_AUTH_PORT", "")),
            ("supabase-api", "3000", env_vars.get("SUPABASE_API_PORT", "")),
            ("supabase-realtime", "4000", env_vars.get("SUPABASE_REALTIME_PORT", "")),
            ("supabase-studio", "3000", env_vars.get("SUPABASE_STUDIO_PORT", "")),
            ("neo4j-graph-db", "7687", env_vars.get("GRAPH_DB_PORT", "")),
            ("weaviate", "8080", env_vars.get("WEAVIATE_PORT", "")),
            ("local-deep-researcher", "2024", env_vars.get("LOCAL_DEEP_RESEARCHER_PORT", "")),
            ("open-web-ui", "8080", env_vars.get("OPEN_WEB_UI_PORT", "")),
            ("backend", "8000", env_vars.get("BACKEND_PORT", "")),
            ("kong-api-gateway", "8000", env_vars.get("KONG_HTTP_PORT", "")),
            ("kong-api-gateway", "8443", env_vars.get("KONG_HTTPS_PORT", "")),
            ("n8n", "5678", env_vars.get("N8N_PORT", "")),
            ("searxng", "8080", env_vars.get("SEARXNG_PORT", "")),
            ("jupyterhub", "8888", env_vars.get("JUPYTERHUB_PORT", "")),
        ]

        # Add conditional services based on their scales
        ollama_scale = env_vars.get("OLLAMA_SCALE", "0")
        if ollama_scale != "0":
            services_to_check.append(("ollama", "11434", env_vars.get("LLM_PROVIDER_PORT", "")))

        comfyui_scale = env_vars.get("COMFYUI_SCALE", "0")
        if comfyui_scale != "0":
            services_to_check.append(("comfyui", "18188", env_vars.get("COMFYUI_PORT", "")))

        if on_line is None:
            # Legacy linear flow — preserve today's exact behavior including
            # the `docker compose ps` text dump.
            print()
            self.docker_manager.show_container_status()
            print()
            print("🔍 Checking if Docker assigned the expected ports...")

            for service_name, internal_port, expected_port in services_to_check:
                if not expected_port:
                    continue
                actual_port = self.docker_manager.get_service_port(service_name, internal_port)
                if not actual_port:
                    print(f"  • ❌ {service_name}: Could not determine port mapping")
                elif actual_port == expected_port:
                    print(f"  • ✅ {service_name}: Using expected port {expected_port}")
                else:
                    print(f"  • ⚠️  {service_name}: Expected port {expected_port} but got {actual_port}")
            return

        # TUI mode — route per-service lines through on_line, skip the ps dump.
        # The dots in the anchored box already convey "is the container up";
        # this verification is specifically about port-mapping correctness.
        mismatches = 0
        for service_name, internal_port, expected_port in services_to_check:
            if not expected_port:
                continue
            actual_port = self.docker_manager.get_service_port(service_name, internal_port)
            if not actual_port:
                on_line(f"❌ {service_name}: could not determine port mapping", "error")
                mismatches += 1
            elif actual_port == expected_port:
                on_line(f"✅ {service_name}: port {expected_port} ok", "ok")
            else:
                on_line(f"⚠️  {service_name}: expected :{expected_port}, got :{actual_port}", "warn")
                mismatches += 1
        return mismatches
                
    def show_container_logs(self):
        """
        Show container logs with follow option.
        Replicates the logs display from original start.sh.
        """
        try:
            self.docker_manager.show_container_logs(follow=True)
        except KeyboardInterrupt:
            print("\n🔄 Log viewing interrupted by user")
            print("   Use 'docker compose logs -f' to view logs again")
        


@click.command()
@click.option('--base-port', type=int, help=f'Base port for all services (default: {DEFAULT_BASE_PORT})')
@click.option('--cold', is_flag=True, help='Perform cold start with cleanup')
@click.option('--setup-hosts', is_flag=True, help='Setup hosts file entries (requires admin/sudo)')
@click.option('--skip-hosts', is_flag=True, help='Skip hosts file checks and setup')
@click.option('--llm-provider-source', 
              type=click.Choice(['ollama-container-cpu', 'ollama-container-gpu', 'ollama-localhost', 
                                'ollama-external', 'api', 'disabled'], case_sensitive=False),
              help='Override LLM_PROVIDER_SOURCE')
@click.option('--comfyui-source', 
              type=click.Choice(['container-cpu', 'container-gpu', 'localhost', 
                                'external', 'disabled'], case_sensitive=False),
              help='Override COMFYUI_SOURCE')
@click.option('--weaviate-source', 
              type=click.Choice(['container', 'localhost', 'disabled'], case_sensitive=False),
              help='Override WEAVIATE_SOURCE')
@click.option('--n8n-source', 
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override N8N_SOURCE')
@click.option('--searxng-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override SEARXNG_SOURCE')
@click.option('--jupyterhub-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override JUPYTERHUB_SOURCE')
@click.option('--stt-provider-source',
              type=click.Choice(['parakeet-container-gpu', 'parakeet-localhost',
                                'disabled'], case_sensitive=False),
              help='Override STT_PROVIDER_SOURCE')
@click.option('--tts-provider-source',
              type=click.Choice(['xtts-container-gpu', 'xtts-localhost',
                                'disabled'], case_sensitive=False),
              help='Override TTS_PROVIDER_SOURCE')
@click.option('--doc-processor-source',
              type=click.Choice(['docling-container-gpu', 'docling-localhost',
                                'disabled'], case_sensitive=False),
              help='Override DOC_PROCESSOR_SOURCE')
@click.option('--openclaw-source',
              type=click.Choice(['container', 'localhost',
                                'disabled'], case_sensitive=False),
              help='Override OPENCLAW_SOURCE')
@click.option('--neo4j-graph-db-source',
              type=click.Choice(['container', 'localhost',
                                'disabled'], case_sensitive=False),
              help='Override NEO4J_GRAPH_DB_SOURCE')
@click.option('--multi2vec-clip-source',
              type=click.Choice(['container-cpu', 'container-gpu',
                                'disabled'], case_sensitive=False),
              help='Override MULTI2VEC_CLIP_SOURCE')
@click.option('--help-usage', is_flag=True, help='Show detailed usage information')
@click.option('--no-tui', is_flag=True,
              help='Disable the TUI (wizard + Textual log app). Falls back to the legacy '
                   'linear flow with passthrough docker output. Useful for log capture, '
                   'debugging, and terminals that don\'t support the alternate screen buffer.')
def main(base_port, cold, setup_hosts, skip_hosts, llm_provider_source,
         comfyui_source, weaviate_source, n8n_source, searxng_source,
         jupyterhub_source, stt_provider_source, tts_provider_source,
         doc_processor_source, openclaw_source, neo4j_graph_db_source,
         multi2vec_clip_source, help_usage, no_tui):
    """Start the GenAI Vanilla Stack - Cross-platform AI development environment."""
    
    starter = GenAIStackStarter()
    
    if help_usage:
        starter.show_usage()
        return
    
    try:
        # Step 1.6: Apply SOURCE overrides from CLI arguments
        source_args = {
            'llm_provider_source': llm_provider_source,
            'comfyui_source': comfyui_source,
            'weaviate_source': weaviate_source,
            'n8n_source': n8n_source,
            'searxng_source': searxng_source,
            'jupyterhub_source': jupyterhub_source,
            'stt_provider_source': stt_provider_source,
            'tts_provider_source': tts_provider_source,
            'doc_processor_source': doc_processor_source,
            'openclaw_source': openclaw_source,
            'neo4j_graph_db_source': neo4j_graph_db_source,
            'multi2vec_clip_source': multi2vec_clip_source,
        }

        # Step 0: Early sudo check for CLI --setup-hosts flag
        if setup_hosts:
            from utils.system import is_elevated as _is_elevated
            if not _is_elevated():
                starter.banner.console.print("\n  [bright_yellow]⚠️  --setup-hosts requires admin privileges.[/bright_yellow]")
                starter.banner.console.print("  [bright_white]Please restart with:[/bright_white] [bright_cyan]sudo ./start.sh --setup-hosts[/bright_cyan]")
                sys.exit(1)

        # Determine if wizard mode — only when NO flags are provided at all
        wizard_ran = False
        no_source_flags = all(v is None for v in source_args.values())
        no_stack_flags = (base_port is None and not cold and not setup_hosts and not skip_hosts and not help_usage)
        will_run_wizard = no_source_flags and no_stack_flags and sys.stdin.isatty()

        # Check dependencies early — silently in wizard mode (wizard clears screen)
        if not will_run_wizard:
            if not starter.ensure_dependencies_available():
                sys.exit(1)
        else:
            if not starter.docker_manager.check_docker_available():
                print("❌ Docker is not available. Please install Docker and ensure it's running.")
                sys.exit(1)

        # Track whether the wizard ran in TUI mode — drives the post-pipeline
        # display path (scroll-region pin vs. legacy summary+prompt).
        tui_capable = False

        if will_run_wizard:
            # Setup .env first so wizard can read current defaults.
            if not starter.setup_env_file(cold_start=cold, base_port=base_port):
                sys.exit(1)

            # Decide whether to run the wizard at all: TUI (anchored-box,
            # readchar widgets) when the terminal supports it. Non-TUI shells
            # have no interactive wizard — they use .env defaults plus any
            # CLI flags the user passed.
            from ui.presentation_app import is_tui_capable as _is_tui_capable
            if _is_tui_capable(no_tui_flag=no_tui):
                from ui.presentation_app import PresentationApp
                from ui.state_builder import build_app_state
                from wizard.tui_wizard import TUIWizard

                state = build_app_state(starter.config_parser, starter.hosts_manager,
                                        box_mode="wizard")
                # The wizard's PresentationApp is the ONLY thing that runs
                # inside Live now. Once the user confirms launch, we tear
                # Live down and the rest of the flow (pipeline + docker
                # streaming) runs in plain stdout — natural mouse-wheel
                # scrollback, no flicker. ANSI scroll-region pinning keeps
                # the summary visible at the top.
                wizard_app = PresentationApp(state)
                wizard_app.__enter__()
                original_banner = starter.banner
                try:
                    starter.banner = wizard_app
                    starter.docker_manager.set_command_echo_callback(
                        lambda msg: wizard_app.log(msg.strip(), level="dim")
                    )
                    # Route HostsManager status messages through the Live
                    # region too — the level keyword maps to log levels.
                    starter.hosts_manager.set_logger(
                        lambda msg, level="info": wizard_app.log(
                            msg, level={"warning": "warn", "success": "ok"}.get(level, level)
                        )
                    )
                    wizard = TUIWizard(starter.config_parser, wizard_app)
                    try:
                        wizard_source_args, wizard_stack_options = wizard.run()
                    except KeyboardInterrupt:
                        wizard_app.log("Setup cancelled.", level="dim")
                        import time
                        time.sleep(0.5)
                        raise
                    source_args.update(wizard_source_args)
                    base_port = wizard_stack_options.get('base_port', base_port)
                    cold = wizard_stack_options.get('cold', cold)
                    setup_hosts = wizard_stack_options.get('setup_hosts', setup_hosts)
                    skip_hosts = wizard_stack_options.get('skip_hosts', skip_hosts)
                    # The wizard's last step is "Launch the stack with this
                    # configuration?" — bail out cleanly if the user said no.
                    launch_confirmed = wizard_stack_options.get('launch_confirmed', True)
                    if not launch_confirmed:
                        wizard_app.status(message="Launch cancelled", level="warn")
                        import time
                        time.sleep(1)
                        sys.exit(0)
                    wizard_ran = True
                    tui_capable = True
                finally:
                    # ALWAYS exit Live after the wizard. From here on, the
                    # rest of the flow runs in plain stdout — pipeline status
                    # messages print normally; the Textual `LogStreamApp`
                    # owns the docker streaming phase if `tui_capable`.
                    wizard_app.__exit__(None, None, None)
                    starter.banner = original_banner
                    starter.docker_manager.set_command_echo_callback(print)
                    starter.hosts_manager.set_logger(None)
            else:
                # Non-TUI shells (--no-tui, non-TTY, narrow terminals): no
                # interactive wizard. The user's existing .env defaults are
                # used; CLI flags can still override individual sources.
                pass

        # Show banner for normal mode (wizard already displayed its own)
        if not wizard_ran:
            starter.show_banner()

        # Setup .env file (skipped if wizard already did it)
        if not wizard_ran:
            if not starter.setup_env_file(cold_start=cold, base_port=base_port):
                sys.exit(1)

        if not starter.apply_source_overrides(**source_args):
            sys.exit(1)
        
        # Step 1.7: Cold start cleanup if requested (before port check)
        # In TUI mode, LogStreamApp does this itself so the noisy
        # "Container … Removed" output streams INSIDE the boxed log
        # region. Non-TUI legacy mode runs it here as before.
        if cold and not tui_capable:
            starter.perform_cold_start_cleanup()
        
        # Step 2: Validate SOURCE configurations
        if not starter.validate_source_configurations():
            sys.exit(1)
        
        # Step 3: Handle port configuration
        if not starter.handle_port_configuration(base_port):
            sys.exit(1)
        
        # Step 4: Generate service configuration
        if not starter.generate_service_configuration():
            sys.exit(1)
            
        # Step 4.1: Check service dependencies
        if not starter.check_service_dependencies():
            sys.exit(1)
        
        # Step 4.5: Generate dynamic Kong configuration
        if not starter.generate_kong_configuration():
            sys.exit(1)
        
        # Step 4.6: Validate Supabase keys (auto-generate for cold start)
        if not starter.validate_supabase_keys(cold_start=cold):
            sys.exit(1)
        
        # Step 5: Handle hosts configuration
        if not starter.handle_hosts_configuration(setup_hosts, skip_hosts):
            sys.exit(1)
        
        # Step 6: Generate encryption keys (improved behavior - always ensures keys exist)
        if not starter.generate_encryption_keys(cold_start=cold):
            sys.exit(1)
        
        # Step 7: Validate localhost services before starting
        if not starter.validate_localhost_services():
            sys.exit(1)

        # Pre-launch summary + docker streaming.
        #
        # TUI mode: hand the screen to a Textual app (LogStreamApp). It
        # composes the rendered info-box (Static widget, pinned at top)
        # above a bordered "Streaming Logs" RichLog widget. An async
        # worker drives `docker compose` build / up / verify / logs and
        # writes each line into the RichLog via Text.from_ansi() —
        # native compositing, native scrolling, native ANSI handling.
        #
        # Legacy mode (--no-tui, non-TTY, or wizard didn't run): print
        # the legacy Rich-Table summary, prompt for confirm, then run
        # the TTY-passthrough docker streaming via execute_compose_command.
        if tui_capable:
            from rich.console import Group as _Group
            from ui.log_stream_app import LogStreamApp
            from ui.state_builder import build_app_state
            from ui.info_box import render_info_box
            from ui import logo as _logo
            import shutil as _shutil

            # Use the SAME stylized info-box the wizard rendered — built
            # from a fresh AppState reflecting post-pipeline configuration.
            summary_state = build_app_state(
                starter.config_parser, starter.hosts_manager, box_mode='normal'
            )
            term_size = _shutil.get_terminal_size()
            summary = render_info_box(summary_state, available_width=term_size.columns)

            # Stack the GENAI VANILLA ASCII banner above the info-box —
            # same logo the wizard renders. Adapts to terminal size:
            # full art on tall terminals, 1-line tagline on medium,
            # nothing on short. The combined Group goes into a single
            # Static widget inside LogStreamApp.
            logo_renderable = _logo.render_logo(
                term_size.columns, term_size.lines,
                brand_name=summary_state.brand_name,
            )
            top_region = _Group(logo_renderable, summary)

            LogStreamApp(info_box=top_region, starter=starter, cold=cold).run()
        else:
            # Legacy linear flow — show the summary table, prompt to
            # confirm (since the wizard didn't), then stream.
            if not starter.show_pre_launch_summary():
                starter.banner.console.print("\n  [color(245)]Launch cancelled.[/color(245)]")
                sys.exit(0)
            if not starter.start_docker_services(cold_start=cold):
                sys.exit(1)
            starter.show_container_status_and_verify_ports()
            starter.check_comfyui_models()
            starter.show_container_logs()

    except KeyboardInterrupt:
        print("\n❌ Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()