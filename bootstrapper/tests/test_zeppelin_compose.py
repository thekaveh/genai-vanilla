"""Smoke test that services/zeppelin/compose.yml is properly included.

Mirrors the test_spark_compose.py pattern — exercises through the merged
top-level compose (the fragment can't render standalone because it
references backend-network from the top-level)."""
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def test_zeppelin_fragment_renders():
    result = subprocess.run(
        [
            "docker", "compose",
            "--env-file", str(REPO_ROOT / ".env.example"),
            "-p", "genai",
            "-f", str(REPO_ROOT / "docker-compose.yml"),
            "config", "--services",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    services = set(result.stdout.split())
    assert "zeppelin" in services, "zeppelin missing from merged compose"
