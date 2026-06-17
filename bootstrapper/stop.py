#!/usr/bin/env python3
"""
Atlas - Stop Script

Python implementation of stop.sh with full feature parity.
Cross-platform stop script for the Atlas development environment.
"""

import sys
from pathlib import Path
import click

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from utils.banner import BannerDisplay
from utils.hosts_manager import HostsManager
from core.config_parser import ConfigParser
from core.docker_manager import DockerManager


class AtlasStopper:
    """Main class for stopping the Atlas."""
    
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
Usage: ./stop.sh [options]   (or: python bootstrapper/stop.py)

Options:
  --cold             Remove volumes (data will be lost)
  --clean-hosts      Remove Atlas hosts file entries (requires sudo/admin)
  --help-usage       Show this detailed usage message
  --help             Show the option summary

Examples:
  ./stop.sh                 # Stop all containers, preserve data
  ./stop.sh --cold          # Stop containers, remove project volumes, AND run a global `docker system prune -f --volumes` (touches unused images/volumes of OTHER projects too)
  ./stop.sh --clean-hosts   # Stop containers and clean up hosts file
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

            return success
                
        else:
            self.banner.show_status_message("Performing standard stop (preserving volumes)...", "info")
            result = self.docker_manager.stop_services(remove_volumes=False, remove_orphans=True)
            
            if result == 0:
                self.banner.show_status_message("All containers stopped successfully - data volumes preserved", "success")
                return True
            else:
                self.banner.show_status_message("Some issues occurred while stopping containers", "warning")
                return False
                
    def cleanup_hosts_entries(self) -> bool:
        """Clean up hosts file entries if requested."""
        self.banner.show_section_header("Cleaning Up Hosts File", "🧹")
        
        return self.hosts_manager.cleanup_hosts_entries()
        
    def show_final_status(self, cold_stop: bool, clean_hosts: bool, services_ok: bool = True, hosts_ok: bool = True):
        """Display final stop status and next steps."""
        print()
        self.banner.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="bright_white")

        if not services_ok:
            self.banner.console.print("⚠️  Atlas stop completed with errors — see messages above", style="bold bright_yellow")
        elif cold_stop:
            self.banner.console.print("🎯 Atlas stopped with complete data cleanup", style="bold bright_green")
            self.banner.console.print("   ✅ All containers stopped and removed")
            self.banner.console.print("   ✅ All data volumes removed")
            self.banner.console.print("   ✅ Project networks cleaned up")
            self.banner.console.print("   ✅ Docker system pruned")
        else:
            self.banner.console.print("🎯 Atlas stopped successfully", style="bold bright_green")
            self.banner.console.print("   ✅ All containers stopped and removed")
            self.banner.console.print("   ✅ Data volumes preserved")
            
        if clean_hosts:
            if hosts_ok:
                self.banner.console.print("   ✅ Hosts file entries cleaned up")
            else:
                self.banner.console.print(
                    "   ⚠️  Hosts file cleanup FAILED (needs sudo?) — run "
                    "./stop.sh --clean-hosts again with privileges",
                    style="bold bright_yellow",
                )
            
        self.banner.console.print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", style="bright_white")
        print()
        
        # Show restart instructions
        self.banner.console.print("🔄 To restart the stack, run:", style="bold bright_white")
        self.banner.console.print("   ./start.sh                    # Start with default settings")
        self.banner.console.print("   ./start.sh --base-port 64567  # Start with custom base port")
        
        if cold_stop:
            self.banner.console.print("   ./start.sh --cold             # Recommended after cold stop")
            
        print()
        self.banner.console.print("📚 For more information, check the README.md file", style="bright_white")


@click.command()
@click.option('--cold', is_flag=True, help='Remove volumes (data will be lost)')
@click.option('--clean-hosts', is_flag=True, help='Remove Atlas hosts file entries (requires sudo/admin)')
@click.option('--help-usage', is_flag=True, help='Show detailed usage information')
def main(cold, clean_hosts, help_usage):
    """Stop the Atlas - Cross-platform AI development environment."""
    
    stopper = AtlasStopper()
    
    if help_usage:
        stopper.show_usage()
        return
    
    # Show initial message
    stopper.banner.show_status_message("Stopping Atlas...", "info")
    print()
    
    try:
        # Step 1: Show configuration information
        project_name = stopper.show_configuration_info(cold, clean_hosts)
        
        # Step 2: Stop Docker services. Keep going on failure so hosts
        # cleanup and the final status still run, but exit non-zero at the
        # end — scripts/CI need a truthful exit code for a failed `down`.
        services_ok = stopper.stop_services(cold, project_name)

        # Step 3: Clean up hosts entries if requested
        hosts_ok = True
        if clean_hosts:
            # Don't exit on hosts cleanup failure — but DO tell the truth
            # about it in the final banner instead of a blanket ✅.
            hosts_ok = stopper.cleanup_hosts_entries()

        # Step 4: Show final status
        stopper.show_final_status(
            cold, clean_hosts, services_ok=services_ok, hosts_ok=hosts_ok,
        )

        if not services_ok:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n❌ Stop process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during stop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()