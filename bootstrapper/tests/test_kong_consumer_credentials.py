"""Regression tests for Kong's ``dashboard_user`` consumer.

Two production bugs the consumer block has to guard against:

1. **No ``${VAR}`` substitution in Kong DB-less declarative config.**
   The YAML loaded via ``KONG_DECLARATIVE_CONFIG`` is read literally —
   if the credentials are emitted as ``${DASHBOARD_USERNAME}`` /
   ``${DASHBOARD_PASSWORD}``, Kong stores those literal strings and
   any real-credential login attempt returns 401.

2. **ACL plugin checks group membership, not consumer username.** A
   route with ``acl: { allow: [dashboard_user] }`` lets through any
   consumer that belongs to the ``dashboard_user`` GROUP — not the
   consumer NAMED ``dashboard_user``. The consumer must carry an
   explicit ``acls: [{group: dashboard_user}]`` entry. Without it,
   basic-auth succeeds and ACL returns 403 anyway.

Both issues were observed live on the Ray dashboard route: passing the
literal placeholder strings got past basic-auth (401 → 403), and
passing the real credentials was rejected (still 401).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_parser import ConfigParser
from utils.kong_config_generator import KongConfigGenerator


@pytest.fixture
def consumers(tmp_path: Path) -> list[dict]:
    """Build the consumer block via the live generator + an .env stub.

    Doesn't write the kong-dynamic.yml — we only need the dict that the
    generator would write so we can assert on its shape.
    """
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DASHBOARD_USERNAME=alice_admin\n"
        "DASHBOARD_PASSWORD=s3cret-p@ss\n",
        encoding="utf-8",
    )
    cp = ConfigParser(str(tmp_path))
    cp.env_file_path = env_path
    cp.parse_env_file()
    gen = KongConfigGenerator(cp)
    # The generator caches env vars in its own internal dict; loaded
    # lazily by ``generate_kong_config`` in production. ``get_consumers``
    # in isolation expects that load to have happened.
    gen.load_environment_variables()
    return gen.get_consumers()


def test_consumers_block_has_a_single_dashboard_user(consumers):
    assert len(consumers) == 1
    assert consumers[0]["username"] == "dashboard_user"


def test_basic_auth_credentials_are_resolved_from_env(consumers):
    """Literal env values — NOT ``${...}`` shell-style placeholders."""
    creds = consumers[0]["basicauth_credentials"]
    assert len(creds) == 1
    assert creds[0]["username"] == "alice_admin"
    assert creds[0]["password"] == "s3cret-p@ss"
    # Belt and suspenders: explicitly check the placeholder strings
    # are gone. If a future refactor reintroduces them, this fails
    # with a more readable assertion than "expected X, got '${DASH…'".
    for field in ("username", "password"):
        assert "${" not in creds[0][field], (
            f"basicauth_credentials[{field!r}] contains an un-substituted "
            f"${{VAR}} placeholder: {creds[0][field]!r}. Kong's DB-less "
            f"declarative config does NOT interpolate shell-style env "
            f"refs — resolve from .env in the generator instead."
        )


def test_consumer_carries_dashboard_user_acl_group_membership(consumers):
    """ACL plugin checks group membership, not consumer username.

    Without an ``acls`` entry, every route guarded by
    ``acl: { allow: [dashboard_user] }`` returns 403 even when
    basic-auth succeeds. The Ray dashboard route exhibited this exact
    failure mode in the wild.
    """
    acls = consumers[0].get("acls", [])
    assert isinstance(acls, list) and len(acls) >= 1, (
        "dashboard_user consumer is missing its acls block — every "
        "basic-auth-protected route also runs the ACL plugin and will "
        "403 without explicit group membership."
    )
    groups = [entry.get("group") for entry in acls]
    assert "dashboard_user" in groups, (
        f"Expected the dashboard_user consumer to belong to the "
        f"'dashboard_user' ACL group. Got: {groups}"
    )


def test_defaults_used_when_env_vars_missing(tmp_path: Path):
    """When .env doesn't set DASHBOARD_USERNAME / DASHBOARD_PASSWORD,
    the generator falls back to the documented defaults (matching
    .env.example) instead of crashing or emitting None."""
    env_path = tmp_path / ".env"
    env_path.write_text("# intentionally empty\n", encoding="utf-8")
    cp = ConfigParser(str(tmp_path))
    cp.env_file_path = env_path
    cp.parse_env_file()
    gen = KongConfigGenerator(cp)
    gen.load_environment_variables()
    creds = gen.get_consumers()[0]["basicauth_credentials"][0]
    assert creds["username"] == "kong_admin"
    assert creds["password"] == "kong_password"
