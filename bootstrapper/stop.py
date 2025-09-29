#!/usr/bin/env python3
"""
GenAI Vanilla Stack - Stop Script

Python implementation of stop.sh with full feature parity.
Cross-platform stop script for the GenAI development environment.
"""

import sys
import os
from pathlib import Path
import click
from typing import Optional

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from utils.banner import BannerDisplay
from utils.hosts_manager import HostsManager
from core.config_parser import ConfigParser
from core.docker_manager import DockerManager


class GenAIStackStopper:
    """Main class for stopping the GenAI Stack."""
    
    def __init__(self):
        # Set root directory first
        self.root_dir = Path(__file__).resolve().parent.parent
        
        # Initialize all managers with correct root_dir
        self.banner = BannerDisplay()
        self.hosts_manager = HostsManager()
        self.config_parser = ConfigParser(str(self.root_dir))
        self.docker_manager = DockerManager(str(self.root_dir))
        
    def show_usage(self):
        """Display usage information."""
        usage_text = """
Usage: python stop.py [options]

Options:
  --cold             Remove volumes (data will be lost)
  --clean-hosts      Remove GenAI Stack hosts file entries (requires sudo/admin)
  --help             Show this help message

Examples:
  python stop.py                 # Stop all containers, preserve data
  python stop.py --cold          # Stop all containers and remove all data volumes
  python stop.py --clean-hosts   # Stop containers and clean up hosts file
"""
        print(usage_text)
        
    def show_configuration_info(self, cold_stop: bool, clean_hosts: bool):
        """Display environment configuration information."""
        self.banner.show_section_header("Environment Configuration", "📋")
        
        # Check .env file
        if self.config_parser.env_file_exists():
            timestamp = self.config_parser.get_env_file_timestamp()
            self.banner.show_status_message(f"Found .env file with timestamp: {timestamp}", "info")
            
            # Get project name
            project_name = self.config_parser.get_project_name()
            self.banner.show_status_message(f"Project name: {project_name}", "info")
        else:
            self.banner.show_status_message(".env file not found. Using default configuration.", "warning")
            project_name = self.config_parser.get_project_name()
            
        # Show Docker compose command
        compose_cmd = self.docker_manager.get_compose_command_display()
        self.banner.show_status_message(f"Using Docker Compose command: {compose_cmd}", "info")
        
        # Show stop options
        if cold_stop:
            self.banner.show_status_message("Cold Stop: Yes (removing volumes and aggressive cleanup)", "warning")
            
        if clean_hosts:
            self.banner.show_status_message("Clean Hosts: Yes (will remove hosts file entries)", "info")
            
        return project_name
        
    def stop_services(self, cold_stop: bool, project_name: str) -> bool:
        """Stop Docker services."""
        self.banner.show_section_header("Stopping Docker Compose Services", "🐳")
        
        if cold_stop:
            self.banner.show_status_message("Performing cold stop (removing volumes and aggressive cleanup)...", "warning")
            self.banner.console.print("⚠️ WARNING: This will permanently delete all data!", style="bold red")
            print()
            
            # Use the enhanced cold stop cleanup from Docker manager
            success = self.docker_manager.perform_cold_stop_cleanup()
            
            if success:
                self.banner.show_status_message("Cold stop completed successfully - all containers stopped and data removed", "success")
            else:
                self.banner.show_status_message("Some issues occurred during cold stop", "warning")
                
            return True  # Continue despite any issues
                
        else:
            self.banner.show_status_message("Performing standard stop (preserving volumes)...", "info")
            result = self.docker_manager.stop_services(remove_volumes=False, remove_orphans=True)
            
            if result == 0:
                self.banner.show_status_message("All containers stopped successfully - data volumes preserved", "success")
                return True
            else:
                self.banner.show_status_message("Some issues occurred while stopping containers", "warning")
                return True  # Continue despite issues
                
    def cleanup_hosts_entries(self) -> bool:
        """Clean up hosts file entries if requested."""
        self.banner.show_section_header("Cleaning Up Hosts File", "🧹")
        
        return self.hosts_manager.cleanup_hosts_entries()
        
    def show_final_status(self, cold_stop: bool, clean_hosts: bool):
        """Display final stop status and next steps."""
        print()
        self.banner.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="bright_white")
        
        if cold_stop:
            self.banner.console.print("🎯 GenAI Vanilla Stack stopped with complete data cleanup", style="bold bright_green")
            self.banner.console.print("   ✅ All containers stopped and removed")
            self.banner.console.print("   ✅ All data volumes removed")
            self.banner.console.print("   ✅ Project networks cleaned up")
            self.banner.console.print("   ✅ Docker system pruned")
        else:
            self.banner.console.print("🎯 GenAI Vanilla Stack stopped successfully", style="bold bright_green")
            self.banner.console.print("   ✅ All containers stopped and removed")
            self.banner.console.print("   ✅ Data volumes preserved")
            
        if clean_hosts:
            self.banner.console.print("   ✅ Hosts file entries cleaned up")
            
        self.banner.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="bright_white")
        print()
        
        # Show restart instructions
        self.banner.console.print("🔄 To restart the stack, run:", style="bold bright_white")
        self.banner.console.print("   ./start.py                    # Start with default settings")
        self.banner.console.print("   ./start.py --base-port 64567  # Start with custom base port")
        
        if cold_stop:
            self.banner.console.print("   ./start.py --cold             # Recommended after cold stop")
            
        print()
        self.banner.console.print("📚 For more information, check the README.md file", style="bright_white")


@click.command()
@click.option('--cold', is_flag=True, help='Remove volumes (data will be lost)')
@click.option('--clean-hosts', is_flag=True, help='Remove GenAI Stack hosts file entries (requires sudo/admin)')
@click.option('--help-usage', is_flag=True, help='Show detailed usage information')
def main(cold, clean_hosts, help_usage):
    """Stop the GenAI Vanilla Stack - Cross-platform AI development environment."""
    
    stopper = GenAIStackStopper()
    
    if help_usage:
        stopper.show_usage()
        return
    
    # Show initial message
    stopper.banner.show_status_message("Stopping GenAI Vanilla Stack...", "info")
    print()
    
    try:
        # Step 1: Show configuration information
        project_name = stopper.show_configuration_info(cold, clean_hosts)
        
        # Step 2: Stop Docker services
        if not stopper.stop_services(cold, project_name):
            sys.exit(1)
            
        # Step 3: Clean up hosts entries if requested
        if clean_hosts:
            if not stopper.cleanup_hosts_entries():
                # Don't exit on hosts cleanup failure, just continue
                pass
                
        # Step 4: Show final status
        stopper.show_final_status(cold, clean_hosts)
        
    except KeyboardInterrupt:
        print("\n❌ Stop process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during stop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()