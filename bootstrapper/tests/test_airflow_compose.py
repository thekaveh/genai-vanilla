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


def test_airflow_scheduler_carries_api_secret_key():
    """airflow-scheduler MUST set AIRFLOW__API__SECRET_KEY.

    Airflow 3.x signs inter-process payloads (DagFileProcessor → scheduler
    RPC, deferrable triggers, JWT in multi-scheduler HA). Both api-server
    and scheduler need the same secret.

    Historical note: pre-Airflow-3 this lived at [webserver] secret_key;
    early drafts of this service used AIRFLOW__WEBSERVER__SECRET_KEY and
    it was a silent no-op (the [webserver] section was retired alongside
    the `airflow webserver` subcommand). The test asserts the canonical
    3.x name to lock against regression.
    """
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    for svc_name in ("airflow-webserver", "airflow-scheduler"):
        env = doc["services"][svc_name]["environment"]
        assert "AIRFLOW__API__SECRET_KEY" in env, (
            f"{svc_name} is missing AIRFLOW__API__SECRET_KEY in its "
            f"compose env block. Airflow 3.x requires this for inter-process "
            f"signed payloads; missing it breaks deferrable triggers and HA."
        )
        # Must reference the auto-generated env var, not a literal.
        assert env["AIRFLOW__API__SECRET_KEY"] == "${AIRFLOW_SECRET_KEY}", (
            f"{svc_name}.AIRFLOW__API__SECRET_KEY should be "
            f"${{AIRFLOW_SECRET_KEY}}, not {env['AIRFLOW__API__SECRET_KEY']!r}"
        )


def test_airflow_webserver_uses_fab_auth_manager_for_basic_auth():
    """Airflow 3.x defaults to SimpleAuthManager. The Web UI authentication
    surface (FAB session cookie at `/login/`) needs explicit FabAuthManager
    + the FAB-section basic_auth backend; without those, the Web UI logs
    users in via SimpleAuthManager's password-token flow which doesn't
    match the seeded `admin` user.

    History:
    - Pass 9 caught: AIRFLOW__API__AUTH_BACKENDS (legacy 2.x name) was
      silently ignored — Airflow 3.x renamed the section to [fab].
    - Pass 14 caught: the public REST API at `/api/v2/` is JWT-ONLY
      (`/auth/token` exchange). FAB+basic_auth governs LEGACY FAB
      endpoints and Web-UI sessions, NOT `/api/v2/`. So these env
      vars stay in place for the UI; the README curl examples switched
      to the two-step JWT pattern.
    """
    doc = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    env = doc["services"]["airflow-webserver"]["environment"]
    assert env.get("AIRFLOW__CORE__AUTH_MANAGER", "").endswith("FabAuthManager"), (
        "airflow-webserver must set AIRFLOW__CORE__AUTH_MANAGER to "
        "FabAuthManager — SimpleAuthManager (the 3.x default) does not "
        "support HTTP basic auth, which the README + Hermes integration use."
    )
    assert "AIRFLOW__FAB__AUTH_BACKENDS" in env, (
        "AIRFLOW__FAB__AUTH_BACKENDS missing — Airflow 3.x moved this from "
        "[api] auth_backends to [fab] auth_backends. The [api] env var is "
        "silently ignored; without the [fab] version, basic_auth is unwired."
    )
    assert "basic_auth" in env["AIRFLOW__FAB__AUTH_BACKENDS"]
    # The deprecated [api] form should NOT exist — its presence would
    # signal someone reverted without realizing it's a no-op in 3.x.
    assert "AIRFLOW__API__AUTH_BACKENDS" not in env, (
        "AIRFLOW__API__AUTH_BACKENDS is a no-op in Airflow 3.x; use "
        "AIRFLOW__FAB__AUTH_BACKENDS instead. Remove the deprecated var."
    )
