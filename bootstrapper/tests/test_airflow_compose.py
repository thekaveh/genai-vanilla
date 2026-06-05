"""Smoke test that services/airflow/compose.yml is properly included."""
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def test_airflow_fragment_renders():
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
    for svc in ("airflow-webserver", "airflow-scheduler", "airflow-init"):
        assert svc in services, f"{svc} missing from merged compose"
