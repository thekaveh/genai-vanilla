"""
Localhost service validation utilities.

Validates that localhost services are accessible when configured as SOURCE=localhost.
"""

import socket
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Optional
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
            
    def validate_service(self, source_var: str, source_value: str) -> Tuple[bool, List[str]]:
        """
        Validate a specific service configuration.
        
        Args:
            source_var: SOURCE variable name (e.g., 'COMFYUI_SOURCE')
            source_value: SOURCE value (e.g., 'localhost')
            
        Returns:
            tuple: (is_valid, messages)
        """
        if source_var not in self.SERVICE_CHECKS:
            return True, []  # Not a service we validate
            
        config = self.SERVICE_CHECKS[source_var]
        
        # Check if this source value requires validation
        if source_value not in config['source_values']:
            return True, []  # Not a localhost source
            
        service_name = config['service_name']
        messages = []
        
        if config['check_type'] == 'http':
            # HTTP endpoint validation
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
                
                # Add specific instructions for ComfyUI
                if source_var == 'COMFYUI_SOURCE':
                    messages.append("   Please start ComfyUI locally with: python main.py --listen --port 8188")
                    messages.append("   Or refer to the documentation for installation instructions.")
                    
            return accessible, messages
            
        elif config['check_type'] == 'tcp':
            # TCP port validation
            host = config['host']
            port = config['port']
            
            accessible = self.check_tcp_port(host, port)
            
            if accessible:
                messages.append(f"✅ Localhost {service_name} service is accessible at {host}:{port}")
            else:
                messages.append(f"⚠️  Warning: {service_name} not detected at {host}:{port}")
                messages.append(f"   Make sure {service_name} is running locally before starting the stack")
                
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
            if source_var in self.SERVICE_CHECKS:
                config = self.SERVICE_CHECKS[source_var]
                if source_value in config['source_values']:
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
            config = self.SERVICE_CHECKS[source_var]
            service_name = config['service_name']
            
            print(f"  • {service_name}:")
            for message in messages:
                print(f"    {message}")
            print()
            
            if not is_valid:
                all_valid = False
                
        return all_valid