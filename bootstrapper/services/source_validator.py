"""
SOURCE configuration validation against service-configs.yml.

Python implementation of validate_source_values() function from start.sh.
"""

from typing import Dict, List, Optional, Set
from core.config_parser import ConfigParser


class SourceValidator:
    """Validates SERVICE SOURCE configurations against YAML definitions."""
    
    def __init__(self, config_parser: Optional[ConfigParser] = None):
        """
        Initialize source validator.
        
        Args:
            config_parser: ConfigParser instance (creates new one if None)
        """
        self.config_parser = config_parser or ConfigParser()
        self.yaml_config = None
        self.validation_errors = []
    
    def load_yaml_config(self) -> bool:
        """
        Load the YAML configuration for validation.
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            self.yaml_config = self.config_parser.load_yaml_config()
            return True
        except Exception as e:
            self.validation_errors.append(f"Failed to load YAML config: {e}")
            return False
    
    def get_valid_sources_for_service(self, service_key: str) -> Set[str]:
        """
        Get valid SOURCE values for a specific service.
        
        Args:
            service_key: Service key in YAML config (e.g., "llm_provider", "comfyui")
            
        Returns:
            set: Set of valid SOURCE values for the service
        """
        if not self.yaml_config:
            return set()
            
        source_configurable = self.yaml_config.get('source_configurable', {})
        service_config = source_configurable.get(service_key, {})
        
        return set(service_config.keys())
    
    def get_service_mapping_from_yaml(self) -> Dict[str, str]:
        """
        Build service mapping dynamically from YAML configuration.
        Maps SOURCE variable names to service keys in YAML.
        
        Returns:
            dict: Mapping of SOURCE variables to YAML service keys
        """
        if not self.yaml_config:
            return {}
            
        service_mapping = {}
        
        # Get source_configurable services
        source_configurable = self.yaml_config.get('source_configurable', {})
        for service_key in source_configurable.keys():
            # Convert service key to SOURCE variable name
            # e.g., 'llm_provider' -> 'LLM_PROVIDER_SOURCE'
            source_var = service_key.upper().replace('-', '_') + '_SOURCE'
            service_mapping[source_var] = service_key
            
        # Get fixed_services (services that only have one configuration)
        fixed_services = self.yaml_config.get('fixed_services', {})
        for service_key in fixed_services.keys():
            source_var = service_key.upper().replace('-', '_') + '_SOURCE'
            service_mapping[source_var] = service_key
            
        return service_mapping
        
    def get_adaptive_services_from_yaml(self) -> Set[str]:
        """
        Get adaptive services from YAML configuration.
        
        Returns:
            set: Set of adaptive service SOURCE variable names
        """
        if not self.yaml_config:
            return set()
            
        adaptive_services = set()
        adaptive_config = self.yaml_config.get('adaptive_services', {})
        
        for service_key in adaptive_config.keys():
            source_var = service_key.upper().replace('-', '_') + '_SOURCE'
            adaptive_services.add(source_var)
            
        return adaptive_services
    
    def validate_source_value(self, service_var: str, source_value: str) -> bool:
        """
        Validate a single SOURCE value against YAML configuration.
        
        Args:
            service_var: SOURCE variable name (e.g., "LLM_PROVIDER_SOURCE")
            source_value: SOURCE value to validate
            
        Returns:
            bool: True if valid
        """
        # Clear validation errors for clean state
        self.validation_errors = []
        
        # Get service mappings dynamically from YAML
        service_mapping = self.get_service_mapping_from_yaml()
        adaptive_services = self.get_adaptive_services_from_yaml()
        
        if service_var in adaptive_services:
            # Adaptive services only support 'container' source (currently only backend)
            if source_value != 'container':
                self.validation_errors.append(
                    f"❌ {service_var}='{source_value}' is invalid. "
                    f"Adaptive services only support 'container'"
                )
                return False
            return True
            
        service_key = service_mapping.get(service_var)
        if not service_key:
            self.validation_errors.append(f"❌ Unknown SOURCE variable: {service_var}")
            return False
            
        valid_sources = self.get_valid_sources_for_service(service_key)
        if not valid_sources:
            self.validation_errors.append(
                f"❌ No valid sources found for service: {service_key}"
            )
            return False
            
        if source_value not in valid_sources:
            valid_list = ', '.join(sorted(valid_sources))
            self.validation_errors.append(
                f"❌ {service_var}='{source_value}' is invalid. "
                f"Valid options: {valid_list}"
            )
            return False
            
        return True
        
    def validate_scale_values(self) -> bool:
        """
        Validate all scale values from .env file.
        
        Returns:
            bool: True if all scale values are valid
        """
        env_vars = self.config_parser.parse_env_file()
        all_valid = True
        
        # Get all scale variables from .env
        scale_vars = {k: v for k, v in env_vars.items() if k.endswith('_SCALE')}
        
        for scale_var, scale_value in scale_vars.items():
            if not scale_value.strip():
                continue
                
            try:
                scale_int = int(scale_value)
                
                # Validate scale is 0 or 1 (or positive integer)
                if scale_int < 0:
                    self.validation_errors.append(
                        f"❌ {scale_var}='{scale_value}' is invalid. Scale must be 0 or positive integer"
                    )
                    all_valid = False
                elif scale_int > 1:
                    # Warn about scale > 1 (not common in this stack)
                    print(f"⚠️  {scale_var}='{scale_value}' - High scale values may cause resource issues")
                    
            except ValueError:
                self.validation_errors.append(
                    f"❌ {scale_var}='{scale_value}' is invalid. Scale must be a number"
                )
                all_valid = False
        
        return all_valid
    
    def validate_all_sources(self) -> bool:
        """
        Validate all SOURCE configurations from .env file.
        Replicates the validate_source_values() function from start.sh.
        
        Returns:
            bool: True if all sources are valid
        """
        self.validation_errors = []
        
        if not self.load_yaml_config():
            return False
            
        # Get all service sources from .env
        service_sources = self.config_parser.parse_service_sources()
        
        if not service_sources:
            self.validation_errors.append("❌ No SOURCE configurations found")
            return False
        
        all_valid = True
        
        for service_var, source_value in service_sources.items():
            if not source_value:  # Skip empty values
                continue
                
            if not self.validate_source_value(service_var, source_value):
                all_valid = False
        
        return all_valid
    
    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation errors.
        
        Returns:
            list: List of error messages
        """
        return self.validation_errors.copy()
    
    def print_validation_results(self) -> None:
        """Print validation results to console."""
        if self.validation_errors:
            print("❌ SOURCE validation failed:")
            for error in self.validation_errors:
                print(f"   {error}")
            print("\n💡 Please check your .env file and fix the invalid SOURCE values.")
            print("   Valid SOURCE options are defined in bootstrapper/service-configs.yml")
        else:
            print("✅ All SOURCE values are valid")
    
    def get_service_source_options(self, service_var: str) -> List[str]:
        """
        Get valid SOURCE options for a specific service variable.
        
        Args:
            service_var: SOURCE variable name
            
        Returns:
            list: List of valid SOURCE values
        """
        if not self.yaml_config:
            self.load_yaml_config()
            
        # Get mappings dynamically from YAML
        service_mapping = self.get_service_mapping_from_yaml()
        adaptive_services = self.get_adaptive_services_from_yaml()
        
        if service_var in adaptive_services:
            return ['container']
            
        service_key = service_mapping.get(service_var)
        if not service_key:
            return []
            
        valid_sources = self.get_valid_sources_for_service(service_key)
        return sorted(list(valid_sources))
    
    def suggest_valid_source(self, service_var: str, invalid_source: str) -> Optional[str]:
        """
        Suggest a valid SOURCE value for an invalid one.
        
        Args:
            service_var: SOURCE variable name
            invalid_source: The invalid source value
            
        Returns:
            str: Suggested valid source, or None if no suggestion
        """
        valid_options = self.get_service_source_options(service_var)
        
        if not valid_options:
            return None
            
        # Simple suggestion logic - return first valid option
        # Could be enhanced with fuzzy matching in the future
        return valid_options[0] if valid_options else None