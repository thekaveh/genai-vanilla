"""
Docker operations manager for compose commands and Docker availability checking.

Python implementation of Docker functions from start.sh and stop.sh.
"""

import os
import signal
import subprocess
from typing import Callable, List, Optional
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

        # Callback for the "Command: docker compose …" echo. Defaults to
        # builtin print so the legacy linear flow is unchanged. The Live
        # presentation sets this to `app.log` to route the echo through the
        # log pane in dim style.
        self._on_command: Callable[[str], None] = print
    
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

        self._on_command(f"      Command: {' '.join(full_cmd)}")

        try:
            # Run the command in the root directory
            # Docker Compose will read the .env file directly via --env-file flag.
            # stdin=DEVNULL prevents any terminal keystroke from leaking into
            # docker's stdin during long-running passthrough commands like
            # `logs -f` — the keystrokes would otherwise be visible inside an
            # active scroll region.
            result = subprocess.run(
                full_cmd,
                cwd=str(self.root_dir),
                stdin=subprocess.DEVNULL,
                check=False
            )
            return result.returncode
        except Exception as e:
            self._on_command(f"❌ Error executing docker compose command: {e}")
            return 1

    def set_command_echo_callback(self, callback: Callable[[str], None]) -> None:
        """
        Override where 'Command: docker compose …' echoes get routed.

        The Live presentation passes app.log here so command echoes appear
        in the windowed log pane (in dim style) rather than as raw stdout
        breaking the alternate screen. Reset to `print` for the legacy flow.
        """
        self._on_command = callback
    
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

        self._on_command(f"      Command: {' '.join(args)}")

        try:
            proc = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self._on_command(line.rstrip("\n"))
            return proc.wait()
        except Exception as e:
            self._on_command(f"❌ Error running docker system prune: {e}")
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
        """Stop containers, remove volumes and orphans, drop the project network, and prune the Docker system (twice — once with volumes, once general).

        All output flows through the registered command-echo callback
        (`_on_command`) so the wizard's Live region can stream it into
        the log pane without tearing the alternate screen.

        Returns True if every step succeeded.
        """
        project_name = self.config_parser.get_project_name()
        all_successful = True

        self._on_command("    - Stopping and removing containers...")
        result = self.stream_compose(
            ['down', '--remove-orphans'],
            on_line=self._on_command,
        )
        if result != 0:
            all_successful = False

        self._on_command("    - Removing volumes (cold start)...")
        result = self.stream_compose(
            ['down', '-v'],
            on_line=self._on_command,
        )
        if result != 0:
            all_successful = False

        self._on_command("    - Removing project network (cold start)...")
        self._on_command(f"      Command: docker network rm {project_name}-network")
        if not self.remove_project_networks(project_name):
            self._on_command("      Note: Network may not exist or is already removed")

        self._on_command("    - Performing aggressive Docker system prune (cold start)...")
        result = self.prune_system(remove_volumes=True)
        if result != 0:
            all_successful = False

        self._on_command("    - Performing general Docker system prune...")
        result = self.prune_system(remove_volumes=False)
        if result != 0:
            all_successful = False

        return all_successful
    
    def perform_cold_stop_cleanup(self) -> bool:
        """Stop containers, remove volumes and orphans, drop project networks, and prune the Docker system with volumes.

        Returns True if every step succeeded.
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
    
    def show_container_status(self) -> int:
        """
        Show container status using docker compose ps.
        Replicates the 'execute_compose_cmd ps' from original start.sh.
        
        Returns:
            int: Return code from the command
        """
        print("🔍 Verifying port mappings from Docker...")
        return self.execute_compose_command(['ps'])
        
    def are_project_containers_running(self) -> bool:
        """
        Check if any containers from this project's Docker Compose stack are currently running.

        Uses 'docker compose ps -q' which returns container IDs of running services.
        An empty result means no containers are running.

        Returns:
            bool: True if any project containers are running
        """
        try:
            cmd = self.get_compose_command()
            project_name = self.config_parser.get_project_name()
            cmd.extend(['-p', project_name])
            if self.config_parser.env_file_exists():
                cmd.append('--env-file=.env')
            cmd.extend(['ps', '-q'])

            result = subprocess.run(
                cmd,
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                check=False
            )

            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

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
            cmd = self.get_compose_command()
            project_name = self.config_parser.get_project_name()
            cmd.extend(['-p', project_name])
            if self.config_parser.env_file_exists():
                cmd.append('--env-file=.env')
            cmd.extend(['port', service, internal_port])

            result = subprocess.run(
                cmd,
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

    # --- Streaming variants for the Live-region presentation -----------------
    # These replace the TTY-passthrough `execute_compose_command` for the
    # log-streaming and long-running build/cleanup phases. Without piping
    # and line-buffering, the alternate-screen Live region would be torn up
    # by raw subprocess output.

    def _build_compose_command(
        self,
        args: List[str],
        use_env_file: bool = True,
        top_level_flags: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Internal helper — build the full `docker compose` argv with project
        name and --env-file flag, mirroring `execute_compose_command` but
        without running it. Used by the streaming variants below.

        `top_level_flags` are inserted between the `docker compose` binary
        and the `-p` / `--env-file` flags — i.e. they're docker-compose
        global flags (like `--ansi=always` or `--progress=plain`) that
        must come before the subcommand.
        """
        full_cmd = self.detect_docker_compose_command().split()
        if top_level_flags:
            full_cmd.extend(top_level_flags)
        project_name = self.config_parser.get_project_name()
        full_cmd.extend(['-p', project_name])
        if use_env_file and self.config_parser.env_file_exists():
            full_cmd.extend(['--env-file=.env'])
        full_cmd.extend(args)
        return full_cmd

    def stream_compose(
        self,
        args: List[str],
        on_line: Callable[[str], None],
        use_env_file: bool = True,
    ) -> int:
        """
        Run a docker compose command with stdout piped, line-buffered, and
        forwarded to `on_line` per line. Used for cold-start cleanup, image
        build, and `up -d` so their output flows into the log pane instead
        of inheriting (and tearing up) the Live region's alternate screen.

        bufsize=1 + text=True is essential — without it Python block-buffers
        piped stdout and the log pane stalls then bursts.

        We pass `--ansi=always` so compose keeps emitting SGR color codes
        even when stdout isn't a TTY (the default --ansi=auto would strip
        them). We deliberately do NOT pass `--progress=plain` — compose
        rejects that combination ("can't use --progress plain while ANSI
        support is forced"). With `--progress=auto` (the default) compose
        auto-detects the piped stdout and emits plain line-based progress
        anyway, so we get plain progress AND colors without the conflict.

        BUILDKIT_PROGRESS=plain in the subprocess env keeps buildkit's
        own renderer (used during `docker compose build`) on plain
        output too — buildkit doesn't share compose's --ansi conflict.

        Returns the subprocess exit code.
        """
        full_cmd = self._build_compose_command(
            args,
            use_env_file=use_env_file,
            top_level_flags=['--ansi=always'],
        )
        self._on_command(f"      Command: {' '.join(full_cmd)}")

        env = os.environ.copy()
        env['BUILDKIT_PROGRESS'] = 'plain'

        try:
            proc = subprocess.Popen(
                full_cmd,
                cwd=str(self.root_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
                env=env,
            )
        except Exception as e:
            on_line(f"❌ Error launching docker compose: {e}")
            return 1

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                on_line(line.rstrip("\n"))
            return proc.wait()
        except KeyboardInterrupt:
            return self._terminate_subprocess(proc)

    def stream_logs(self, on_line: Callable[[str], None]) -> int:
        """
        Run `docker compose logs -f` with stdout piped and forwarded line
        by line to `on_line`. Replaces show_container_logs's passthrough
        behavior when the Live region is active.

        Blocks until the subprocess exits or the caller raises
        KeyboardInterrupt; on Ctrl+C, sends SIGINT to the subprocess and
        waits up to 3 s before SIGKILL so the user gets a clean detach.
        """
        return self.stream_compose(['logs', '-f'], on_line=on_line)

    @staticmethod
    def _terminate_subprocess(proc: subprocess.Popen) -> int:
        """Best-effort clean termination — SIGINT, wait 3 s, then SIGKILL."""
        try:
            proc.send_signal(signal.SIGINT)
            try:
                return proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                return proc.wait()
        except Exception:
            return 1

    def get_services_status(self) -> dict:
        """
        Run `docker compose ps --format json` and return a dict of
        {service_name: state_string}, where state_string is one of
        "running" | "starting" | "unhealthy" | "stopped".

        Tolerates both line-delimited JSON (Compose ≥ 2.21) and the older
        single-array shape. Failures (timeout, docker stopped, malformed
        JSON) return an empty dict so the caller can fall back to .env
        configured state without crashing.
        """
        import json

        full_cmd = self._build_compose_command(['ps', '--format', 'json'])
        try:
            result = subprocess.run(
                full_cmd,
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return {}

        if result.returncode != 0 or not result.stdout.strip():
            return {}

        # Try parsing as a single JSON array first; fall back to JSONL.
        entries = []
        try:
            parsed = json.loads(result.stdout)
            entries = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip malformed lines, keep going

        snapshot = {}
        for e in entries:
            service = e.get("Service") or e.get("Name") or ""
            if not service:
                continue
            state = (e.get("State") or "").lower()
            health = (e.get("Health") or "").lower()

            if state == "running" and health in ("healthy", "", "none"):
                snapshot[service] = "running"
            elif health == "unhealthy":
                snapshot[service] = "unhealthy"
            elif health == "starting" or state in ("created", "restarting"):
                snapshot[service] = "starting"
            elif state == "exited":
                snapshot[service] = "stopped"
            else:
                # Unknown state — show as starting so the user sees something
                # is happening rather than a stale "off" dot.
                snapshot[service] = "starting"
        return snapshot