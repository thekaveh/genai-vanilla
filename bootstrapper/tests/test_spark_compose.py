"""Smoke test that services/spark/compose.yml renders cleanly via include:.

The fragment cross-references `backend-network` (defined in top-level
docker-compose.yml) and `depends_on: minio-init` (from services/minio/),
so it cannot render standalone. We exercise it through the merged
top-level compose, which is also how it ships at runtime.
"""
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def test_spark_fragment_renders():
    result = subprocess.run(
        [
            "docker", "compose",
            "--env-file", str(REPO_ROOT / ".env.example"),
            "-p", "genai",
            "-f", str(REPO_ROOT / "docker-compose.yml"),
            "config", "-q",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, f"compose render failed:\n{result.stderr}"
    # Confirm spark services are present in the merged shape.
    services_result = subprocess.run(
        [
            "docker", "compose",
            "--env-file", str(REPO_ROOT / ".env.example"),
            "-p", "genai",
            "-f", str(REPO_ROOT / "docker-compose.yml"),
            "config", "--services",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert services_result.returncode == 0, services_result.stderr
    services = set(services_result.stdout.split())
    for svc in ("spark-master", "spark-worker", "spark-history", "spark-init"):
        assert svc in services, f"{svc} missing from merged compose"
