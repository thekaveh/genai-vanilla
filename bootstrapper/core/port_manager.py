"""
Port management utilities for validating and updating service ports.

Python implementation of port functions from start.sh.
"""

import socket
import re
from typing import Optional, Dict, List
from pathlib import Path
from core.config_parser import ConfigParser


class PortManager:
    """Manages port validation and assignment for GenAI Stack services."""
    
    # Port mapping based on start.sh update_port() function
    PORT_MAPPING = {
        'SUPABASE_DB_PORT': 0,        # Base port + 0
        'REDIS_PORT': 1,              # Base port + 1
        'KONG_HTTP_PORT': 2,          # Base port + 2
        'KONG_HTTPS_PORT': 3,         # Base port + 3
        'SUPABASE_META_PORT': 4,      # Base port + 4
        'SUPABASE_STORAGE_PORT': 5,   # Base port + 5
        'SUPABASE_AUTH_PORT': 6,      # Base port + 6
        'SUPABASE_API_PORT': 7,       # Base port + 7
        'SUPABASE_REALTIME_PORT': 8,  # Base port + 8
        'SUPABASE_STUDIO_PORT': 9,    # Base port + 9
        'GRAPH_DB_PORT': 10,          # Base port + 10
        'GRAPH_DB_DASHBOARD_PORT': 11, # Base port + 11
        'LLM_PROVIDER_PORT': 12,      # Base port + 12
        'LOCAL_DEEP_RESEARCHER_PORT': 13, # Base port + 13
        'SEARXNG_PORT': 14,           # Base port + 14
        'OPEN_WEB_UI_PORT': 15,       # Base port + 15
        'BACKEND_PORT': 16,           # Base port + 16
        'N8N_PORT': 17,               # Base port + 17
        'COMFYUI_PORT': 18,           # Base port + 18
        'WEAVIATE_PORT': 19,          # Base port + 19
        'WEAVIATE_GRPC_PORT': 20,     # Base port + 20
        'DOC_PROCESSOR_PORT': 21,     # Base port + 21
        'STT_PROVIDER_PORT': 22,      # Base port + 22
        'TTS_PROVIDER_PORT': 23,      # Base port + 23
        'JUPYTERHUB_PORT': 48,        # Base port + 48
    }
    
    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize port manager.
        
        Args:
            root_dir: Root directory containing .env file
        """
        if root_dir is None:
            # Default to parent directory of bootstrapper
            self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir)
            
        self.config_parser = ConfigParser(str(self.root_dir))
        
    def validate_base_port(self, port: int) -> bool:
        """
        Validate that a base port is in valid range.
        
        Args:
            port: Base port number to validate
            
        Returns:
            bool: True if port is valid (1024-65535)
        """
        return 1024 <= port <= 65535 - max(self.PORT_MAPPING.values())
    
    def check_port_availability(self, port: int) -> bool:
        """
        Check if a specific port is available.
        
        Args:
            port: Port number to check
            
        Returns:
            bool: True if port is available
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return True  # Assume available on error
    
    def check_port_range_availability(self, base_port: int) -> List[int]:
        """
        Check availability of all ports in the range starting from base_port.
        
        Args:
            base_port: Starting port number
            
        Returns:
            list: List of ports that are in use
        """
        used_ports = []
        
        for port_var, offset in self.PORT_MAPPING.items():
            port = base_port + offset
            if not self.check_port_availability(port):
                used_ports.append(port)
                
        return used_ports
    
    def calculate_port_assignments(self, base_port: int) -> Dict[str, int]:
        """
        Calculate all port assignments based on base port.
        
        Args:
            base_port: Base port number
            
        Returns:
            dict: Dictionary mapping port variable names to port numbers
        """
        assignments = {}
        
        for port_var, offset in self.PORT_MAPPING.items():
            assignments[port_var] = base_port + offset
            
        return assignments
    
    def update_env_ports(self, base_port: int, create_backup: bool = True) -> bool:
        """
        Update port assignments in .env file based on base port.
        Replicates the update_port() function from start.sh.
        
        Args:
            base_port: Base port number
            create_backup: Whether to create a backup before updating
            
        Returns:
            bool: True if successful
        """
        if not self.validate_base_port(base_port):
            print(f"❌ Invalid base port: {base_port}")
            return False
            
        env_file_path = self.config_parser.env_file_path
        
        if not env_file_path.exists():
            print(f"❌ .env file not found: {env_file_path}")
            return False
        
        try:
            # Create backup if requested
            if create_backup:
                backup_path = self.config_parser.create_env_backup()
                print(f"📋 Created .env backup: {backup_path}")
            
            # Read current .env file
            with open(env_file_path, 'r') as f:
                content = f.read()
            
            # Calculate new port assignments
            port_assignments = self.calculate_port_assignments(base_port)
            
            # Update each port in the content
            updated_content = content
            for port_var, new_port in port_assignments.items():
                # Use regex to find and replace the port assignment
                pattern = rf'^{port_var}=.*$'
                replacement = f'{port_var}={new_port}'
                updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
            
            # Write updated content back to .env file
            with open(env_file_path, 'w') as f:
                f.write(updated_content)
                
            print(f"✅ Updated all service ports with base port {base_port}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update ports in .env file: {e}")
            return False
    
    def get_port_conflicts(self, base_port: int) -> Dict[str, int]:
        """
        Get a mapping of port variables to conflicting port numbers.
        
        Args:
            base_port: Base port to check from
            
        Returns:
            dict: Dictionary mapping port variable names to conflicting ports
        """
        conflicts = {}
        port_assignments = self.calculate_port_assignments(base_port)
        
        for port_var, port in port_assignments.items():
            if not self.check_port_availability(port):
                conflicts[port_var] = port
                
        return conflicts
    
    def suggest_available_base_port(self, start_from: int = 50000, max_attempts: int = 100) -> Optional[int]:
        """
        Suggest an available base port by checking ranges.
        
        Args:
            start_from: Port number to start checking from
            max_attempts: Maximum number of base ports to try
            
        Returns:
            int: Suggested base port, or None if none found
        """
        for attempt in range(max_attempts):
            candidate_base = start_from + (attempt * 100)  # Try every 100 ports
            
            if not self.validate_base_port(candidate_base):
                continue
                
            used_ports = self.check_port_range_availability(candidate_base)
            if not used_ports:
                return candidate_base
                
        return None