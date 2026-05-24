"""Tests for /api/ray/* (services/backend/app/app/ray_routes.py).

Covers:
- 503 on disabled: when RAY_ADDRESS empty, every endpoint returns 503.
- 200 on enabled: submit returns job_id, status returns status payload, etc.
- 422 on invalid payloads.

Note: Backend has no auth dependency (Kong gates external access at the
edge), so these tests don't override an auth dependency on the FastAPI app.
"""

from __future__ import annotations

import sys
import types

import pytest

# Pre-stub the `ray` package so that `monkeypatch.setattr("ray.job_submission.JobSubmissionClient", ...)`
# can resolve the dotted path without requiring a real ray installation.
# This must happen at import time (module level) — before conftest fixtures run.
if "ray" not in sys.modules:
    _ray_stub = types.ModuleType("ray")
    _ray_job_stub = types.ModuleType("ray.job_submission")
    _ray_job_stub.JobSubmissionClient = None  # placeholder; tests override this via monkeypatch
    _ray_stub.job_submission = _ray_job_stub
    sys.modules["ray"] = _ray_stub
    sys.modules["ray.job_submission"] = _ray_job_stub


def test_submit_returns_503_when_ray_disabled(monkeypatch):
    """Override env directly + reset singleton; can't use ray_disabled_env
    + fastapi_client together because they conflict (one enables, one
    disables)."""
    monkeypatch.setenv("RAY_ADDRESS", "")
    monkeypatch.delenv("RAY_DASHBOARD_URL", raising=False)
    # Provide stub values for env vars main.py validates at import time.
    import os as _os
    for _var, _default in (
        ("KONG_URL", "http://kong:8000"),
        ("SUPABASE_SERVICE_KEY", "dummy-key"),
        ("DATABASE_URL", "postgresql://x:x@localhost/x"),
    ):
        if not _os.environ.get(_var):
            monkeypatch.setenv(_var, _default)
    import ray_client
    ray_client.RayClient._instance = None

    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    resp = client.post("/api/ray/jobs/submit", json={"entrypoint": "echo hi"})
    assert resp.status_code == 503, resp.text
    body = resp.json()["detail"].lower()
    assert "not set" in body or "disabled" in body


def test_submit_returns_200_when_ray_enabled(fastapi_client, mock_job_submission_client):
    mock_instance = mock_job_submission_client.return_value
    mock_instance.submit_job.return_value = "raysubmit_abc"
    resp = fastapi_client.post(
        "/api/ray/jobs/submit",
        json={"entrypoint": "python -c 'print(1)'"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"job_id": "raysubmit_abc"}


def test_get_status_returns_200_when_enabled(fastapi_client, mock_job_submission_client):
    from types import SimpleNamespace
    mock_instance = mock_job_submission_client.return_value
    mock_instance.get_job_status.return_value = SimpleNamespace(value="RUNNING")
    mock_instance.get_job_info.return_value = SimpleNamespace(__dict__={"status": "RUNNING"})
    resp = fastapi_client.get("/api/ray/jobs/raysubmit_abc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "raysubmit_abc"
    assert body["status"] == "RUNNING"


def test_stop_job_returns_200_when_enabled(fastapi_client, mock_job_submission_client):
    mock_instance = mock_job_submission_client.return_value
    mock_instance.stop_job.return_value = True
    resp = fastapi_client.delete("/api/ray/jobs/raysubmit_abc")
    assert resp.status_code == 200
    assert resp.json() == {"stopped": True}


def test_invalid_payload_returns_422(fastapi_client):
    """Missing the required `entrypoint` field → FastAPI returns 422 unprocessable."""
    resp = fastapi_client.post("/api/ray/jobs/submit", json={})
    assert resp.status_code == 422
