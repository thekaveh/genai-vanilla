"""App-level behavior in main.py: research/start user_id validation and the
lifespan shutdown that closes the long-lived n8n client.

Backend has no auth dependency (Kong gates external access at the edge),
so these tests don't override any auth dependency.
"""

from __future__ import annotations

import os

import pytest


def _stub_required_env(monkeypatch):
    """main.py validates a few env vars at import time; provide stubs so
    `from main import app` works without a running stack."""
    for var, default in (
        ("KONG_URL", "http://kong-api-gateway:8000"),
        ("SUPABASE_SERVICE_KEY", "dummy-key"),
        ("DATABASE_URL", "postgresql://x:x@localhost/x"),
    ):
        if not os.environ.get(var):
            monkeypatch.setenv(var, default)


def test_research_start_rejects_non_uuid_user_id(monkeypatch):
    """POST /research/start with a non-UUID user_id returns a clean 400,
    not an opaque 500 from UUID() deep inside research_service."""
    _stub_required_env(monkeypatch)
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.post(
        "/research/start",
        json={"query": "anything", "user_id": "not-a-uuid"},
    )
    assert resp.status_code == 400
    assert "user_id" in resp.json()["detail"]


def test_lifespan_closes_n8n_client(monkeypatch):
    """App shutdown awaits n8n_client.aclose() so httpx doesn't leak the
    process-lifetime client on reload/shutdown."""
    _stub_required_env(monkeypatch)
    from fastapi.testclient import TestClient
    import main

    closed = {"v": False}

    async def fake_aclose():
        closed["v"] = True

    monkeypatch.setattr(main.n8n_client, "aclose", fake_aclose)
    # Entering and exiting the context manager runs lifespan startup +
    # shutdown.
    with TestClient(main.app):
        pass
    assert closed["v"] is True
