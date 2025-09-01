"""
Encryption key generation utilities for GenAI Stack services.

Generates N8N_ENCRYPTION_KEY and SEARXNG_SECRET for secure operation.
"""

import os
import secrets
import re
from pathlib import Path
from typing import Optional, Dict


class KeyGenerator:
    """Generates and manages encryption keys for GenAI Stack services."""
    
    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize key generator.
        
        Args:
            root_dir: Root directory containing .env file
        """
        if root_dir is None:
            # Default to parent directory of bootstrapper
            self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir)
            
        self.env_file_path = self.root_dir / ".env"
    
    def generate_n8n_encryption_key(self) -> str:
        """
        Generate N8N encryption key (48 character hex string).
        Equivalent to: openssl rand -hex 24
        
        Returns:
            str: 48-character hex string
        """
        return secrets.token_hex(24)
    
    def generate_searxng_secret(self) -> str:
        """
        Generate SearxNG secret key (64 character hex string).
        Equivalent to: openssl rand -hex 32
        
        Returns:
            str: 64-character hex string
        """
        return secrets.token_hex(32)
    
    def get_current_env_value(self, key_name: str) -> Optional[str]:
        """
        Get current value of an environment variable from .env file.
        
        Args:
            key_name: Name of the environment variable
            
        Returns:
            str: Current value, or None if not found/empty
        """
        if not self.env_file_path.exists():
            return None
            
        try:
            with open(self.env_file_path, 'r') as f:
                content = f.read()
            
            # Look for line like "KEY_NAME=value"
            pattern = rf'^{re.escape(key_name)}=(.*)$'
            match = re.search(pattern, content, re.MULTILINE)
            
            if match:
                value = match.group(1).strip().strip('"').strip("'")
                return value if value else None
            
        except Exception:
            pass
            
        return None
    
    def update_env_key(self, key_name: str, key_value: str, create_backup: bool = False) -> bool:
        """
        Update or add a key in the .env file.
        
        Args:
            key_name: Name of the environment variable
            key_value: Value to set
            create_backup: Whether to create a backup before modifying
            
        Returns:
            bool: True if successful
        """
        if not self.env_file_path.exists():
            print(f"❌ .env file not found: {self.env_file_path}")
            return False
        
        try:
            # Create backup if requested
            if create_backup:
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                backup_path = self.root_dir / f".env.backup.{timestamp}"
                import shutil
                shutil.copy2(self.env_file_path, backup_path)
                print(f"  • Created .env backup: {backup_path}")
            
            # Read current content
            with open(self.env_file_path, 'r') as f:
                content = f.read()
            
            # Check if key already exists
            pattern = rf'^{re.escape(key_name)}=.*$'
            if re.search(pattern, content, re.MULTILINE):
                # Replace existing key
                replacement = f'{key_name}={key_value}'
                updated_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                # Add new key at the end
                updated_content = content
                if not content.endswith('\n'):
                    updated_content += '\n'
                updated_content += f'{key_name}={key_value}\n'
            
            # Write updated content back
            with open(self.env_file_path, 'w') as f:
                f.write(updated_content)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to update {key_name} in .env file: {e}")
            return False
    
    def generate_and_update_n8n_key(self, force: bool = False) -> bool:
        """
        Generate and update N8N_ENCRYPTION_KEY in .env file.
        
        Args:
            force: Generate new key even if one already exists
            
        Returns:
            bool: True if successful
        """
        current_value = self.get_current_env_value('N8N_ENCRYPTION_KEY')
        
        if not force and current_value:
            print(f"  • N8N encryption key already exists: {current_value[:8]}...")
            return True
        
        print("  • Generating n8n encryption key...")
        new_key = self.generate_n8n_encryption_key()
        
        if self.update_env_key('N8N_ENCRYPTION_KEY', new_key):
            print("  • n8n encryption key generated successfully")
            return True
        else:
            return False
    
    def generate_and_update_searxng_secret(self, force: bool = False) -> bool:
        """
        Generate and update SEARXNG_SECRET in .env file.
        
        Args:
            force: Generate new key even if one already exists
            
        Returns:
            bool: True if successful
        """
        current_value = self.get_current_env_value('SEARXNG_SECRET')
        
        if not force and current_value:
            print(f"  • SearxNG secret already exists: {current_value[:8]}...")
            return True
        
        print("  • Generating SearxNG secret key...")
        new_secret = self.generate_searxng_secret()
        
        if self.update_env_key('SEARXNG_SECRET', new_secret):
            print("  • SearxNG secret key generated successfully")
            return True
        else:
            return False
    
    def generate_missing_keys(self, force_regenerate: bool = False) -> Dict[str, bool]:
        """
        Generate any missing encryption keys.
        
        Args:
            force_regenerate: Force regeneration of existing keys
            
        Returns:
            dict: Dictionary with key names and success status
        """
        results = {}
        
        # Generate N8N encryption key
        results['N8N_ENCRYPTION_KEY'] = self.generate_and_update_n8n_key(force=force_regenerate)
        
        # Generate SearxNG secret
        results['SEARXNG_SECRET'] = self.generate_and_update_searxng_secret(force=force_regenerate)
        
        return results
    
    def validate_keys(self) -> Dict[str, bool]:
        """
        Validate that all required encryption keys are present and valid.
        
        Returns:
            dict: Dictionary with key names and validation status
        """
        results = {}
        
        # Validate N8N encryption key (should be 48 characters)
        n8n_key = self.get_current_env_value('N8N_ENCRYPTION_KEY')
        results['N8N_ENCRYPTION_KEY'] = bool(n8n_key and len(n8n_key) == 48)
        
        # Validate SearxNG secret (should be 64 characters)
        searxng_secret = self.get_current_env_value('SEARXNG_SECRET')
        results['SEARXNG_SECRET'] = bool(searxng_secret and len(searxng_secret) == 64)
        
        return results