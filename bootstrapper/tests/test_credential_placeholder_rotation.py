"""Credential placeholder rotation: `.env.example` ships well-known
defaults (``password``, ``redis_password``, ``neo4j_password``,
``kong_password``, ``admin``, ``your-random-encryption-key``,
``app_password``, ``secret``) that the key-generator must upgrade to a
real value on the first ``./start.sh``. Without these, ``cp .env.example
.env && ./start.sh`` boots the stack with credentials anyone can read
from the public repo.

These tests exercise the bootstrapper end of the rotation: every
``generate_and_update_*`` rotator covered by ``PLACEHOLDER_DEFAULTS``
must replace the placeholder, preserve a hand-supplied real value, and
(for the composite ``GRAPH_DB_AUTH=neo4j/<password>``) keep the derived
form in sync.
"""
from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from utils.key_generator import KeyGenerator


# (env_var, placeholder, rotator_method_name)
ROTATORS = [
    ("N8N_ENCRYPTION_KEY", "your-random-encryption-key", "generate_and_update_n8n_key"),
    ("SUPABASE_DB_PASSWORD", "password", "generate_and_update_supabase_db_password"),
    ("SUPABASE_DB_APP_PASSWORD", "app_password", "generate_and_update_supabase_db_app_password"),
    ("GRAPH_DB_PASSWORD", "neo4j_password", "generate_and_update_graph_db_password"),
    ("REDIS_PASSWORD", "redis_password", "generate_and_update_redis_password"),
    ("DASHBOARD_PASSWORD", "kong_password", "generate_and_update_kong_dashboard_password"),
    ("OPEN_WEB_UI_ADMIN_PASSWORD", "admin", "generate_and_update_webui_admin_password"),
    ("OPEN_WEB_UI_SECRET_KEY", "secret", "generate_and_update_webui_secret_key"),
]


def _seed_env(tmp_path: Path, body: str) -> Path:
    env = tmp_path / ".env"
    env.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return env


@pytest.mark.parametrize("var,placeholder,method", ROTATORS)
def test_placeholder_is_rotated(tmp_path, var, placeholder, method):
    _seed_env(tmp_path, f"{var}={placeholder}\n")
    kg = KeyGenerator(str(tmp_path))
    assert getattr(kg, method)() is True
    new_value = kg.get_current_env_value(var)
    assert new_value, f"{var} not written"
    assert new_value != placeholder, (
        f"{var}: placeholder {placeholder!r} survived rotation"
    )


@pytest.mark.parametrize("var,placeholder,method", ROTATORS)
def test_hand_supplied_value_is_preserved(tmp_path, var, placeholder, method):
    real = "operator-supplied-real-value-9c3f"
    _seed_env(tmp_path, f"{var}={real}\n")
    kg = KeyGenerator(str(tmp_path))
    assert getattr(kg, method)() is True
    assert kg.get_current_env_value(var) == real, (
        f"{var}: real hand-supplied value was overwritten"
    )


def test_graph_db_auth_stays_in_sync_with_password(tmp_path):
    """`services/neo4j/compose.yml` passes the literal `GRAPH_DB_AUTH`
    string to `NEO4J_AUTH`. Rotating `GRAPH_DB_PASSWORD` without
    rewriting the composite leaves Neo4j authenticating against the
    stale embedded password.
    """
    _seed_env(
        tmp_path,
        """
        GRAPH_DB_USER=neo4j
        GRAPH_DB_PASSWORD=neo4j_password
        GRAPH_DB_AUTH=neo4j/neo4j_password
        """,
    )
    kg = KeyGenerator(str(tmp_path))
    assert kg.generate_and_update_graph_db_password() is True
    new_pw = kg.get_current_env_value("GRAPH_DB_PASSWORD")
    assert new_pw and new_pw != "neo4j_password"
    assert kg.get_current_env_value("GRAPH_DB_AUTH") == f"neo4j/{new_pw}"


def test_generate_missing_keys_covers_all_placeholder_vars(tmp_path):
    """End-to-end: the aggregator generates every placeholder var."""
    body = "\n".join(
        f"{var}={placeholder}" for var, placeholder, _ in ROTATORS
    ) + "\n"
    _seed_env(tmp_path, body)
    kg = KeyGenerator(str(tmp_path))
    results = kg.generate_missing_keys(force_regenerate=False)
    for var, placeholder, _ in ROTATORS:
        assert results.get(var) is True, f"{var} not in results / failed"
        assert kg.get_current_env_value(var) != placeholder, (
            f"{var}: aggregator did not upgrade placeholder"
        )
