"""
Configuration parsing for YAML service configs and .env files.

Python implementation of configuration parsing from start.sh and stop.sh.
"""

import os
import re
import yaml
from typing import Dict, Optional, Any
from pathlib import Path


class ConfigParser:
    """Configuration parser for GenAI Stack."""
    
    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize the config parser.

        Args:
            root_dir: Root directory containing .env and config files.
                     If None, uses the parent of the bootstrapper directory.
        """
        if root_dir is None:
            # Default to parent directory of bootstrapper
            self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir)

        self.service_config_path = self.root_dir / "bootstrapper" / "service-configs.yml"

        # .env.example always lives in repository root
        self.env_example_path = self.root_dir / ".env.example"

        # .env path can be customized via GENAI_ENV_FILE environment variable
        self.env_file_path = self._resolve_env_file_path()

        self.service_sources = {}

    def _resolve_env_file_path(self) -> Path:
        """
        Resolve .env file path from GENAI_ENV_FILE environment variable.
        Falls back to default .env in repository root if not set.

        This allows users to specify custom .env file locations, useful for:
        - CI/CD pipelines with secret injection
        - Multiple deployments with different configurations
        - Parent projects managing infrastructure config centrally

        Returns:
            Path: Resolved .env file path
        """
        custom_env_path = os.environ.get('GENAI_ENV_FILE', '').strip()

        if custom_env_path:
            # User specified custom path - resolve and expand
            resolved_path = Path(custom_env_path).expanduser().resolve()
            return resolved_path

        # Default: .env in repository root
        return self.root_dir / ".env"

    def get_env_file_location(self) -> str:
        """
        Get human-readable env file location for display.

        Returns:
            str: Path to the env file being used
        """
        return str(self.env_file_path)

    def is_using_custom_env_file(self) -> bool:
        """
        Check if using a custom env file path via GENAI_ENV_FILE.

        Returns:
            bool: True if GENAI_ENV_FILE is set
        """
        return bool(os.environ.get('GENAI_ENV_FILE'))
        
    def load_yaml_config(self) -> Dict[str, Any]:
        """
        Load the service configuration YAML file.
        
        Returns:
            dict: Loaded YAML configuration
            
        Raises:
            FileNotFoundError: If service-configs.yml not found
            yaml.YAMLError: If YAML parsing fails
        """
        if not self.service_config_path.exists():
            raise FileNotFoundError(f"Service configuration file not found: {self.service_config_path}")
            
        with open(self.service_config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def parse_env_file(self) -> Dict[str, str]:
        """
        Parse .env file for all variables.
        
        Returns:
            dict: Dictionary of environment variables from .env file
        """
        env_vars = {}
        
        if not self.env_file_path.exists():
            return env_vars
            
        with open(self.env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Split on first = only
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove any inline comments
                    if '#' in value:
                        value = value.split('#')[0]
                    # Clean up the value
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value
                    
        return env_vars
    
    def parse_service_sources(self) -> Dict[str, str]:
        """
        Parse service SOURCE configurations from .env file.
        Replicates the parse_service_sources() function from start.sh.
        
        Returns:
            dict: Dictionary mapping SOURCE variable names to their values
        """
        # Start with only non-customizable services  
        # Backend is always 'container' and not exposed in .env.example
        source_mapping = {
            'BACKEND_SOURCE': 'container',
        }
            
        # Parse SOURCE variables from .env file using the same regex as start.sh
        if self.env_file_path.exists():
            with open(self.env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Use the same regex pattern as start.sh: ^([A-Z0-9_]+_SOURCE)=([^#]*)
                    match = re.match(r'^([A-Z0-9_]+_SOURCE)=([^#]*)', line)
                    if match:
                        var_name = match.group(1)
                        var_value = match.group(2).strip().strip('"').strip("'")
                        source_mapping[var_name] = var_value
                        
        self.service_sources = source_mapping
        return source_mapping
    
    def get_service_source(self, service_var: str) -> str:
        """
        Get the SOURCE value for a specific service.
        
        Args:
            service_var: The SOURCE variable name (e.g. 'LLM_PROVIDER_SOURCE')
            
        Returns:
            str: The SOURCE value for the service
        """
        if not self.service_sources:
            self.parse_service_sources()
        return self.service_sources.get(service_var, '')
    
    def get_project_name(self) -> str:
        """
        Get the project name from .env file.
        
        Returns:
            str: Project name, defaults to 'genai' if not found
        """
        env_vars = self.parse_env_file()
        return env_vars.get('PROJECT_NAME', 'genai')
    
    def env_file_exists(self) -> bool:
        """
        Check if .env file exists.
        
        Returns:
            bool: True if .env file exists
        """
        return self.env_file_path.exists()
    
    def get_env_file_timestamp(self) -> Optional[str]:
        """
        Get the .env file modification timestamp.
        
        Returns:
            str: Formatted timestamp string, or None if file doesn't exist
        """
        if not self.env_file_exists():
            return None
            
        import datetime
        mtime = self.env_file_path.stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    
    def create_env_backup(self) -> str:
        """
        Create a backup of the .env file with timestamp.
        Works with both default and custom .env file paths.
        Backup is created in the same directory as the .env file.

        Returns:
            str: Path to the backup file

        Raises:
            FileNotFoundError: If .env file doesn't exist
        """
        if not self.env_file_exists():
            raise FileNotFoundError("Cannot backup .env file - it doesn't exist")

        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        # Create backup in the same directory as the .env file
        # This ensures backups work correctly with custom paths
        backup_filename = f"{self.env_file_path.name}.backup.{timestamp}"
        backup_path = self.env_file_path.parent / backup_filename

        import shutil
        shutil.copy2(self.env_file_path, backup_path)
        return str(backup_path)