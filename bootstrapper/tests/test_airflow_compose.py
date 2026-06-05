"""Smoke + structural tests for services/airflow/compose.yml."""
from pathlib import Path
import subprocess
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE = REPO_ROOT / "services" / "airflow" / "compose.yml"


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


def test_airflow_scheduler_carries_webserver_secret_key():
    """airflow-scheduler MUST set AIRFLOW__WEBSERVER__SECRET_KEY.

    Airflow 3.x signs inter-process payloads (DagFileProcessor → scheduler
    RPC, deferrable triggers, JWT in multi-scheduler HA). The webserver
    block carried it from day one; the scheduler block initially missed it
    and Pass 1 of the post-ship audit added it. This test locks the dual
    presence so a future env-block rewrite doesn't silently drop the key.
    """
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    for svc_name in ("airflow-webserver", "airflow-scheduler"):
        env = doc["services"][svc_name]["environment"]
        assert "AIRFLOW__WEBSERVER__SECRET_KEY" in env, (
            f"{svc_name} is missing AIRFLOW__WEBSERVER__SECRET_KEY in its "
            f"compose env block. Airflow 3.x requires this for inter-process "
            f"signed payloads; missing it breaks deferrable triggers and HA."
        )
        # Must reference the auto-generated env var, not a literal.
        assert env["AIRFLOW__WEBSERVER__SECRET_KEY"] == "${AIRFLOW_SECRET_KEY}", (
            f"{svc_name}.AIRFLOW__WEBSERVER__SECRET_KEY should be "
            f"${{AIRFLOW_SECRET_KEY}}, not {env['AIRFLOW__WEBSERVER__SECRET_KEY']!r}"
        )
