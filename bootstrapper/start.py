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
from core.config_parser import ConfigParser
from core.docker_manager import DockerManager
from core.port_manager import PortManager
from services.source_validator import SourceValidator
from services.service_config import ServiceConfig
from services.dependency_manager import DependencyManager
from utils.source_override_manager import SourceOverrideManager

# Constants matching original Bash script
DEFAULT_BASE_PORT = 63000  # Default base port from original start.sh


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
            self.banner.show_section_header("Applying SOURCE Overrides", "🔄")
            return self.source_override_manager.apply_overrides(overrides)
        return True
        
    def validate_source_configurations(self) -> bool:
        """Validate all SOURCE configurations and scale values against YAML."""
        self.banner.show_section_header("Validating Configuration", "✓")
        
        # Validate SOURCE configurations
        sources_valid = self.source_validator.validate_all_sources()
        if not sources_valid:
            self.source_validator.print_validation_results()
            return False
            
        # Validate scale values
        scales_valid = self.source_validator.validate_scale_values()
        if not scales_valid:
            print("❌ Scale validation failed:")
            for error in self.source_validator.get_validation_errors():
                print(f"   {error}")
            return False
            
        self.source_validator.print_validation_results()
        return True
        
    def setup_env_file(self, cold_start: bool, base_port: Optional[int] = None) -> bool:
        """
        Setup .env file from .env.example if needed.
        Replicates the .env setup logic from the original start.sh.
        
        Args:
            cold_start: Whether this is a cold start
            
        Returns:
            bool: True if successful
        """
        env_file_path = self.root_dir / ".env"
        env_example_path = self.root_dir / ".env.example"
        
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
                # Copy .env.example to .env
                import shutil
                shutil.copy2(env_example_path, env_file_path)
                print(f"  • Copied {env_example_path} to {env_file_path}")
                
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
            'WEAVIATE_GRPC_PORT'
        ]
        
        print("  • Unsetting potentially lingering port environment variables...")
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
                print()
                print("  Missing keys:")
                for key in missing_keys:
                    print(f"    • {key}")
                print()
                print("  To fix this issue:")
                print("    1. Run: ./bootstrapper/generate_supabase_keys.sh")
                print("    2. Then restart this script")
                print()
                print("  💡 Tip: The generate_supabase_keys.sh script will create secure JWT keys")
                print("    to generate the required JWT keys for Supabase services.")
                return False
        
        return True
        
    def handle_port_configuration(self, base_port: Optional[int]) -> bool:
        """Handle port configuration and updates."""
        # Use default base port if not specified (matching original Bash behavior)
        if base_port is None:
            base_port = DEFAULT_BASE_PORT
            
        self.banner.show_section_header("Configuring Ports", "🔌")
        self.banner.show_status_message(f"Using base port: {base_port}", "info")
        
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
            self.banner.show_status_message("Port conflicts detected:", "warning")
            for port_var, port in conflicts.items():
                print(f"  • {port_var}: Port {port} is already in use")
            
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
            
        # Verify ports were updated correctly (matching original Bash behavior)
        self.show_verified_port_assignments(base_port)
            
        return True
        
    def show_verified_port_assignments(self, base_port: int) -> None:
        """Display verified port assignments after updating .env file."""
        print()
        self.banner.console.print("🚀 PORT ASSIGNMENTS (verified from .env file):", style="bold bright_white")
        
        # Re-read .env file to verify ports were written correctly
        env_vars = self.config_parser.parse_env_file()
        
        # Display all port assignments in the same order as original Bash
        port_assignments = [
            ("Supabase PostgreSQL Database", "SUPABASE_DB_PORT"),
            ("Redis", "REDIS_PORT"),
            ("Kong HTTP Gateway", "KONG_HTTP_PORT"),
            ("Kong HTTPS Gateway", "KONG_HTTPS_PORT"),
            ("Supabase Meta Service", "SUPABASE_META_PORT"),
            ("Supabase Storage Service", "SUPABASE_STORAGE_PORT"),
            ("Supabase Auth Service", "SUPABASE_AUTH_PORT"),
            ("Supabase API (PostgREST)", "SUPABASE_API_PORT"),
            ("Supabase Realtime", "SUPABASE_REALTIME_PORT"),
            ("Supabase Studio Dashboard", "SUPABASE_STUDIO_PORT"),
            ("Neo4j Graph Database (Bolt)", "GRAPH_DB_PORT"),
            ("Neo4j Graph Database (Dashboard)", "GRAPH_DB_DASHBOARD_PORT"),
            ("Ollama API", "LLM_PROVIDER_PORT"),
            ("Local Deep Researcher", "LOCAL_DEEP_RESEARCHER_PORT"),
            ("SearxNG Privacy Search", "SEARXNG_PORT"),
            ("Open Web UI", "OPEN_WEB_UI_PORT"),
            ("Backend API", "BACKEND_PORT"),
            ("n8n Workflow Automation", "N8N_PORT"),
            ("ComfyUI Image Generation", "COMFYUI_PORT"),
            ("Weaviate Vector DB (HTTP)", "WEAVIATE_PORT"),
            ("Weaviate Vector DB (gRPC)", "WEAVIATE_GRPC_PORT"),
        ]
        
        for service_name, port_var in port_assignments:
            verified_port = env_vars.get(port_var, 'NOT_SET')
            print(f"  • {service_name:<35} {verified_port}")
        
    def generate_service_configuration(self) -> bool:
        """Generate and update service configuration."""
        self.banner.show_section_header("Generating Service Configuration", "⚙️")
        
        return self.service_config.generate_and_update_env()
    
    def generate_kong_configuration(self) -> bool:
        """Generate dynamic Kong configuration based on SOURCE values."""
        self.banner.show_section_header("Generating Kong Configuration", "🔧")
        
        try:
            from utils.kong_config_generator import KongConfigGenerator
            generator = KongConfigGenerator(self.config_parser)
            
            # Generate configuration
            kong_config = generator.generate_kong_config()
            
            # Validate configuration
            errors = generator.validate_config(kong_config)
            if errors:
                self.banner.show_status_message("Kong configuration validation failed:", "error")
                for error in errors:
                    print(f"  • {error}")
                return False
            
            # Write to kong-dynamic.yml
            config_path = self.root_dir / "volumes/api/kong-dynamic.yml"
            if not generator.write_config(kong_config, config_path):
                return False
            
            self.banner.show_status_message(f"Kong configuration generated: {config_path}", "success")
            
            # Show enabled services
            services = kong_config.get('services', [])
            service_names = []
            for service in services:
                if 'hosts' in service.get('routes', [{}])[0]:
                    hosts = service['routes'][0]['hosts']
                    service_names.extend(hosts)
                elif service['name'] in ['dashboard', 'backend-api', 'openwebui-api']:
                    service_names.append(service['name'])
            
            if service_names:
                print(f"  • Enabled services: {len(services)} total")
                domain_services = [name for name in service_names if '.localhost' in name]
                if domain_services:
                    print(f"  • Public domains: {', '.join(domain_services[:3])}" + 
                          (f" (+{len(domain_services)-3} more)" if len(domain_services) > 3 else ""))
            
            return True
            
        except Exception as e:
            self.banner.show_status_message(f"Failed to generate Kong configuration: {e}", "error")
            return False
        
    def check_service_dependencies(self) -> bool:
        """Check and enforce service dependencies."""
        self.banner.show_section_header("Checking Service Dependencies", "🔗")
        
        # Check dependencies
        dependencies_satisfied = self.dependency_manager.check_service_dependencies()
        
        if not dependencies_satisfied:
            # Show violations
            violations = self.dependency_manager.get_dependency_violations()
            
            self.banner.show_status_message("Service dependency violations found:", "warning")
            for violation in violations:
                print(f"   ⚠️  {violation['error_message']}")
            
            print()
            self.banner.show_status_message("Auto-resolving dependency violations...", "info")
            
            # Auto-resolve by disabling dependent services
            disabled_services = self.dependency_manager.auto_resolve_dependency_violations()
            
            if disabled_services:
                for service in disabled_services:
                    self.banner.show_status_message(f"Auto-disabled {service} due to missing dependencies", "warning")
                print()
                self.banner.show_status_message("Dependency violations resolved - restarting with updated configuration", "info")
                return True
            else:
                self.banner.show_status_message("Could not auto-resolve dependency violations", "error")
                return False
        else:
            self.banner.show_status_message("All service dependencies satisfied", "success")
            return True
        
    def handle_hosts_configuration(self, setup_hosts: bool, skip_hosts: bool) -> bool:
        """Handle hosts file configuration."""
        if skip_hosts:
            self.banner.show_status_message("Skipping hosts file checks", "info")
            return True
            
        self.banner.show_section_header("Checking Hosts Configuration", "🌐")
        
        if setup_hosts:
            return self.hosts_manager.setup_hosts_entries()
        else:
            # Just check status
            self.hosts_manager.check_hosts_status()
            return True
            
    def perform_cold_start_cleanup(self) -> bool:
        """Perform cold start cleanup if requested."""
        self.banner.show_section_header("Cold Start Cleanup", "🧹")
        
        self.banner.show_status_message("Performing comprehensive cold start cleanup...", "info")
        
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
        self.banner.show_section_header("Generating Encryption Keys", "🔐")
        
        # For cold start, regenerate all keys. Otherwise, only generate missing ones.
        force_regenerate = cold_start
        
        if force_regenerate:
            self.banner.show_status_message("Regenerating all encryption keys (cold start)...", "info")
        else:
            self.banner.show_status_message("Checking for missing encryption keys...", "info")
        
        try:
            results = self.key_generator.generate_missing_keys(force_regenerate=force_regenerate)
            
            # Check results
            all_successful = all(results.values())
            
            if all_successful:
                self.banner.show_status_message("All encryption keys are ready", "success")
                return True
            else:
                failed_keys = [key for key, success in results.items() if not success]
                self.banner.show_status_message(
                    f"Failed to generate some keys: {', '.join(failed_keys)}", 
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
                
                print(f"  • {service_name}:")
                for message in messages:
                    print(f"    {message}")
                print()
                
                if not is_valid:
                    all_valid = False
            
            if all_valid:
                self.banner.show_status_message("All localhost services are accessible", "success")
            else:
                self.banner.show_status_message(
                    "Some localhost services are not accessible (warnings above)", 
                    "warning"
                )
                print("  • The stack will still start, but affected services may not work correctly")
                print("  • Please ensure localhost services are running as indicated")
                
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
            
    def display_service_status(self):
        """Display the service status table."""
        self.banner.show_service_table_header()
        
        # Get service information
        service_sources = self.config_parser.parse_service_sources()
        env_vars = self.config_parser.parse_env_file()
        
        # Display core services
        self.banner.console.print("🏗️  Infrastructure Tier", style="bold bright_blue")
        
        services_info = [
            ("  Supabase Database", service_sources.get('SUPABASE_DB_SOURCE', 'container'), 
             f"postgresql://localhost:{env_vars.get('SUPABASE_DB_PORT')}", "1"),
            ("  Redis Cache", service_sources.get('REDIS_SOURCE', 'container'),
             f"redis://localhost:{env_vars.get('REDIS_PORT')}", "1"),
            ("  Kong API Gateway", service_sources.get('KONG_API_GATEWAY_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('KONG_HTTP_PORT')}", "1"),
            ("  Neo4j Graph Database", service_sources.get('NEO4J_GRAPH_DB_SOURCE', 'container'),
             f"bolt://localhost:{env_vars.get('GRAPH_DB_PORT')}", 
             env_vars.get('NEO4J_SCALE', '1')),
        ]
        
        for service_name, source, endpoint, scale in services_info:
            service_format = "%-25s %-15s %-35s %-8s"
            service_line = service_format % (service_name, source, endpoint, scale)
            self.banner.console.print(service_line)
            
        print()
        self.banner.console.print("🤖 AI & ML Tier", style="bold bright_green")
        
        ai_services_info = [
            ("  Ollama", service_sources.get('LLM_PROVIDER_SOURCE', 'ollama-container-cpu'),
             env_vars.get('OLLAMA_ENDPOINT', 'http://ollama:11434'), 
             env_vars.get('OLLAMA_SCALE', '1')),
            ("  ComfyUI", service_sources.get('COMFYUI_SOURCE', 'container-cpu'),
             env_vars.get('COMFYUI_ENDPOINT', 'http://comfyui:18188'),
             env_vars.get('COMFYUI_SCALE', '1')),
            ("  Weaviate Vector DB", service_sources.get('WEAVIATE_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('WEAVIATE_PORT')}",
             env_vars.get('WEAVIATE_SCALE', '1')),
            ("  Multi2Vec-CLIP", service_sources.get('MULTI2VEC_CLIP_SOURCE', 'container-cpu'),
             "http://multi2vec-clip:8080", env_vars.get('CLIP_SCALE', '1')),
            ("  Local Deep Researcher", service_sources.get('LOCAL_DEEP_RESEARCHER_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('LOCAL_DEEP_RESEARCHER_PORT')}",
             env_vars.get('LOCAL_DEEP_RESEARCHER_SCALE', '1')),
        ]
        
        for service_name, source, endpoint, scale in ai_services_info:
            service_format = "%-25s %-15s %-35s %-8s"
            service_line = service_format % (service_name, source, endpoint, scale)
            self.banner.console.print(service_line)
        
        print()
        self.banner.console.print("🌐 Application Tier", style="bold bright_cyan")
        
        app_services_info = [
            ("  Open WebUI", service_sources.get('OPEN_WEB_UI_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('OPEN_WEB_UI_PORT')}",
             env_vars.get('OPEN_WEB_UI_SCALE', '1')),
            ("  Backend API", service_sources.get('BACKEND_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('BACKEND_PORT')}",
             env_vars.get('BACKEND_SCALE', '1')),
            ("  n8n Workflows", service_sources.get('N8N_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('N8N_PORT')}",
             env_vars.get('N8N_SCALE', '1')),
            ("  SearxNG Search", service_sources.get('SEARXNG_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('SEARXNG_PORT')}",
             env_vars.get('SEARXNG_SCALE', '1')),
            ("  JupyterHub IDE", service_sources.get('JUPYTERHUB_SOURCE', 'container'),
             f"http://localhost:{env_vars.get('JUPYTERHUB_PORT')}",
             env_vars.get('JUPYTERHUB_SCALE', '1')),
        ]
        
        for service_name, source, endpoint, scale in app_services_info:
            service_format = "%-25s %-15s %-35s %-8s"
            service_line = service_format % (service_name, source, endpoint, scale)
            self.banner.console.print(service_line)
        
        self.banner.show_service_table_footer()
        
    def check_comfyui_models(self):
        """Check ComfyUI local models."""
        self.service_config.check_comfyui_local_models()
        
    def show_container_status_and_verify_ports(self):
        """
        Show container status and verify actual vs expected ports.
        Replicates the verification logic from original start.sh.
        """
        print()
        
        # Show container status (docker compose ps equivalent)
        self.docker_manager.show_container_status()
        
        # Verify actual port mappings against expected values
        print()
        print("🔍 Checking if Docker assigned the expected ports...")
        
        # Get expected ports from .env
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
        
        # Check each service
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
        
    def show_final_status(self):
        """Display final startup status and instructions."""
        print()
        self.banner.console.print("🎯 GenAI Vanilla Stack started successfully!", style="bold bright_green")
        print()
        print("🌐 Access your services:")
        
        env_vars = self.config_parser.parse_env_file()
        
        # Access points matching original Bash script exactly
        print(f"  • Supabase Studio: http://localhost:{env_vars.get('SUPABASE_STUDIO_PORT')}")
        print(f"  • Open WebUI: http://localhost:{env_vars.get('OPEN_WEB_UI_PORT')}")
        print(f"  • Backend API: http://localhost:{env_vars.get('BACKEND_PORT')}/docs")
        print(f"  • n8n Workflows: http://localhost:{env_vars.get('N8N_PORT')}")
        
        # ComfyUI only if running
        comfyui_scale = env_vars.get("COMFYUI_SCALE", "0")
        if comfyui_scale != "0":
            print(f"  • ComfyUI: http://localhost:{env_vars.get('COMFYUI_PORT')}")

        # JupyterHub only if running
        jupyterhub_scale = env_vars.get("JUPYTERHUB_SCALE", "0")
        if jupyterhub_scale != "0":
            print(f"  • JupyterHub IDE: http://localhost:{env_vars.get('JUPYTERHUB_PORT')}")

        print(f"  • Neo4j Browser: http://localhost:{env_vars.get('GRAPH_DB_DASHBOARD_PORT')}")
        print(f"  • Weaviate: http://localhost:{env_vars.get('WEAVIATE_PORT')}/v1")
        
        print()
        self.banner.console.print("🛑 To stop the stack:", style="bold bright_white")
        self.banner.console.print("  • Standard stop: ./stop.py")
        self.banner.console.print("  • Cold stop: ./stop.py --cold")
        print()


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
@click.option('--help-usage', is_flag=True, help='Show detailed usage information')
def main(base_port, cold, setup_hosts, skip_hosts, llm_provider_source,
         comfyui_source, weaviate_source, n8n_source, searxng_source,
         jupyterhub_source, help_usage):
    """Start the GenAI Vanilla Stack - Cross-platform AI development environment."""
    
    starter = GenAIStackStarter()
    
    if help_usage:
        starter.show_usage()
        return
    
    # Show banner
    starter.show_banner()
    
    try:
        # Step 1: Check dependencies
        if not starter.ensure_dependencies_available():
            sys.exit(1)
        
        # Step 1.5: Setup .env file from .env.example if needed
        if not starter.setup_env_file(cold_start=cold, base_port=base_port):
            sys.exit(1)
        
        # Step 1.6: Apply SOURCE overrides from CLI arguments
        source_args = {
            'llm_provider_source': llm_provider_source,
            'comfyui_source': comfyui_source,
            'weaviate_source': weaviate_source,
            'n8n_source': n8n_source,
            'searxng_source': searxng_source,
            'jupyterhub_source': jupyterhub_source,
        }
        if not starter.apply_source_overrides(**source_args):
            sys.exit(1)
        
        # Step 1.7: Cold start cleanup if requested (before port check)
        if cold:
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
        
        # Step 8: Start Docker services (with fresh build for cold start)
        if not starter.start_docker_services(cold_start=cold):
            sys.exit(1)
        
        # Step 9: Show container status and verify ports
        starter.show_container_status_and_verify_ports()
        
        # Step 10: Display service status table
        starter.display_service_status()
        
        # Step 11: Check ComfyUI models
        starter.check_comfyui_models()
        
        # Step 12: Show final status and access points
        starter.show_final_status()
        
        # Step 13: Show container logs (final step - blocking)
        starter.show_container_logs()
        
    except KeyboardInterrupt:
        print("\n❌ Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()