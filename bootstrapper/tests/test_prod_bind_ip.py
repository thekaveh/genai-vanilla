import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not available")
def test_prod_bind_ip_localhost():
    # Render compose with HOST_BIND_IP set; every published port must be 127.0.0.1-bound.
    env = os.environ.copy()
    env["HOST_BIND_IP"] = "127.0.0.1:"
    # provide minimal required vars by sourcing the committed .env.example
    out = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "--env-file", ".env.example", "config"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr

    # Docker Compose renders published ports in expanded form:
    #   - mode: ingress
    #     host_ip: 127.0.0.1
    #     target: <container_port>
    #     published: "<host_port>"
    # In prod mode every published port must carry host_ip: 127.0.0.1.
    # The literal string "0.0.0.0" must not appear as a host_ip value.
    assert "host_ip: 0.0.0.0" not in out.stdout, (
        "A port was rendered with host_ip 0.0.0.0 — some fragment is missing the HOST_BIND_IP prefix"
    )
    # Sanity: at least one port is actually bound to 127.0.0.1.
    assert "host_ip: 127.0.0.1" in out.stdout, (
        "No port was rendered with host_ip 127.0.0.1 — HOST_BIND_IP substitution did not take effect"
    )
