"""
Service configuration generation based on YAML and SOURCE values.

Python implementation of generate_service_environment() and related functions from start.sh.
"""

import re
from typing import Dict, Any, Optional
from core.config_parser import ConfigParser
from utils.system import get_localhost_host


class ServiceConfig:
    """Generates service configurations based on YAML and SOURCE values."""
    
    def __init__(self, config_parser: Optional[ConfigParser] = None):
        """
        Initialize service configuration manager.
        
        Args:
            config_parser: ConfigParser instance (creates new one if None)
        """
        self.config_parser = config_parser or ConfigParser()
        self.yaml_config = None
        self.service_sources = {}
        self.localhost_host = get_localhost_host()
        
    def load_config(self) -> bool:
        """
        Load YAML configuration and service sources.
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            self.yaml_config = self.config_parser.load_yaml_config()
            self.service_sources = self.config_parser.parse_service_sources()
            return True
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return False
    
    def get_service_config(self, service_key: str, source_value: str) -> Dict[str, Any]:
        """
        Get configuration for a specific service and source.
        
        Args:
            service_key: Service key in YAML (e.g., "llm_provider")
            source_value: SOURCE value (e.g., "ollama-container-cpu")
            
        Returns:
            dict: Service configuration from YAML
        """
        if not self.yaml_config:
            return {}
            
        source_configurable = self.yaml_config.get('source_configurable', {})
        service_configs = source_configurable.get(service_key, {})
        return service_configs.get(source_value, {})
    
    def generate_service_environment(self) -> Dict[str, str]:
        """
        Generate all service environment variables based on YAML configuration.
        Replicates the generate_service_environment() function from start.sh.
        
        Returns:
            dict: Dictionary of environment variables to set
        """
        if not self.load_config():
            return {}
            
        env_vars = {}
        
        print("🔧 Generating service environment from YAML configuration...")
        print(f"🔗 Using '{self.localhost_host}' for localhost service connections")
        
        # Generate LLM Provider (Ollama) configuration
        llm_config = self._generate_llm_provider_config()
        env_vars.update(llm_config)
        
        # Generate ComfyUI configuration
        comfyui_config = self._generate_comfyui_config()
        env_vars.update(comfyui_config)
        
        # Generate Weaviate configuration 
        weaviate_config = self._generate_weaviate_config()
        env_vars.update(weaviate_config)
        
        # Generate Multi2Vec CLIP configuration
        clip_config = self._generate_clip_config()
        env_vars.update(clip_config)
        
        # Generate other service configurations
        other_configs = self._generate_other_services_config()
        env_vars.update(other_configs)
        
        # Generate adaptive service configurations
        adaptive_configs = self._generate_adaptive_services_config()
        env_vars.update(adaptive_configs)
        
        return env_vars
    
    def _generate_llm_provider_config(self) -> Dict[str, str]:
        """Generate LLM Provider (Ollama) configuration."""
        source_value = self.service_sources.get('LLM_PROVIDER_SOURCE', 'ollama-container-cpu')
        config = self.get_service_config('llm_provider', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)
        env_vars['OLLAMA_SCALE'] = str(scale)
        
        # Set endpoint with localhost host replacement
        endpoint = config.get('environment', {}).get('OLLAMA_ENDPOINT', 'http://ollama:11434')
        endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
        env_vars['OLLAMA_ENDPOINT'] = endpoint
        
        # Set GPU devices if specified
        gpu_devices = config.get('environment', {}).get('NVIDIA_VISIBLE_DEVICES')
        if gpu_devices:
            env_vars['OLLAMA_NVIDIA_VISIBLE_DEVICES'] = gpu_devices
        else:
            env_vars['OLLAMA_NVIDIA_VISIBLE_DEVICES'] = 'null'
            
        # Set deployment resources
        deploy_resources = config.get('deploy', {})
        if deploy_resources:
            env_vars['OLLAMA_DEPLOY_RESOURCES'] = str(deploy_resources)
        else:
            env_vars['OLLAMA_DEPLOY_RESOURCES'] = '~'
        
        return env_vars
    
    def _generate_comfyui_config(self) -> Dict[str, str]:
        """Generate ComfyUI configuration."""
        source_value = self.service_sources.get('COMFYUI_SOURCE', 'container-cpu')
        config = self.get_service_config('comfyui', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)
        env_vars['COMFYUI_SCALE'] = str(scale)
        
        # Set endpoint
        endpoint = config.get('environment', {}).get('COMFYUI_ENDPOINT', 'http://comfyui:18188')
        endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
        env_vars['COMFYUI_ENDPOINT'] = endpoint
        
        # Set deployment resources
        deploy_resources = config.get('deploy', {})
        if deploy_resources:
            env_vars['COMFYUI_DEPLOY_RESOURCES'] = str(deploy_resources)
        else:
            env_vars['COMFYUI_DEPLOY_RESOURCES'] = '~'
            
        # Set local ComfyUI flag
        is_local = config.get('environment', {}).get('IS_LOCAL_COMFYUI', 'false')
        env_vars['IS_LOCAL_COMFYUI'] = is_local
        
        return env_vars
    
    def _generate_weaviate_config(self) -> Dict[str, str]:
        """Generate Weaviate configuration."""
        source_value = self.service_sources.get('WEAVIATE_SOURCE', 'container')
        config = self.get_service_config('weaviate', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)
        env_vars['WEAVIATE_SCALE'] = str(scale)
        
        # Set URL
        weaviate_url = config.get('environment', {}).get('WEAVIATE_URL', 'http://weaviate:8080')
        weaviate_url = weaviate_url.replace('host.docker.internal', self.localhost_host)
        env_vars['WEAVIATE_URL'] = weaviate_url
        
        # Set Ollama endpoint for Weaviate (inherits from LLM provider)
        ollama_endpoint = self.service_sources.get('OLLAMA_ENDPOINT', 'http://ollama:11434')
        env_vars['WEAVIATE_OLLAMA_ENDPOINT'] = ollama_endpoint
        
        return env_vars
    
    def _generate_clip_config(self) -> Dict[str, str]:
        """Generate Multi2Vec CLIP configuration."""
        source_value = self.service_sources.get('MULTI2VEC_CLIP_SOURCE', 'container-cpu')
        config = self.get_service_config('multi2vec-clip', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)  
        env_vars['CLIP_SCALE'] = str(scale)
        
        # Set CUDA enable flag
        cuda_flag = config.get('environment', {}).get('ENABLE_CUDA', '0')
        env_vars['CLIP_ENABLE_CUDA'] = cuda_flag
        
        # Set deployment resources
        deploy_resources = config.get('deploy', {})
        if deploy_resources:
            env_vars['CLIP_DEPLOY_RESOURCES'] = str(deploy_resources)
        else:
            env_vars['CLIP_DEPLOY_RESOURCES'] = '~'
            
        return env_vars
    
    def _generate_other_services_config(self) -> Dict[str, str]:
        """Generate configuration for other services."""
        env_vars = {}
        
        # N8N configuration
        n8n_source = self.service_sources.get('N8N_SOURCE', 'container')
        n8n_config = self.get_service_config('n8n', n8n_source)
        
        # Check if N8N_SCALE was already set (e.g., by dependency manager)
        current_env = self.config_parser.parse_env_file()
        n8n_scale = current_env.get('N8N_SCALE', str(n8n_config.get('scale', 1)))
        
        env_vars['N8N_SCALE'] = n8n_scale
        env_vars['N8N_WORKER_SCALE'] = n8n_scale  # Worker follows main N8N scale
        env_vars['N8N_INIT_SCALE'] = n8n_scale    # Init follows main N8N scale
        
        # SearxNG configuration  
        searxng_source = self.service_sources.get('SEARXNG_SOURCE', 'container')
        searxng_config = self.get_service_config('searxng', searxng_source)
        env_vars['SEARXNG_SCALE'] = str(searxng_config.get('scale', 1))
        
        # Neo4j configuration
        neo4j_source = self.service_sources.get('NEO4J_GRAPH_DB_SOURCE', 'container')
        neo4j_config = self.get_service_config('neo4j-graph-db', neo4j_source)
        env_vars['NEO4J_SCALE'] = str(neo4j_config.get('scale', 1))
        
        # Set Neo4j URI
        neo4j_uri = neo4j_config.get('environment', {}).get('NEO4J_URI', 'bolt://neo4j-graph-db:7687')
        neo4j_uri = neo4j_uri.replace('host.docker.internal', self.localhost_host)
        env_vars['NEO4J_URI'] = neo4j_uri
        
        # Initialization service scales - conditional based on parent service sources
        
        # WEAVIATE_INIT_SCALE follows WEAVIATE_SCALE 
        weaviate_source = self.service_sources.get('WEAVIATE_SOURCE', 'container')
        if weaviate_source == 'disabled':
            env_vars['WEAVIATE_INIT_SCALE'] = '0'
        else:
            weaviate_config = self.get_service_config('weaviate', weaviate_source)
            env_vars['WEAVIATE_INIT_SCALE'] = str(weaviate_config.get('scale', 1))
        
        # OLLAMA_PULL_SCALE: 1 if LLM provider is container mode, 0 otherwise
        llm_source = self.service_sources.get('LLM_PROVIDER_SOURCE', 'ollama-container-cpu')
        if llm_source in ['ollama-container-cpu', 'ollama-container-gpu']:
            env_vars['OLLAMA_PULL_SCALE'] = '1'
        else:
            env_vars['OLLAMA_PULL_SCALE'] = '0'
            
        # COMFYUI_INIT_SCALE: 1 unless ComfyUI is disabled (init handles both local and container)
        comfyui_source = self.service_sources.get('COMFYUI_SOURCE', 'container-cpu')
        if comfyui_source == 'disabled':
            env_vars['COMFYUI_INIT_SCALE'] = '0'
        else:
            env_vars['COMFYUI_INIT_SCALE'] = '1'
        
        return env_vars
    
    def _generate_adaptive_services_config(self) -> Dict[str, str]:
        """Generate configuration for adaptive services."""
        env_vars = {}
        sources = self.config_parser.parse_service_sources()
        
        # Backend always enabled (no SOURCE check - always runs)
        env_vars['BACKEND_SCALE'] = '1'
        
        # Open WebUI - check SOURCE variable
        webui_source = sources.get('OPEN_WEB_UI_SOURCE', 'container')
        env_vars['OPEN_WEB_UI_SCALE'] = '0' if webui_source == 'disabled' else '1'
        
        # Local Deep Researcher - check SOURCE variable
        researcher_source = sources.get('LOCAL_DEEP_RESEARCHER_SOURCE', 'container')
        env_vars['LOCAL_DEEP_RESEARCHER_SCALE'] = '0' if researcher_source == 'disabled' else '1'
        
        return env_vars
    
    def update_env_file(self, env_vars: Dict[str, str], create_backup: bool = True) -> bool:
        """
        Update .env file with computed environment variables.
        Replicates the update_env_file() function from start.sh.
        
        Args:
            env_vars: Dictionary of environment variables to set
            create_backup: Whether to create backup before updating
            
        Returns:
            bool: True if successful
        """
        env_file_path = self.config_parser.env_file_path
        
        if not env_file_path.exists():
            print(f"❌ .env file not found: {env_file_path}")
            return False
        
        try:
            # Create backup if requested
            if create_backup:
                backup_path = self.config_parser.create_env_backup()
                print(f"📋 Created .env backup: {backup_path}")
            
            # Read current .env content
            with open(env_file_path, 'r') as f:
                content = f.read()
            
            updated_content = content
            
            # Update each environment variable
            for var_name, var_value in env_vars.items():
                # Use regex to find and replace the variable assignment
                pattern = rf'^{re.escape(var_name)}=.*$'
                replacement = f'{var_name}={var_value}'
                
                if re.search(pattern, updated_content, re.MULTILINE):
                    # Variable exists, replace it
                    updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
                else:
                    # Variable doesn't exist, append it
                    updated_content += f'\n{replacement}'
            
            # Write updated content back
            with open(env_file_path, 'w') as f:
                f.write(updated_content)
                
            print("✅ Updated .env file with computed service variables")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update .env file: {e}")
            return False
    
    def check_comfyui_local_models(self) -> None:
        """
        Check ComfyUI local models directory.
        Replicates the ComfyUI local models check from start.sh.
        """
        comfyui_source = self.service_sources.get('COMFYUI_SOURCE', 'container-cpu')
        is_local = comfyui_source == 'localhost'
        
        if is_local:
            from pathlib import Path
            
            # Get local models path from env
            env_vars = self.config_parser.parse_env_file()
            models_path = env_vars.get('COMFYUI_LOCAL_MODELS_PATH', '~/Documents/ComfyUI/models')
            
            # Expand user home directory
            models_path = Path(models_path).expanduser()
            
            if models_path.exists():
                print(f"  • ✅ ComfyUI local models found: {models_path}")
            else:
                print(f"  • ⚠️  ComfyUI local models directory not found: {models_path}")
                print("    Please ensure your local ComfyUI models are in the correct location")
    
    def generate_and_update_env(self, create_backup: bool = True) -> bool:
        """
        Generate service environment and update .env file.
        
        Args:
            create_backup: Whether to create backup before updating
            
        Returns:
            bool: True if successful
        """
        env_vars = self.generate_service_environment()
        
        if not env_vars:
            print("❌ Failed to generate service environment variables")
            return False
            
        return self.update_env_file(env_vars, create_backup)