"""
Docker operations manager for compose commands and Docker availability checking.

Python implementation of Docker functions from start.sh and stop.sh.
"""

import subprocess
from typing import List, Optional
from pathlib import Path
from core.config_parser import ConfigParser


class DockerManager:
    """Manages Docker operations and compose commands."""
    
    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize Docker manager.
        
        Args:
            root_dir: Root directory containing docker-compose files and .env
        """
        if root_dir is None:
            # Default to parent directory of bootstrapper
            self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir)
            
        self.config_parser = ConfigParser(str(self.root_dir))
        self._compose_cmd = None
    
    def detect_docker_compose_command(self) -> str:
        """
        Detect available docker compose command.
        Replicates the detect_docker_compose_cmd() function from start.sh and stop.sh.
        
        Returns:
            str: Either "docker compose" or "docker-compose"
            
        Raises:
            RuntimeError: If neither Docker nor docker-compose is available
        """
        if self._compose_cmd is not None:
            return self._compose_cmd
            
        # Check if docker is available
        try:
            subprocess.run(['docker', '--version'], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("Docker is not installed or not in PATH")
        
        # Check if 'docker compose' (newer) works
        try:
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, check=True)
            self._compose_cmd = "docker compose"
            return self._compose_cmd
        except subprocess.CalledProcessError:
            pass
        
        # Check if 'docker-compose' (legacy) works
        try:
            subprocess.run(['docker-compose', '--version'], 
                         capture_output=True, check=True)
            self._compose_cmd = "docker-compose"
            return self._compose_cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        raise RuntimeError("Neither 'docker compose' nor 'docker-compose' command is available")
    
    def check_docker_available(self) -> bool:
        """
        Check if Docker is available.
        
        Returns:
            bool: True if Docker is available
        """
        try:
            self.detect_docker_compose_command()
            return True
        except RuntimeError:
            return False
    
    def execute_compose_command(self, args: List[str], use_env_file: bool = True) -> int:
        """
        Execute a docker compose command with proper error handling.
        Replicates the execute_compose_cmd() function from start.sh and stop.sh.
        
        Args:
            args: List of arguments to pass to docker compose
            use_env_file: Whether to use --env-file=.env flag
            
        Returns:
            int: Return code from the command
        """
        compose_cmd = self.detect_docker_compose_command().split()
        
        # Build the full command
        full_cmd = compose_cmd.copy()

        # Add project name to ensure consistency with PROJECT_NAME from .env
        project_name = self.config_parser.get_project_name()
        full_cmd.extend(['-p', project_name])

        # Add --env-file if .env exists and use_env_file is True
        if use_env_file and self.config_parser.env_file_exists():
            full_cmd.extend(['--env-file=.env'])

        full_cmd.extend(args)
        
        print(f"      Command: {' '.join(full_cmd)}")
        
        try:
            # Run the command in the root directory
            # Docker Compose will read the .env file directly via --env-file flag
            result = subprocess.run(
                full_cmd,
                cwd=str(self.root_dir),
                check=False
            )
            return result.returncode
        except Exception as e:
            print(f"❌ Error executing docker compose command: {e}")
            return 1
    
    def stop_services(self, remove_volumes: bool = False, remove_orphans: bool = True) -> int:
        """
        Stop Docker compose services.
        
        Args:
            remove_volumes: Whether to remove volumes (--volumes flag)
            remove_orphans: Whether to remove orphan containers
            
        Returns:
            int: Return code from the command
        """
        args = ['down']
        
        if remove_volumes:
            args.append('--volumes')
            
        if remove_orphans:
            args.append('--remove-orphans')
            
        return self.execute_compose_command(args)
    
    def start_services(self, detached: bool = True) -> int:
        """
        Start Docker compose services.
        Always uses --force-recreate to ensure containers are recreated with new port settings.
        This matches the original Bash script behavior.
        
        Args:
            detached: Whether to run in detached mode (-d flag)
            
        Returns:
            int: Return code from the command
        """
        args = ['up']
        
        if detached:
            args.append('-d')
            
        # Always use --force-recreate to match original Bash behavior
        # This ensures containers are recreated with updated port settings
        args.append('--force-recreate')
            
        return self.execute_compose_command(args)
    
    def remove_project_networks(self, project_name: str) -> bool:
        """
        Remove project-specific Docker networks.
        
        Args:
            project_name: Name of the project
            
        Returns:
            bool: True if successful or network doesn't exist
        """
        network_name = f"{project_name}-network"
        
        try:
            result = subprocess.run(
                ['docker', 'network', 'rm', network_name],
                capture_output=True,
                check=False
            )
            # Return True even if network doesn't exist (exit code 1)
            return True
        except Exception:
            return False
    
    def prune_system(self, remove_volumes: bool = False) -> int:
        """
        Run docker system prune to clean up unused resources.
        
        Args:
            remove_volumes: Whether to also remove volumes (--volumes flag)
            
        Returns:
            int: Return code from the command
        """
        args = ['docker', 'system', 'prune', '-f']
        
        if remove_volumes:
            args.append('--volumes')
            
        print(f"      Command: {' '.join(args)}")
        
        try:
            result = subprocess.run(args, check=False)
            return result.returncode
        except Exception as e:
            print(f"❌ Error running docker system prune: {e}")
            return 1
    
    def get_compose_command_display(self) -> str:
        """
        Get the Docker compose command for display purposes.
        
        Returns:
            str: The detected Docker compose command
        """
        try:
            return self.detect_docker_compose_command()
        except RuntimeError:
            return "docker compose (not available)"
    
    def get_compose_command(self) -> List[str]:
        """
        Get the Docker compose command as list for subprocess calls.
        
        Returns:
            List[str]: The detected Docker compose command as list
        """
        return self.detect_docker_compose_command().split()
    
    def perform_cold_start_cleanup(self) -> bool:
        """
        Perform comprehensive cold start cleanup as per the original start.sh script.
        This includes:
        1. Stop containers and remove orphans
        2. Remove volumes  
        3. Remove project network
        4. Aggressive system prune with volumes
        5. General system prune
        
        Returns:
            bool: True if all operations succeeded
        """
        project_name = self.config_parser.get_project_name()
        all_successful = True
        
        print("    - Stopping and removing containers...")
        result = self.execute_compose_command(['down', '--remove-orphans'])
        if result != 0:
            all_successful = False
            
        print("    - Removing volumes (cold start)...")
        result = self.execute_compose_command(['down', '-v'])
        if result != 0:
            all_successful = False
        
        print("    - Removing project network (cold start)...")
        print(f"      Command: docker network rm {project_name}-network")
        if not self.remove_project_networks(project_name):
            print("      Note: Network may not exist or is already removed")
            
        print("    - Performing aggressive Docker system prune (cold start)...")
        result = self.prune_system(remove_volumes=True)
        if result != 0:
            all_successful = False
            
        print("    - Performing general Docker system prune...")
        result = self.prune_system(remove_volumes=False)
        if result != 0:
            all_successful = False
            
        return all_successful
    
    def perform_cold_stop_cleanup(self) -> bool:
        """
        Perform comprehensive cold stop cleanup as per the original stop.sh script.
        This includes:
        1. Stop containers, remove volumes and orphans
        2. Remove project networks
        3. System prune with volumes
        
        Returns:
            bool: True if all operations succeeded
        """
        project_name = self.config_parser.get_project_name()
        all_successful = True
        
        print("    - Stopping containers and removing volumes...")
        result = self.execute_compose_command(['down', '--volumes', '--remove-orphans'])
        if result != 0:
            all_successful = False
            
        print("    - Removing project networks...")
        if not self.remove_project_networks(project_name):
            print("      Note: Network may not exist or is already removed")
            
        print("    - Performing Docker system cleanup...")
        result = self.prune_system(remove_volumes=True)
        if result != 0:
            all_successful = False
            
        return all_successful
    
    def build_services(self, no_cache: bool = False, pull: bool = False) -> int:
        """
        Build Docker compose services with optional flags.
        
        Args:
            no_cache: Whether to build without cache (--no-cache flag)
            pull: Whether to pull latest images (--pull flag)
            
        Returns:
            int: Return code from the command
        """
        args = ['build']
        
        if no_cache:
            args.append('--no-cache')
            
        if pull:
            args.append('--pull')
            
        return self.execute_compose_command(args)
    
    def up_with_build(self, detached: bool = True, no_cache: bool = False) -> int:
        """
        Start services with build, replicating the fresh build functionality from start.sh.
        
        Args:
            detached: Whether to run in detached mode
            no_cache: Whether to build without cache
            
        Returns:
            int: Return code from the command
        """
        args = ['up']
        
        if detached:
            args.append('-d')
            
        args.append('--build')
        
        if no_cache:
            # For no-cache, we need to build first then up
            print("    - Building services without cache...")
            build_result = self.build_services(no_cache=True, pull=True)
            if build_result != 0:
                return build_result
            
            # Then start normally
            return self.start_services(detached=detached)
        
        return self.execute_compose_command(args)
    
    def show_container_status(self) -> int:
        """
        Show container status using docker compose ps.
        Replicates the 'execute_compose_cmd ps' from original start.sh.
        
        Returns:
            int: Return code from the command
        """
        print("🔍 Verifying port mappings from Docker...")
        return self.execute_compose_command(['ps'])
        
    def get_service_port(self, service: str, internal_port: str) -> str:
        """
        Get the actual external port mapped to a service's internal port.
        Replicates the get_actual_port() function from original start.sh.
        
        Args:
            service: Service name
            internal_port: Internal port number
            
        Returns:
            str: External port number, or empty string if not found
        """
        try:
            result = subprocess.run(
                [*self.get_compose_command(), '--env-file=.env', 'port', service, internal_port],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Extract port number from output like "0.0.0.0:63000"
                import re
                match = re.search(r':(\d+)$', result.stdout.strip())
                if match:
                    return match.group(1)
            return ""
        except Exception:
            return ""
    
    def show_container_logs(self, follow: bool = True) -> int:
        """
        Show container logs using docker compose logs.
        Replicates the 'execute_compose_cmd logs -f' from original start.sh.
        
        Args:
            follow: Whether to follow logs (default True)
            
        Returns:
            int: Return code from the command
        """
        args = ['logs']
        if follow:
            args.append('-f')
            
        print("📋 Container logs (press Ctrl+C to exit):")
        return self.execute_compose_command(args)