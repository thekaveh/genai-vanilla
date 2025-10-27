"""
SOURCE override manager for command-line arguments.
Handles runtime overrides of SERVICE SOURCE configurations.
"""

from typing import Dict, Optional, List, Tuple
from pathlib import Path
import re

class SourceOverrideManager:
    """Manages command-line SOURCE overrides for services."""
    
    def __init__(self, config_parser):
        """
        Initialize the SOURCE override manager.
        
        Args:
            config_parser: ConfigParser instance for file operations
        """
        self.config_parser = config_parser
        self.applied_overrides = {}
        
        # Map CLI argument names to environment variable names
        self.source_mapping = {
            'llm_provider_source': 'LLM_PROVIDER_SOURCE',
            'comfyui_source': 'COMFYUI_SOURCE',
            'weaviate_source': 'WEAVIATE_SOURCE',
            'n8n_source': 'N8N_SOURCE',
            'searxng_source': 'SEARXNG_SOURCE',
            'jupyterhub_source': 'JUPYTERHUB_SOURCE',
            'stt_provider_source': 'STT_PROVIDER_SOURCE',
            'tts_provider_source': 'TTS_PROVIDER_SOURCE',
            'doc_processor_source': 'DOC_PROCESSOR_SOURCE',
        }
    
    def collect_overrides(self, **kwargs) -> Dict[str, str]:
        """
        Collect non-None SOURCE overrides from CLI arguments.
        
        Args:
            **kwargs: Keyword arguments from CLI (click options)
            
        Returns:
            dict: Mapping of environment variable names to override values
        """
        overrides = {}
        for cli_arg, env_var in self.source_mapping.items():
            value = kwargs.get(cli_arg)
            if value is not None:
                overrides[env_var] = value
        return overrides
    
    def apply_overrides(self, overrides: Dict[str, str]) -> bool:
        """
        Apply SOURCE overrides to .env file.
        
        Args:
            overrides: Dictionary of environment variables to override
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not overrides:
            return True
            
        print("\n🔄 Applying SOURCE overrides from command-line:")
        for env_var, value in overrides.items():
            print(f"  • {env_var} → {value}")
        
        # Update .env file with overrides
        if self.update_env_file(overrides):
            self.applied_overrides = overrides
            print("✅ SOURCE overrides applied successfully")
            return True
        
        return False
    
    def update_env_file(self, overrides: Dict[str, str]) -> bool:
        """
        Update SOURCE values in .env file using regex replacement.
        
        Args:
            overrides: Dictionary of environment variables to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        env_file_path = self.config_parser.env_file_path
        
        if not env_file_path.exists():
            print(f"❌ .env file not found: {env_file_path}")
            return False
        
        try:
            # Read current .env content
            with open(env_file_path, 'r') as f:
                content = f.read()
            
            updated_content = content
            
            # Update each environment variable using regex
            for var_name, var_value in overrides.items():
                pattern = rf'^{re.escape(var_name)}=.*$'
                replacement = f'{var_name}={var_value}'
                
                if re.search(pattern, updated_content, re.MULTILINE):
                    # Variable exists, replace it
                    updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
                else:
                    # Variable doesn't exist, append it (shouldn't happen with SOURCE vars)
                    print(f"⚠️  {var_name} not found in .env, appending...")
                    updated_content += f'\n{replacement}'
            
            # Write updated content back to file
            with open(env_file_path, 'w') as f:
                f.write(updated_content)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply SOURCE overrides: {e}")
            return False
    
    def show_override_summary(self):
        """Display summary of applied SOURCE overrides."""
        if self.applied_overrides:
            print("\n📋 Active SOURCE Overrides:")
            for var, value in self.applied_overrides.items():
                print(f"  • {var}: {value}")
        else:
            print("\n📋 No SOURCE overrides active (using .env defaults)")
    
    def get_applied_overrides(self) -> Dict[str, str]:
        """
        Get dictionary of applied overrides.
        
        Returns:
            dict: Currently applied SOURCE overrides
        """
        return self.applied_overrides.copy()
    
    def has_overrides(self) -> bool:
        """
        Check if any overrides are currently applied.
        
        Returns:
            bool: True if overrides are active, False otherwise
        """
        return bool(self.applied_overrides)