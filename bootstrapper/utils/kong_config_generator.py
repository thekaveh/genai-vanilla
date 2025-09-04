"""
Dynamic Kong Configuration Generator

Generates Kong API Gateway configuration based on SOURCE values from environment.
Replaces static kong.yml/kong-local.yml with dynamic service routing.
"""

import os
import yaml
import socket
from typing import Dict, Any, List, Optional
from pathlib import Path


class KongConfigGenerator:
    """Generates dynamic Kong configuration based on SOURCE values."""
    
    def __init__(self, config_parser):
        """
        Initialize Kong configuration generator.
        
        Args:
            config_parser: ConfigParser instance for accessing environment values
        """
        self.config_parser = config_parser
        self.env_vars = {}
        
    def load_environment_variables(self):
        """Load current environment variables from .env file."""
        self.env_vars = self.config_parser.parse_env_file()
    
    def get_env_value(self, key: str, default: str = "") -> str:
        """
        Get environment variable value.
        
        Args:
            key: Environment variable key
            default: Default value if key not found
            
        Returns:
            str: Environment variable value
        """
        return self.env_vars.get(key, default)
    
    def check_localhost_service(self, host: str, port: int, service_name: str) -> bool:
        """
        Check if a localhost service is available before adding to Kong configuration.
        
        Args:
            host: Host address (e.g., 'localhost', '127.0.0.1')
            port: Port number to check
            service_name: Service name for logging
            
        Returns:
            bool: True if service is reachable, False otherwise
        """
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.error, socket.timeout):
            print(f"⚠️  {service_name} localhost service not reachable on {host}:{port}")
            print(f"    Kong route will be created but may fail until service is started")
            return False
    
    def generate_kong_config(self) -> Dict[str, Any]:
        """
        Generate complete Kong configuration based on current SOURCE values.
        
        Returns:
            dict: Complete Kong configuration
        """
        # Load current environment
        self.load_environment_variables()
        
        # Base configuration structure
        config = {
            '_format_version': '2.1',
            '_transform': True,
            'consumers': self.get_consumers(),
            'services': self.get_all_services()
        }
        
        return config
    
    def get_consumers(self) -> List[Dict[str, Any]]:
        """Get Kong consumers configuration."""
        return [
            {
                'username': 'dashboard_user',
                'basicauth_credentials': [
                    {
                        'username': '${DASHBOARD_USERNAME}',
                        'password': '${DASHBOARD_PASSWORD}'
                    }
                ]
            }
        ]
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """
        Get all Kong services based on current SOURCE configurations.
        
        Returns:
            list: List of Kong service configurations
        """
        services = []
        
        # Always-containerized Supabase services
        services.extend(self.get_supabase_services())
        
        # SOURCE-configurable services
        comfyui_service = self.generate_comfyui_service()
        if comfyui_service:
            services.append(comfyui_service)
            
        n8n_service = self.generate_n8n_service()
        if n8n_service:
            services.append(n8n_service)
            
        searxng_service = self.generate_searxng_service()
        if searxng_service:
            services.append(searxng_service)
            
        
        # Always-containerized adaptive services
        services.extend(self.get_adaptive_services())
        
        return services
    
    def get_supabase_services(self) -> List[Dict[str, Any]]:
        """Get Supabase services (always containerized)."""
        return [
            # Auth services
            {
                'name': 'auth-v1-open',
                'url': 'http://supabase-auth:9999/verify',
                'routes': [
                    {
                        'name': 'auth-v1-open',
                        'strip_path': True,
                        'paths': ['/auth/v1/verify']
                    }
                ],
                'plugins': [{'name': 'cors'}]
            },
            {
                'name': 'auth-v1-open-callback',
                'url': 'http://supabase-auth:9999/callback',
                'routes': [
                    {
                        'name': 'auth-v1-open-callback',
                        'strip_path': True,
                        'paths': ['/auth/v1/callback']
                    }
                ],
                'plugins': [{'name': 'cors'}]
            },
            {
                'name': 'auth-v1-open-authorize',
                'url': 'http://supabase-auth:9999/authorize',
                'routes': [
                    {
                        'name': 'auth-v1-open-authorize',
                        'strip_path': True,
                        'paths': ['/auth/v1/authorize']
                    }
                ],
                'plugins': [{'name': 'cors'}]
            },
            {
                'name': 'auth-v1',
                'url': 'http://supabase-auth:9999/',
                'routes': [
                    {
                        'name': 'auth-v1-all',
                        'strip_path': True,
                        'paths': ['/auth/v1/']
                    }
                ],
                'plugins': [
                    {'name': 'cors'},
                    {'name': 'key-auth', 'config': {'key_names': ['apikey']}}
                ]
            },
            # API services
            {
                'name': 'rest-v1',
                'url': 'http://supabase-api:3000/',
                'routes': [
                    {
                        'name': 'rest-v1-all',
                        'strip_path': True,
                        'paths': ['/rest/v1/']
                    }
                ],
                'plugins': [
                    {'name': 'cors'},
                    {'name': 'key-auth', 'config': {'key_names': ['apikey']}}
                ]
            },
            {
                'name': 'graphql-v1',
                'url': 'http://supabase-api:3000/rpc/graphql',
                'routes': [
                    {
                        'name': 'graphql-v1-all',
                        'strip_path': True,
                        'paths': ['/graphql/v1/']
                    }
                ],
                'plugins': [
                    {'name': 'cors'},
                    {'name': 'key-auth', 'config': {'key_names': ['apikey']}}
                ]
            },
            # Realtime services
            {
                'name': 'realtime-v1-ws',
                'url': 'http://supabase-realtime:4000/socket',
                'protocol': 'ws',
                'routes': [
                    {
                        'name': 'realtime-v1-ws',
                        'strip_path': True,
                        'paths': ['/realtime/v1/']
                    }
                ],
                'plugins': [{'name': 'cors'}]
            },
            {
                'name': 'realtime-v1-rest',
                'url': 'http://supabase-realtime:4000/api',
                'protocol': 'http',
                'routes': [
                    {
                        'name': 'realtime-v1-rest',
                        'strip_path': True,
                        'paths': ['/realtime/v1/api/']
                    }
                ],
                'plugins': [
                    {'name': 'cors'},
                    {'name': 'key-auth', 'config': {'key_names': ['apikey']}}
                ]
            },
            # Storage services
            {
                'name': 'storage-v1',
                'url': 'http://supabase-storage:5000/',
                'routes': [
                    {
                        'name': 'storage-v1-all',
                        'strip_path': True,
                        'paths': ['/storage/v1/']
                    }
                ],
                'plugins': [
                    {'name': 'cors'},
                    {'name': 'key-auth', 'config': {'key_names': ['apikey']}}
                ]
            },
            # Meta service
            {
                'name': 'meta',
                'url': 'http://supabase-meta:8080/',
                'routes': [
                    {
                        'name': 'meta-all',
                        'strip_path': True,
                        'paths': ['/pg/']
                    }
                ],
                'plugins': [
                    {'name': 'cors'},
                    {'name': 'basic-auth'},
                    {'name': 'acl', 'config': {'allow': ['dashboard_user']}}
                ]
            },
            # Studio dashboard
            {
                'name': 'dashboard',
                'url': 'http://supabase-studio:3000/',
                'routes': [
                    {
                        'name': 'dashboard-all',
                        'strip_path': False,
                        'paths': ['/']
                    }
                ],
                'plugins': [{'name': 'cors'}]
            }
        ]
    
    def generate_comfyui_service(self) -> Optional[Dict[str, Any]]:
        """Generate ComfyUI service configuration based on SOURCE."""
        source = self.get_env_value('COMFYUI_SOURCE')
        
        if source == 'disabled':
            return None
            
        service = {
            'name': 'comfyui-api',
            'routes': [
                {
                    'name': 'comfyui-api-all',
                    'strip_path': False,
                    'hosts': ['comfyui.localhost']
                }
            ],
            'plugins': [{'name': 'cors'}]
        }
        
        # Dynamic URL based on SOURCE
        if source == 'localhost':
            # Health check for localhost service
            self.check_localhost_service('localhost', 8000, 'ComfyUI')
            service['url'] = 'http://host.docker.internal:8000/'
        elif source == 'external':
            external_url = self.get_env_value('COMFYUI_EXTERNAL_URL')
            if not external_url:
                print("❌ COMFYUI_SOURCE is set to 'external' but COMFYUI_EXTERNAL_URL is not provided")
                return None
            if not external_url.startswith(('http://', 'https://')):
                print("❌ COMFYUI_EXTERNAL_URL must be a valid URL starting with http:// or https://")
                return None
            service['url'] = external_url
        elif source in ['container-cpu', 'container-gpu']:
            service['url'] = 'http://comfyui:18188/'
        else:
            # Default to container
            service['url'] = 'http://comfyui:18188/'
        
        return service
    
    def generate_n8n_service(self) -> Optional[Dict[str, Any]]:
        """Generate N8N service configuration based on SOURCE."""
        source = self.get_env_value('N8N_SOURCE')
        
        if source == 'disabled':
            return None
            
        return {
            'name': 'n8n-api',
            'url': 'http://n8n:5678/',
            'connect_timeout': 60000,
            'write_timeout': 60000,
            'read_timeout': 60000,
            'routes': [
                {
                    'name': 'n8n-api-all',
                    'strip_path': False,
                    'preserve_host': True,
                    'hosts': ['n8n.localhost']
                }
            ],
            'plugins': [
                {'name': 'cors'},
                {'name': 'request-transformer', 'config': {
                    'add': {'headers': ['X-Forwarded-Host: n8n.localhost:${KONG_HTTP_PORT}']}
                }}
            ]
        }
    
    def generate_searxng_service(self) -> Optional[Dict[str, Any]]:
        """Generate SearxNG service configuration based on SOURCE."""
        source = self.get_env_value('SEARXNG_SOURCE')
        
        if source == 'disabled':
            return None
            
        return {
            'name': 'searxng-api',
            'url': 'http://searxng:8080/',
            'routes': [
                {
                    'name': 'searxng-api-all',
                    'strip_path': False,
                    'hosts': ['search.localhost']
                }
            ],
            'plugins': [
                {'name': 'cors'},
                {
                    'name': 'rate-limiting',
                    'config': {
                        'minute': 60,
                        'hour': 1000,
                        'policy': 'local'
                    }
                }
            ]
        }
    
    
    
    def get_adaptive_services(self) -> List[Dict[str, Any]]:
        """Get adaptive services (always containerized when enabled)."""
        services = []
        
        # Backend API
        backend_service = self.generate_backend_service()
        if backend_service:
            services.append(backend_service)
        
        # Open-WebUI
        openwebui_service = self.generate_openwebui_service()
        if openwebui_service:
            services.append(openwebui_service)
        
        return services
    
    def generate_backend_service(self) -> Optional[Dict[str, Any]]:
        """Generate Backend API service configuration based on SOURCE."""
        source = self.get_env_value('BACKEND_SOURCE')
        
        if source == 'disabled':
            return None
            
        return {
            'name': 'backend-api',
            'url': 'http://backend:8000/',
            'routes': [
                {
                    'name': 'backend-api-all',
                    'strip_path': False,
                    'hosts': ['api.localhost']
                }
            ],
            'plugins': [{'name': 'cors'}]
        }
    
    def generate_openwebui_service(self) -> Optional[Dict[str, Any]]:
        """Generate Open-WebUI service configuration based on SOURCE."""
        source = self.get_env_value('OPEN_WEB_UI_SOURCE')
        
        if source == 'disabled':
            return None
            
        return {
            'name': 'openwebui-api',
            'url': 'http://open-web-ui:8080/',
            'routes': [
                {
                    'name': 'openwebui-api-all',
                    'strip_path': False,
                    'hosts': ['chat.localhost']
                }
            ],
            'plugins': [{'name': 'cors'}]
        }
    
    def write_config(self, config: Dict[str, Any], output_path: Path) -> bool:
        """
        Write Kong configuration to YAML file.
        
        Args:
            config: Kong configuration dictionary
            output_path: Path to write configuration file
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return True
        except Exception as e:
            print(f"❌ Failed to write Kong configuration: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate Kong configuration.
        
        Args:
            config: Kong configuration to validate
            
        Returns:
            list: List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required top-level fields
        required_fields = ['_format_version', 'services']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate services
        services = config.get('services', [])
        for i, service in enumerate(services):
            if 'name' not in service:
                errors.append(f"Service {i} missing name")
            if 'url' not in service:
                errors.append(f"Service {service.get('name', i)} missing URL")
        
        return errors