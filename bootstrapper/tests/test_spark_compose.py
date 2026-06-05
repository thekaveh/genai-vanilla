"""Smoke + structural tests for services/spark/compose.yml.

The fragment cross-references `backend-network` (defined in top-level
docker-compose.yml) and `depends_on: minio-init` (from services/minio/),
so it cannot render standalone. We exercise it through the merged
top-level compose, which is also how it ships at runtime.
"""
from pathlib import Path
import subprocess
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE = REPO_ROOT / "services" / "spark" / "compose.yml"

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
    # Confirm spark services are present in the merged shape (5 containers
    # since Pass 2 added the dedicated spark-connect sidecar — earlier
    # attempts at in-master Spark Connect didn't actually bind the listener).
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
    for svc in (
        "spark-master", "spark-worker", "spark-history",
        "spark-connect", "spark-init",
    ):
        assert svc in services, f"{svc} missing from merged compose"


def test_spark_connect_sidecar_uses_start_connect_server():
    """spark-connect must run apache/spark's start-connect-server.sh — the
    only upstream-supported way to bind the Connect gRPC listener on 15002.

    Locks against a future "let's run it in-master" refactor (Pass 2 audit
    P2-2 verified that SPARK_DAEMON_JAVA_OPTS alone does NOT start the
    listener; standalone Master ignores --conf and spark.plugins).
    """
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert "spark-connect" in doc["services"], "spark-connect sidecar missing"
    cmd = doc["services"]["spark-connect"]["command"]
    assert cmd[0] == "/opt/spark/sbin/start-connect-server.sh", (
        f"spark-connect command should start with start-connect-server.sh, "
        f"got {cmd[0]!r}"
    )
    # Must target the standalone master.
    assert "--master" in cmd and "spark://spark-master:7077" in cmd
    # Must NOT publish a host port (backend-only by design).
    assert "ports" not in doc["services"]["spark-connect"], (
        "spark-connect should be backend-only — no host port mapping."
    )


def test_spark_init_uses_minio_mc_image():
    """spark-init must use the minio/mc image — Alpine's `apk add mc`
    installs GNU Midnight Commander (TUI file manager), NOT MinIO Client.
    Pass 2 audit P2-1 verified this empirically; this test locks the fix.
    """
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    image = doc["services"]["spark-init"]["image"]
    assert "minio/mc" in image, (
        f"spark-init image should be minio/mc:..., got {image!r}. "
        "alpine:latest's mc package is Midnight Commander, not MinIO Client."
    )
