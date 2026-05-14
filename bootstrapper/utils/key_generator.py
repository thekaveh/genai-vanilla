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

    MINIO_CONSUMERS = ("COMFYUI", "BACKEND", "N8N", "JUPYTER", "DOCLING")

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

    def generate_litellm_master_key(self) -> str:
        """LiteLLM master key — must start with `sk-` per LiteLLM's contract."""
        return f"sk-{secrets.token_urlsafe(40)}"

    def generate_minio_root_password(self) -> str:
        """MinIO root password — 32-char URL-safe random."""
        return secrets.token_urlsafe(24)

    def generate_minio_access_key(self) -> str:
        """MinIO service-account access key — 20-char uppercase alphanumeric (S3 convention)."""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(20))

    def generate_minio_secret_key(self) -> str:
        """MinIO service-account secret key — 40-char URL-safe random."""
        return secrets.token_urlsafe(30)

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
                pass  # silent backup
            
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
            return True

        new_key = self.generate_n8n_encryption_key()
        if self.update_env_key('N8N_ENCRYPTION_KEY', new_key):
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
            return True

        new_secret = self.generate_searxng_secret()
        if self.update_env_key('SEARXNG_SECRET', new_secret):
            return True
        else:
            return False
    
    def generate_and_update_litellm_master_key(self, force: bool = False) -> bool:
        """Generate LITELLM_MASTER_KEY when absent. Idempotent: never overwrites
        an existing key (preserves virtual-key + spend history) unless force=True.
        """
        current_value = self.get_current_env_value('LITELLM_MASTER_KEY')
        if not force and current_value:
            return True
        new_key = self.generate_litellm_master_key()
        return self.update_env_key('LITELLM_MASTER_KEY', new_key)

    def generate_hermes_api_key(self) -> str:
        """Hermes API server bearer key. Hermes requires >= 8 chars but doesn't
        prescribe a format; a URL-safe 32-byte token is consistent with
        LITELLM_MASTER_KEY's strength (no `sk-` prefix — Hermes has no contract
        around it).
        """
        return secrets.token_urlsafe(32)

    def generate_and_update_hermes_api_key(self, force: bool = False) -> bool:
        """Generate HERMES_API_KEY when absent. Idempotent: existing keys are
        preserved so already-running Hermes sessions / saved Open-WebUI client
        config keep working across re-runs.
        """
        current_value = self.get_current_env_value('HERMES_API_KEY')
        if not force and current_value:
            return True
        new_key = self.generate_hermes_api_key()
        return self.update_env_key('HERMES_API_KEY', new_key)

    def generate_webui_secret_key(self) -> str:
        """Open WebUI JWT/session signing key. Used by Open WebUI itself
        AND by ``services/open-webui/init/scripts/register-{tools,functions}.py``
        to sign admin-token JWTs via ``jwt.encode(..., algorithm="HS256")``.
        PyJWT 2.10+ logs ``InsecureKeyLengthWarning`` for keys shorter
        than 32 bytes on HS256 (RFC 7518 Section 3.2), so we emit a
        URL-safe 32-byte token — same posture as LITELLM_MASTER_KEY /
        HERMES_API_KEY.
        """
        return secrets.token_urlsafe(32)

    def generate_and_update_webui_secret_key(self, force: bool = False) -> bool:
        """Generate OPEN_WEB_UI_SECRET_KEY when absent OR when the shipped
        placeholder ``"secret"`` (6 bytes literally) is still in place.
        Idempotent for any other user-supplied value: hand-edits stick.
        Rotating mid-run signs everyone out of Open WebUI, so we only
        upgrade the placeholder, never a real key.
        """
        current_value = self.get_current_env_value('OPEN_WEB_UI_SECRET_KEY')
        if not force and current_value and current_value != 'secret':
            return True
        new_key = self.generate_webui_secret_key()
        return self.update_env_key('OPEN_WEB_UI_SECRET_KEY', new_key)

    def generate_and_update_minio_root_password(self, force: bool = False) -> bool:
        """Generate MINIO_ROOT_PASSWORD when absent. Hand-edits stick unless force=True."""
        current_value = self.get_current_env_value('MINIO_ROOT_PASSWORD')
        if not force and current_value:
            return True
        new_value = self.generate_minio_root_password()
        return self.update_env_key('MINIO_ROOT_PASSWORD', new_value)

    def generate_and_update_minio_consumer_keys(self, force: bool = False) -> Dict[str, bool]:
        """Generate MINIO_<NAME>_ACCESS_KEY + MINIO_<NAME>_SECRET_KEY for every consumer in
        MINIO_CONSUMERS, only when blank. Returns a per-variable success map.
        """
        results: Dict[str, bool] = {}
        for consumer in self.MINIO_CONSUMERS:
            access_var = f'MINIO_{consumer}_ACCESS_KEY'
            secret_var = f'MINIO_{consumer}_SECRET_KEY'

            if force or not self.get_current_env_value(access_var):
                results[access_var] = self.update_env_key(access_var, self.generate_minio_access_key())
            else:
                results[access_var] = True

            if force or not self.get_current_env_value(secret_var):
                results[secret_var] = self.update_env_key(secret_var, self.generate_minio_secret_key())
            else:
                results[secret_var] = True

        return results

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

        # LiteLLM master key — never force-regenerate (would invalidate virtual keys
        # and orphan spend history). Only generate when absent.
        results['LITELLM_MASTER_KEY'] = self.generate_and_update_litellm_master_key(force=False)

        # Hermes API bearer key — same posture as LITELLM_MASTER_KEY: only
        # generate when absent. The LiteLLM model_list's hermes-agent row
        # references it via os.environ/HERMES_API_KEY, so rotating it
        # without restarting the LiteLLM container would break routing.
        results['HERMES_API_KEY'] = self.generate_and_update_hermes_api_key(force=False)

        # Open WebUI JWT/session signing key. Upgrades the shipped
        # ``"secret"`` placeholder to a real 32-byte token; preserves
        # any other user-supplied value so logged-in sessions survive
        # restarts. PyJWT 2.10+ logs InsecureKeyLengthWarning for keys
        # < 32 bytes on HS256, which the open-webui-init scripts trip
        # every launch with the placeholder.
        results['OPEN_WEB_UI_SECRET_KEY'] = self.generate_and_update_webui_secret_key(force=False)

        # MinIO root password — never force-regenerate (would lock out console + break
        # provisioning). Only generate when absent.
        results['MINIO_ROOT_PASSWORD'] = self.generate_and_update_minio_root_password(force=False)

        # MinIO per-consumer service-account credentials — only generate when absent.
        # Rotating these means re-running minio-init, which is a deliberate operator action.
        results.update(self.generate_and_update_minio_consumer_keys(force=False))

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