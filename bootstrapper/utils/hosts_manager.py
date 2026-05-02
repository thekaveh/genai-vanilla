"""
Hosts file management utilities.

Python implementation of hosts-utils.sh functions.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional
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
        "jupyter.localhost",
        "openclaw.localhost"
    ]

    def __init__(self):
        self.hosts_file_path = get_hosts_file_path()
        self.os_type = detect_os()
        # Optional logger callback (msg, level). When None, falls back to
        # plain print(). The Live region wires this so output flows through
        # the log pane instead of tearing the alternate screen.
        self._logger: Optional[Callable[[str, str], None]] = None

    def set_logger(self, logger: Optional[Callable[[str, str], None]]) -> None:
        """Inject a (msg, level) callback used by every status message
        emitted from this class. Pass None to revert to print()."""
        self._logger = logger

    def _log(self, message: str, level: str = "info") -> None:
        """Route a status message through the registered logger or print."""
        if self._logger is not None:
            try:
                self._logger(message, level)
                return
            except Exception:
                pass
        print(message)
        
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
                    self._log(f"  • Created backup: {backup_path}", "info")
                    
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
                self._log(f"  • Created backup: {backup_path}", "info")

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
            self._log(f"  • ❌ Cannot determine hosts file location for OS: {self.os_type}", "error")
            return False

        if not Path(self.hosts_file_path).exists():
            self._log(f"  • ❌ Hosts file not found: {self.hosts_file_path}", "error")
            return False

        # Check if we have elevated privileges
        if not is_elevated():
            self._log("  • ❌ Administrative privileges required to modify hosts file", "error")
            if self.os_type == "windows":
                self._log("    Please run as Administrator", "error")
            else:
                self._log("    Please run with sudo (Linux/macOS) or as Administrator (Windows)", "error")
            return False

        self._log("  • Setting up GenAI Stack hosts entries...", "info")
        self._log(f"  • Hosts file: {self.hosts_file_path}", "info")

        # Check which entries are missing first
        missing = self.check_missing_hosts()

        if not missing:
            self._log("  • ✅ All GenAI hosts entries already exist", "success")
            return True

        self._log(f"  • Adding missing entries: {', '.join(missing)}", "info")

        # Add the missing entries
        if self.add_hosts_entries(self.hosts_file_path):
            self._log("  • ✅ Hosts entries added successfully", "success")
            self._log("  • You can now access services via:", "info")
            for host in self.get_genai_hosts():
                self._log(f"    - http://{host}", "info")
            return True
        else:
            self._log("  • ❌ Failed to add hosts entries", "error")
            return False
    
    def cleanup_hosts_entries(self) -> bool:
        """
        Clean up GenAI hosts entries from the hosts file.
        Used by stop.py with --clean-hosts flag.
        
        Returns:
            bool: True if successful
        """
        if not self.hosts_file_path:
            self._log(f"  • ⚠️  Cannot determine hosts file location for OS: {self.os_type}", "warning")
            return False

        if not Path(self.hosts_file_path).exists():
            self._log(f"  • ⚠️  Hosts file not found: {self.hosts_file_path}", "warning")
            return False

        # Check if we have elevated privileges
        if not is_elevated():
            self._log("  • ❌ Administrative privileges required to modify hosts file", "error")
            if self.os_type == "windows":
                self._log("    Please run as Administrator", "error")
            else:
                self._log("    Please run with sudo (Linux/macOS) or as Administrator (Windows)", "error")

            self._log("    Or manually remove these entries from hosts file:", "info")
            for host in self.get_genai_hosts():
                self._log(f"    127.0.0.1 {host}", "info")
            return False

        self._log("  • Removing GenAI Stack hosts file entries...", "info")

        if self.remove_hosts_entries(self.hosts_file_path):
            self._log("  • ✅ Hosts entries removed successfully", "success")
            self._log("    The following entries were removed:", "info")
            for host in self.get_genai_hosts():
                self._log(f"    127.0.0.1 {host}", "info")
            return True
        else:
            self._log("  • ❌ Failed to remove hosts entries", "error")
            return False

    def check_hosts_status(self) -> None:
        """
        Check and display the status of GenAI hosts entries.
        Used by start.py to show hosts status.
        """
        if not self.hosts_file_path or not Path(self.hosts_file_path).exists():
            self._log("  • ⚠️  Cannot access hosts file", "warning")
            self._log("    Manual setup may be required for subdomain access", "warning")
            return

        missing = self.check_missing_hosts()

        if missing:
            self._log(f"  • Missing hosts entries: {', '.join(missing)}", "warning")
            self._log("    Run with --setup-hosts to add them automatically", "info")
        else:
            self._log("  • ✅ All required hosts entries are present", "success")