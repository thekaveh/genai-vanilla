"""
Service dependency management based on service-configs.yml.

Reads service dependencies from YAML configuration and enforces them
during service startup, ensuring required dependencies are available.
"""

from typing import Dict, List, Set, Optional, Tuple
from core.config_parser import ConfigParser


class DependencyManager:
    """Manages service dependencies based on YAML configuration."""
    
    def __init__(self, config_parser: Optional[ConfigParser] = None):
        """
        Initialize dependency manager.
        
        Args:
            config_parser: ConfigParser instance (creates new one if None)
        """
        self.config_parser = config_parser or ConfigParser()
        self.yaml_config = None
        self.dependency_violations = []
        
    def load_yaml_config(self) -> bool:
        """
        Load the YAML configuration for dependency checking.
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            self.yaml_config = self.config_parser.load_yaml_config()
            return True
        except Exception as e:
            print(f"❌ Failed to load service-configs.yml: {e}")
            return False
            
    def get_service_dependencies(self) -> Dict[str, Dict]:
        """
        Get service dependencies from YAML configuration.
        
        Returns:
            dict: Service dependencies structure from YAML
        """
        if not self.yaml_config:
            return {}
            
        return self.yaml_config.get('service_dependencies', {})
        
    def get_service_scale(self, service_name: str) -> int:
        """
        Get the current scale setting for a service from environment.
        
        Args:
            service_name: Name of the service
            
        Returns:
            int: Scale value (0 = disabled, 1+ = enabled)
        """
        env_vars = self.config_parser.parse_env_file()
        
        # Map service names to their scale environment variables
        scale_var_mapping = {
            'n8n': 'N8N_SCALE',
            'n8n-worker': 'N8N_SCALE',  # n8n-worker uses same scale as n8n
            'weaviate': 'WEAVIATE_SCALE',
            'neo4j-graph-db': 'NEO4J_SCALE',
            'searxng': 'SEARXNG_SCALE',
            'backend': 'BACKEND_SCALE',
            'jupyterhub': 'JUPYTERHUB_SCALE',
        }
        
        scale_var = scale_var_mapping.get(service_name)
        if not scale_var:
            # If no explicit scale var, check if service is disabled via SOURCE
            source_vars = self.config_parser.parse_service_sources()
            
            # Map service names to SOURCE variables
            source_var_mapping = {
                'weaviate': 'WEAVIATE_SOURCE',
                'n8n': 'N8N_SOURCE',
                'neo4j-graph-db': 'NEO4J_GRAPH_DB_SOURCE',
                'searxng': 'SEARXNG_SOURCE',
                'backend': 'BACKEND_SOURCE',
                'jupyterhub': 'JUPYTERHUB_SOURCE',
            }
            
            source_var = source_var_mapping.get(service_name)
            if source_var and source_vars.get(source_var) == 'disabled':
                return 0
            return 1  # Assume enabled if no explicit scale or source
            
        return int(env_vars.get(scale_var, '1'))
        
    def check_service_dependencies(self) -> bool:
        """
        Check all service dependencies and identify violations.
        
        Returns:
            bool: True if all dependencies are satisfied
        """
        self.dependency_violations = []
        
        if not self.load_yaml_config():
            return False
            
        dependencies = self.get_service_dependencies()
        if not dependencies:
            return True  # No dependencies defined
            
        all_satisfied = True
        
        for service_name, dep_config in dependencies.items():
            service_scale = self.get_service_scale(service_name)
            
            # Only check dependencies for enabled services
            if service_scale == 0:
                continue
                
            # Check required dependencies
            required_deps = dep_config.get('requires', [])
            for required_service in required_deps:
                required_scale = self.get_service_scale(required_service)
                
                if required_scale == 0:
                    # Required dependency is disabled
                    error_msg = dep_config.get('error_message', 
                        f"{service_name} requires {required_service} but it's disabled")
                    
                    self.dependency_violations.append({
                        'service': service_name,
                        'required_service': required_service,
                        'error_message': error_msg
                    })
                    all_satisfied = False
                    
            # Log info about optional dependencies
            optional_deps = dep_config.get('optional', [])
            if optional_deps:
                available_optional = []
                for optional_service in optional_deps:
                    if self.get_service_scale(optional_service) > 0:
                        available_optional.append(optional_service)
                        
                if available_optional:
                    info_msg = dep_config.get('info_message', 
                        f"{service_name} will connect to: {', '.join(available_optional)}")
                    print(f"ℹ️  {info_msg}")
                    
        return all_satisfied
        
    def auto_resolve_dependency_violations(self) -> List[str]:
        """
        Automatically resolve dependency violations by disabling dependent services.
        
        Returns:
            list: List of services that were auto-disabled
        """
        disabled_services = []
        
        for violation in self.dependency_violations:
            service_name = violation['service']
            
            # Handle N8N services which need multiple scale variables updated
            if service_name in ['n8n', 'n8n-worker']:
                # When disabling n8n, also disable worker and init services
                scale_vars_to_update = ['N8N_SCALE']
                # Note: N8N_WORKER_SCALE and N8N_INIT_SCALE are set by service_config based on N8N_SCALE
                
                env_file_path = self.config_parser.env_file_path
                try:
                    with open(env_file_path, 'r') as f:
                        content = f.read()
                    
                    updated_content = content
                    
                    # Update all related N8N scale variables to 0
                    for scale_var in scale_vars_to_update:
                        import re
                        pattern = rf'^{scale_var}=.*$'
                        replacement = f'{scale_var}=0'
                        updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
                    
                    with open(env_file_path, 'w') as f:
                        f.write(updated_content)
                    
                    disabled_services.append(service_name)
                    
                except Exception as e:
                    print(f"❌ Failed to disable {service_name}: {e}")
            
            else:
                # Handle other services with single scale variable
                scale_var_mapping = {
                    'backend': 'BACKEND_SCALE',
                    'weaviate': 'WEAVIATE_SCALE',
                    'neo4j-graph-db': 'NEO4J_SCALE',
                    'searxng': 'SEARXNG_SCALE',
                    'jupyterhub': 'JUPYTERHUB_SCALE',
                }
                
                scale_var = scale_var_mapping.get(service_name)
                if scale_var:
                    env_file_path = self.config_parser.env_file_path
                    try:
                        with open(env_file_path, 'r') as f:
                            content = f.read()
                        
                        # Update scale to 0
                        import re
                        pattern = rf'^{scale_var}=.*$'
                        replacement = f'{scale_var}=0'
                        updated_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                        
                        with open(env_file_path, 'w') as f:
                            f.write(updated_content)
                        
                        disabled_services.append(service_name)
                        
                    except Exception as e:
                        print(f"❌ Failed to disable {service_name}: {e}")
                    
        return disabled_services
        
    def get_dependency_violations(self) -> List[Dict]:
        """
        Get list of dependency violations.
        
        Returns:
            list: List of violation dictionaries
        """
        return self.dependency_violations.copy()
        
    def print_dependency_results(self) -> None:
        """Print dependency check results to console."""
        if self.dependency_violations:
            print("❌ Service dependency violations found:")
            for violation in self.dependency_violations:
                print(f"   {violation['error_message']}")
        else:
            print("✅ All service dependencies satisfied")
            
    def get_dependency_info(self, service_name: str) -> Dict:
        """
        Get dependency information for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            dict: Dependency information (requires, optional, messages)
        """
        dependencies = self.get_service_dependencies()
        return dependencies.get(service_name, {})