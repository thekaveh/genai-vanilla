"""
Localhost service validation utilities.

Validates that localhost services are accessible when configured as SOURCE=localhost.
"""

import re
import socket
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
from core.config_parser import ConfigParser


class LocalhostValidator:
    """Validates localhost services accessibility."""
    
    # Service validation configurations
    SERVICE_CHECKS = {
        'LLM_PROVIDER_SOURCE': {
            'source_values': ['ollama-localhost'],
            'check_type': 'http',
            'endpoints': ['http://localhost:11434/api/tags'],
            'service_name': 'Ollama',
            'default_port': 11434
        },
        'COMFYUI_SOURCE': {
            'source_values': ['localhost'],
            'check_type': 'http',
            'endpoints': ['http://localhost:8188/system_stats', 'http://localhost:8000/system_stats'],
            'service_name': 'ComfyUI',
            'default_port': 8188,
            'fallback_ports': [8000]
        },
        'WEAVIATE_SOURCE': {
            'source_values': ['localhost'],
            'check_type': 'http',
            'endpoints': ['http://localhost:8080/v1/schema'],
            'service_name': 'Weaviate',
            'default_port': 8080
        },
        'NEO4J_GRAPH_DB_SOURCE': {
            'source_values': ['localhost'],
            'check_type': 'tcp',
            'host': 'localhost',
            'port': 7687,
            'service_name': 'Neo4j',
            'default_port': 7687
        },
        # STT and TTS providers use per-source configs because each
        # localhost variant runs a *different* binary with a different port
        # (read from its own URL env var) and a different health-probe path
        # (Parakeet MLX has /health, whisper.cpp-server only has /inference
        # and /load — no health endpoint — so we TCP-probe it instead).
        # Symmetric story on TTS: Chatterbox exposes /health, so HTTP-probe.
        'STT_PROVIDER_SOURCE': {
            'per_source': {
                'parakeet-localhost': {
                    'check_type': 'http',
                    'url_env_var': 'PARAKEET_LOCALHOST_URL',
                    'health_path': '/health',
                    'default_port': 63022,
                    'service_name': 'Parakeet STT (host-side)',
                    'hint': 'Start the Parakeet MLX/native server — see stt-provider/mlx/README.md.',
                },
                'whisper-cpp-localhost': {
                    # whisper.cpp's whisper-server has no /health endpoint
                    # (only /inference and /load). Fall back to a TCP probe
                    # against the configured port so we at least catch
                    # "server not running" without false-negatives on the
                    # unsupported health URL.
                    'check_type': 'tcp',
                    'url_env_var': 'WHISPER_CPP_LOCALHOST_URL',
                    'default_port': 63025,
                    'service_name': 'whisper.cpp STT (host-side)',
                    'hint': 'Start whisper-server — see stt-provider/whisper-cpp/README.md.',
                },
            },
        },
        'TTS_PROVIDER_SOURCE': {
            'per_source': {
                'chatterbox-localhost': {
                    'check_type': 'http',
                    'url_env_var': 'CHATTERBOX_LOCALHOST_URL',
                    'health_path': '/health',
                    'default_port': 63027,
                    'service_name': 'Chatterbox TTS (host-side)',
                    'hint': 'Start the Chatterbox server — see tts-provider/localhost/README.md.',
                },
            },
        },
        'DOC_PROCESSOR_SOURCE': {
            'source_values': ['docling-localhost'],
            'check_type': 'http',
            'port_env_var': 'DOC_PROCESSOR_PORT',
            'service_name': 'Docling Document Processor',
            'default_port': 63021
        },
        'OPENCLAW_SOURCE': {
            'source_values': ['localhost'],
            'check_type': 'http',
            'port_env_var': 'OPENCLAW_GATEWAY_PORT',
            'service_name': 'OpenClaw Gateway',
            'default_port': 63024
        }
    }
    
    def __init__(self, config_parser: Optional[ConfigParser] = None):
        """
        Initialize localhost validator.
        
        Args:
            config_parser: ConfigParser instance for reading service sources
        """
        self.config_parser = config_parser or ConfigParser()
        
    def check_http_endpoint(self, url: str, timeout: int = 5) -> bool:
        """
        Check if an HTTP endpoint is accessible.
        
        Args:
            url: URL to check
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if accessible
        """
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status < 400
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout):
            return False
            
    def check_tcp_port(self, host: str, port: int, timeout: int = 5) -> bool:
        """
        Check if a TCP port is accessible.
        
        Args:
            host: Host to check
            port: Port to check
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if accessible
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
            
    def _resolve_source_config(self, source_var: str, source_value: str) -> Optional[Dict]:
        """Pick the right SERVICE_CHECKS entry for this source.

        Returns ``None`` if the source isn't one we validate. Handles two
        shapes:

        * Legacy flat shape — top-level keys (``check_type``, ``service_name``,
          etc.) shared by every source listed in ``source_values``. Used for
          all the single-engine services (ComfyUI, Weaviate, Neo4j, …).
        * Per-source shape — ``per_source: {source_value: {...}}``. Used for
          STT/TTS providers where each localhost variant runs a different
          server with its own URL env var, probe protocol, and default port.
        """
        if source_var not in self.SERVICE_CHECKS:
            return None
        top = self.SERVICE_CHECKS[source_var]
        if 'per_source' in top:
            return top['per_source'].get(source_value)
        if source_value in top.get('source_values', []):
            return top
        return None

    @staticmethod
    def _port_from_url(url: str, fallback: int) -> int:
        """Extract the port number from a ``host:port[/...]`` URL.

        Falls back to ``fallback`` when the URL has no port (rare). Treats
        bash-substitution syntax like ``${VAR:-http://host:63025}`` correctly
        by matching the first ``:digits`` group (same approach
        state_builder.resolve_port uses for the wizard's port column).
        """
        if not url:
            return fallback
        match = re.search(r':(\d+)', url)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return fallback

    def validate_service(self, source_var: str, source_value: str) -> Tuple[bool, List[str]]:
        """
        Validate a specific service configuration.

        Args:
            source_var: SOURCE variable name (e.g., 'COMFYUI_SOURCE')
            source_value: SOURCE value (e.g., 'localhost')

        Returns:
            tuple: (is_valid, messages)
        """
        config = self._resolve_source_config(source_var, source_value)
        if config is None:
            return True, []  # Not a localhost source we validate

        service_name = config['service_name']
        messages: List[str] = []

        if config['check_type'] == 'http':
            # HTTP endpoint validation. Two ways the endpoint URL is built:
            #
            # 1. Per-source: ``url_env_var`` names a URL env var (e.g.
            #    ``WHISPER_CPP_LOCALHOST_URL=http://host.docker.internal:63025``).
            #    We extract the port from that URL and append ``health_path``.
            #    This is the correct path for STT/TTS providers because each
            #    localhost variant has its own URL env var; using a generic
            #    ``port_env_var`` would test the wrong port.
            #
            # 2. Legacy: ``port_env_var`` names a port env var (e.g.
            #    ``DOC_PROCESSOR_PORT=63021``), or ``endpoints`` is a hardcoded
            #    list. Preserved for the single-engine services (ComfyUI,
            #    Weaviate, …) so this refactor doesn't ripple beyond audio.
            if 'url_env_var' in config:
                env_vars = self.config_parser.parse_env_file()
                url_value = env_vars.get(config['url_env_var'], '')
                port = self._port_from_url(url_value, config['default_port'])
                endpoints = [f"http://localhost:{port}{config.get('health_path', '/health')}"]
            elif 'port_env_var' in config:
                env_vars = self.config_parser.parse_env_file()
                port = env_vars.get(config['port_env_var'], config['default_port'])
                endpoints = [f"http://localhost:{port}/health"]
            else:
                endpoints = config['endpoints']

            accessible = False

            for endpoint in endpoints:
                if self.check_http_endpoint(endpoint):
                    accessible = True
                    messages.append(f"✅ Localhost {service_name} service is accessible at {endpoint}")
                    break

            if not accessible:
                endpoint_list = ', '.join(endpoints)
                messages.append(f"⚠️  Warning: {service_name} not detected at {endpoint_list}")
                messages.append(f"   Make sure {service_name} is running locally before starting the stack")

                # Per-source hint (set on STT/TTS entries pointing at their localhost docs)
                hint = config.get('hint')
                if hint:
                    messages.append(f"   {hint}")
                elif source_var == 'COMFYUI_SOURCE':
                    messages.append("   Please start ComfyUI locally with: python main.py --listen --port 8188")
                    messages.append("   Or refer to the documentation for installation instructions.")

            return accessible, messages

        elif config['check_type'] == 'tcp':
            # TCP port validation. Used when the server has no health-style
            # GET endpoint (whisper-server only has /inference and /load,
            # both POST-only; a GET probe would return 405, which the HTTP
            # check treats as "down").
            if 'url_env_var' in config:
                env_vars = self.config_parser.parse_env_file()
                url_value = env_vars.get(config['url_env_var'], '')
                port = self._port_from_url(url_value, config['default_port'])
                host = 'localhost'
            else:
                host = config['host']
                port = config['port']

            accessible = self.check_tcp_port(host, port)

            if accessible:
                messages.append(f"✅ Localhost {service_name} service is reachable at {host}:{port}")
            else:
                messages.append(f"⚠️  Warning: {service_name} not detected at {host}:{port}")
                messages.append(f"   Make sure {service_name} is running locally before starting the stack")
                hint = config.get('hint')
                if hint:
                    messages.append(f"   {hint}")

            return accessible, messages

        return True, []
        
    def validate_all_localhost_services(self) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate all localhost services based on current configuration.
        
        Returns:
            dict: Dictionary mapping service names to (is_valid, messages) tuples
        """
        service_sources = self.config_parser.parse_service_sources()
        results = {}
        
        for source_var, source_value in service_sources.items():
            is_valid, messages = self.validate_service(source_var, source_value)
            if messages:  # Only include services that have validation messages
                results[source_var] = (is_valid, messages)
                
        return results
        
    def get_localhost_services(self) -> List[Tuple[str, str]]:
        """
        Get list of services configured to use localhost.

        Returns:
            list: List of (source_var, source_value) tuples for localhost services
        """
        service_sources = self.config_parser.parse_service_sources()
        localhost_services = []

        for source_var, source_value in service_sources.items():
            # Handles both legacy flat (``source_values``) and per-source shapes.
            if self._resolve_source_config(source_var, source_value) is not None:
                localhost_services.append((source_var, source_value))

        return localhost_services
        
    def has_localhost_services(self) -> bool:
        """
        Check if any services are configured to use localhost.
        
        Returns:
            bool: True if any localhost services are configured
        """
        return len(self.get_localhost_services()) > 0
        
    def display_validation_results(self, results: Dict[str, Tuple[bool, List[str]]]) -> bool:
        """
        Display validation results in a user-friendly format.
        
        Args:
            results: Results from validate_all_localhost_services()
            
        Returns:
            bool: True if all services are valid
        """
        if not results:
            return True  # No localhost services to validate
            
        print("🔍 Validating localhost services...")
        print()
        
        all_valid = True
        
        for source_var, (is_valid, messages) in results.items():
            # Pull service_name from the per-source config when present so
            # the heading matches what validate_service emitted; fall back
            # to the legacy top-level service_name for single-engine
            # entries (ComfyUI, Weaviate, etc.).
            top = self.SERVICE_CHECKS.get(source_var, {})
            if 'service_name' in top:
                service_name = top['service_name']
            else:
                source_value = self.config_parser.parse_service_sources().get(source_var, '')
                cfg = top.get('per_source', {}).get(source_value, {})
                service_name = cfg.get('service_name', source_var)
            
            print(f"  • {service_name}:")
            for message in messages:
                print(f"    {message}")
            print()
            
            if not is_valid:
                all_valid = False
                
        return all_valid