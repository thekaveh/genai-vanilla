"""
System utilities for OS detection, permission checking, and localhost resolution.

Python implementation of functions from hosts-utils.sh and start.sh.
"""

import os
import platform
import ctypes
import subprocess
import socket


def detect_os() -> str:
    """
    Detect the operating system.
    
    Returns:
        str: "macos", "linux", "windows", or "unknown"
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux" 
    elif system == "windows":
        return "windows"
    else:
        return "unknown"


def is_elevated() -> bool:
    """
    Check if running with elevated privileges.
    
    Returns:
        bool: True if running as admin/root, False otherwise
    """
    os_type = detect_os()
    
    if os_type == "windows":
        try:
            # Windows: check if running as administrator
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # Unix-like: check if running as root
        try:
            return os.geteuid() == 0
        except AttributeError:
            # Windows doesn't have geteuid - fallback to False
            return False


def get_localhost_host() -> str:
    """
    Get the correct host reference for localhost services.
    On Linux, host.docker.internal might not work, so we need a fallback.
    
    Returns:
        str: The appropriate localhost hostname for Docker
    """
    os_type = detect_os()
    
    if os_type == "linux":
        # Check if host.docker.internal resolves
        try:
            socket.gethostbyname("host.docker.internal")
            return "host.docker.internal"
        except socket.gaierror:
            # Fallback to Docker bridge gateway on Linux
            return "172.17.0.1"
    else:
        # Works on macOS and Windows
        return "host.docker.internal"


def detect_container_runtime() -> str:
    """
    Detect whether the Docker CLI is backed by Docker Engine or Podman.

    Returns:
        str: "docker" or "podman"
    """
    try:
        result = subprocess.run(
            ['docker', 'version'],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )
        output = (result.stdout + result.stderr).lower()
        if 'podman' in output:
            return "podman"
    except (FileNotFoundError, OSError):
        pass
    return "docker"


def resolve_host_gateway_ip() -> str:
    """
    Resolve the IP address that containers should use to reach the host.

    For Docker Desktop: returns the literal string "host-gateway" (Docker
    resolves this at container creation time).

    For Podman: queries the default bridge network gateway IP, which is the
    host from the container's perspective.

    Returns:
        str: IP address or "host-gateway"
    """
    runtime = detect_container_runtime()

    if runtime == "docker":
        return "host-gateway"

    # Podman: resolve from bridge network IPAM config
    try:
        result = subprocess.run(
            ['docker', 'network', 'inspect', 'bridge',
             '--format', '{{range .IPAM.Config}}{{.Gateway}}{{end}}'],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )
        gateway = result.stdout.strip()
        if gateway:
            return gateway
    except (FileNotFoundError, OSError):
        pass

    # Podman fallback: run a throwaway container to read the default route
    try:
        result = subprocess.run(
            ['docker', 'run', '--rm', 'alpine',
             'sh', '-c', "ip route | awk '/default/{print $3}'"],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )
        gateway = result.stdout.strip()
        if gateway:
            return gateway
    except (FileNotFoundError, OSError):
        pass

    # Ultimate fallback: Podman's typical bridge gateway
    return "10.88.0.1"


def get_hosts_file_path() -> str:
    """
    Get the hosts file path based on the operating system.
    
    Returns:
        str: Path to the hosts file, or empty string if unknown
    """
    os_type = detect_os()
    
    if os_type in ["macos", "linux"]:
        return "/etc/hosts"
    elif os_type == "windows":
        return "C:/Windows/System32/drivers/etc/hosts"
    else:
        return ""


def run_command(command: list, capture_output: bool = True) -> subprocess.CompletedProcess:
    """
    Run a system command with proper error handling.
    
    Args:
        command: List of command arguments
        capture_output: Whether to capture stdout/stderr
        
    Returns:
        subprocess.CompletedProcess: The completed process
    """
    try:
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        # Command not found
        raise FileNotFoundError(f"Command not found: {command[0]}")