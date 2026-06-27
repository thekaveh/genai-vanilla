# bootstrapper/tests/test_lightrag_config.py
"""Tests for _generate_lightrag_config()."""
from __future__ import annotations

from unittest.mock import MagicMock

from services.service_config import ServiceConfig


_BASE_ENV = {
    "PROJECT_NAME": "atlas",
    "LIGHTRAG_LOCALHOST_PORT": "63068",
}


def _make(source: str) -> ServiceConfig:
    sc = ServiceConfig(config_parser=MagicMock())
    sc.localhost_host = "localhost"
    sc.service_sources = {"LIGHTRAG_SOURCE": source}
    sc.config_parser.parse_env_file.return_value = dict(_BASE_ENV)
    return sc


def test_disabled_clears_endpoint_and_scales():
    sc = _make("disabled")
    env = sc._generate_lightrag_config()
    assert env["LIGHTRAG_ENDPOINT"] == ""
    assert env["LIGHTRAG_SCALE"] == "0"
    assert env["LIGHTRAG_INIT_SCALE"] == "0"


def test_container_endpoint_and_scales():
    sc = _make("container")
    env = sc._generate_lightrag_config()
    assert env["LIGHTRAG_ENDPOINT"] == "http://lightrag:9621"
    assert env["LIGHTRAG_SCALE"] == "1"
    assert env["LIGHTRAG_INIT_SCALE"] == "1"


def test_localhost_uses_LIGHTRAG_LOCALHOST_PORT():
    sc = _make("localhost")
    env = sc._generate_lightrag_config()
    assert env["LIGHTRAG_ENDPOINT"] == "http://localhost:63068"
    assert env["LIGHTRAG_SCALE"] == "0"
    assert env["LIGHTRAG_INIT_SCALE"] == "0"


def test_init_waits_for_postgres_before_pgvector_migration():
    """supabase-db is SOURCE-replaceable, so lightrag-init must NOT hard
    depend_on it in compose — it polls the Postgres endpoint for readiness in
    the script instead. Guard that the readiness poll precedes the migration so
    the pgvector step can't race supabase-db readiness (regression guard)."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    script = (repo / "services/lightrag/init/scripts/init-lightrag.sh").read_text(
        encoding="utf-8"
    )
    poll_at = script.find("SELECT 1")
    migrate_at = script.find("migrate-pgvector.sql")
    assert poll_at != -1, "lightrag-init must poll Postgres readiness (SELECT 1)"
    assert migrate_at != -1, "lightrag-init must run the pgvector migration"
    assert poll_at < migrate_at, (
        "the Postgres readiness poll must come BEFORE the pgvector migration"
    )
