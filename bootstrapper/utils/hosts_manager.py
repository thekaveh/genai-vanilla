"""
Hosts file management utilities.

Python implementation of hosts-utils.sh functions.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from utils.system import detect_os, is_elevated, get_hosts_file_path


class HostsManager:
    """Manages hosts file entries for GenAI Stack services."""
    
    # GenAI Stack hostnames - matches get_genai_hosts() from hosts-utils.sh
    GENAI_HOSTS = [
        "n8n.localhost",
        "api.localhost",
        "search.localhost",
        "comfyui.localhost",
        "chat.localhost",
        "jupyter.localhost"
    ]
    
    def __init__(self):
        self.hosts_file_path = get_hosts_file_path()
        self.os_type = detect_os()
        
    def get_genai_hosts(self) -> List[str]:
        """
        Get the list of GenAI Stack hostnames.
        Replicates the get_genai_hosts() function from hosts-utils.sh.
        
        Returns:
            list: List of GenAI hostnames
        """
        return self.GENAI_HOSTS.copy()
    
    def check_missing_hosts(self) -> List[str]:
        """
        Check which hosts entries are missing from the hosts file.
        Replicates the check_missing_hosts() function from hosts-utils.sh.
        
        Returns:
            list: List of missing hostnames
        """
        if not self.hosts_file_path or not Path(self.hosts_file_path).exists():
            return self.get_genai_hosts()  # All are missing if no hosts file
            
        missing = []
        
        try:
            with open(self.hosts_file_path, 'r') as f:
                hosts_content = f.read()
                
            for host in self.get_genai_hosts():
                # Check for line like "127.0.0.1    hostname" with flexible whitespace
                pattern = rf'^\s*127\.0\.0\.1\s+.*\b{re.escape(host)}\b'
                if not re.search(pattern, hosts_content, re.MULTILINE):
                    missing.append(host)
                    
        except Exception:
            return self.get_genai_hosts()  # All are missing on error
            
        return missing
    
    def remove_hosts_entries_silent(self, hosts_file_path: str) -> bool:
        """
        Remove GenAI hosts entries without creating backup.
        Replicates the remove_hosts_entries_silent() function from hosts-utils.sh.
        
        Args:
            hosts_file_path: Path to hosts file
            
        Returns:
            bool: True if successful
        """
        try:
            with open(hosts_file_path, 'r') as f:
                lines = f.readlines()
            
            # Filter out GenAI-related lines
            filtered_lines = []
            for line in lines:
                # Skip the comment line
                if "# GenAI Stack subdomains" in line:
                    continue
                    
                # Skip any line with GenAI hostnames
                should_skip = False
                for host in self.get_genai_hosts():
                    if f"127.0.0.1" in line and host in line:
                        should_skip = True
                        break
                        
                if not should_skip:
                    filtered_lines.append(line)
            
            # Write back the filtered content
            with open(hosts_file_path, 'w') as f:
                f.writelines(filtered_lines)
                
            return True
            
        except Exception:
            return False
    
    def add_hosts_entries(self, hosts_file_path: str, create_backup: bool = True) -> bool:
        """
        Add GenAI hosts entries to the hosts file.
        Replicates the add_hosts_entries() function from hosts-utils.sh.
        
        Args:
            hosts_file_path: Path to hosts file
            create_backup: Whether to create a backup first
            
        Returns:
            bool: True if successful
        """
        try:
            if create_backup:
                backup_path = self._create_hosts_backup(hosts_file_path)
                if backup_path:
                    print(f"  • Created backup: {backup_path}")
                    
            # Remove existing GenAI entries first (cleanup)
            self.remove_hosts_entries_silent(hosts_file_path)
            
            # Add new entries
            with open(hosts_file_path, 'a') as f:
                f.write("\n")
                f.write("# GenAI Stack subdomains (added by start.py)\n")
                for host in self.get_genai_hosts():
                    f.write(f"127.0.0.1 {host}\n")
                    
            return True
            
        except Exception:
            return False
    
    def remove_hosts_entries(self, hosts_file_path: str) -> bool:
        """
        Remove GenAI hosts entries with backup.
        Replicates the remove_hosts_entries() function from hosts-utils.sh.
        
        Args:
            hosts_file_path: Path to hosts file
            
        Returns:
            bool: True if successful
        """
        try:
            backup_path = self._create_hosts_backup(hosts_file_path)
            if backup_path:
                print(f"  • Created backup: {backup_path}")
            
            return self.remove_hosts_entries_silent(hosts_file_path)
            
        except Exception:
            return False
    
    def _create_hosts_backup(self, hosts_file_path: str) -> Optional[str]:
        """
        Create a backup of the hosts file with timestamp.
        
        Args:
            hosts_file_path: Path to hosts file
            
        Returns:
            str: Path to backup file, or None if failed
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_path = f"{hosts_file_path}.backup.{timestamp}"
            shutil.copy2(hosts_file_path, backup_path)
            return backup_path
        except Exception:
            return None
    
    def setup_hosts_entries(self) -> bool:
        """
        Main function to setup GenAI hosts entries.
        Replicates the setup_hosts_entries() function from hosts-utils.sh.
        
        Returns:
            bool: True if successful
        """
        if not self.hosts_file_path:
            print(f"  • ❌ Cannot determine hosts file location for OS: {self.os_type}")
            return False
            
        if not Path(self.hosts_file_path).exists():
            print(f"  • ❌ Hosts file not found: {self.hosts_file_path}")
            return False
            
        # Check if we have elevated privileges
        if not is_elevated():
            print("  • ❌ Administrative privileges required to modify hosts file")
            if self.os_type == "windows":
                print("    Please run as Administrator")
            else:
                print("    Please run with sudo (Linux/macOS) or as Administrator (Windows)")
            return False
            
        print("  • Setting up GenAI Stack hosts entries...")
        print(f"  • Hosts file: {self.hosts_file_path}")
        
        # Check which entries are missing first
        missing = self.check_missing_hosts()
        
        if not missing:
            print("  • ✅ All GenAI hosts entries already exist")
            return True
            
        print(f"  • Adding missing entries: {', '.join(missing)}")
        
        # Add the missing entries
        if self.add_hosts_entries(self.hosts_file_path):
            print("  • ✅ Hosts entries added successfully")
            print("  • You can now access services via:")
            for host in self.get_genai_hosts():
                print(f"    - http://{host}")
            return True
        else:
            print("  • ❌ Failed to add hosts entries")
            return False
    
    def cleanup_hosts_entries(self) -> bool:
        """
        Clean up GenAI hosts entries from the hosts file.
        Used by stop.py with --clean-hosts flag.
        
        Returns:
            bool: True if successful
        """
        if not self.hosts_file_path:
            print(f"  • ⚠️  Cannot determine hosts file location for OS: {self.os_type}")
            return False
            
        if not Path(self.hosts_file_path).exists():
            print(f"  • ⚠️  Hosts file not found: {self.hosts_file_path}")
            return False
            
        # Check if we have elevated privileges
        if not is_elevated():
            print("  • ❌ Administrative privileges required to modify hosts file")
            if self.os_type == "windows":
                print("    Please run as Administrator")
            else:
                print("    Please run with sudo (Linux/macOS) or as Administrator (Windows)")
            
            print("    Or manually remove these entries from hosts file:")
            for host in self.get_genai_hosts():
                print(f"    127.0.0.1 {host}")
            return False
            
        print("  • Removing GenAI Stack hosts file entries...")
        
        if self.remove_hosts_entries(self.hosts_file_path):
            print("  • ✅ Hosts entries removed successfully")
            print("    The following entries were removed:")
            for host in self.get_genai_hosts():
                print(f"    127.0.0.1 {host}")
            return True
        else:
            print("  • ❌ Failed to remove hosts entries")
            return False
    
    def check_hosts_status(self) -> None:
        """
        Check and display the status of GenAI hosts entries.
        Used by start.py to show hosts status.
        """
        if not self.hosts_file_path or not Path(self.hosts_file_path).exists():
            print("  • ⚠️  Cannot access hosts file")
            print("    Manual setup may be required for subdomain access")
            return
            
        missing = self.check_missing_hosts()
        
        if missing:
            print(f"  • Missing hosts entries: {', '.join(missing)}")
            print("    Run with --setup-hosts to add them automatically")
        else:
            print("  • ✅ All required hosts entries are present")