"""Port-layout v0 → v1 migration tests."""

from __future__ import annotations

from pathlib import Path
import pytest


def _write_env(tmp_path: Path, contents: str) -> Path:
    env = tmp_path / ".env"
    env.write_text(contents)
    return env


def test_all_defaults_get_rewritten(tmp_path):
    """A .env at all v0 defaults rewrites every port to its v1 slot."""
    from services.migrations.migration_v1 import apply, V0_OFFSETS
    new_defaults = {var: 63000 + i + 100 for i, var in enumerate(V0_OFFSETS)}
    env_path = _write_env(
        tmp_path,
        "\n".join(f"{var}={63000 + off}" for var, off in V0_OFFSETS.items()) + "\n",
    )
    result = apply(env_path, new_defaults, base_port=63000)
    assert set(result.rewritten.keys()) == set(V0_OFFSETS.keys())
    assert result.preserved == []
    assert result.backup_path is not None and result.backup_path.is_file()


def test_customized_port_is_preserved(tmp_path):
    """User-customized port is reported in 'preserved' and not rewritten."""
    from services.migrations.migration_v1 import apply
    env_path = _write_env(tmp_path, "LITELLM_PORT=54321\n")
    new_defaults = {"LITELLM_PORT": 63030}
    result = apply(env_path, new_defaults, base_port=63000)
    assert "LITELLM_PORT" not in result.rewritten
    assert "LITELLM_PORT" in result.preserved
    assert "LITELLM_PORT=54321" in env_path.read_text()


def test_sentinel_already_at_v1_no_migration(tmp_path):
    """needs_migration() is False when the sentinel is already 1."""
    from services.migrations.migration_v1 import needs_migration
    env_path = _write_env(tmp_path, "BOOTSTRAPPER_PORT_LAYOUT_VERSION=1\nLITELLM_PORT=63012\n")
    assert needs_migration(env_path) is False


def test_missing_env_skips(tmp_path):
    """A missing .env returns MigrationResult with no changes and no backup."""
    from services.migrations.migration_v1 import apply, needs_migration
    env_path = tmp_path / ".env"
    assert needs_migration(env_path) is False
    result = apply(env_path, {"LITELLM_PORT": 63030}, base_port=63000)
    assert result.rewritten == {}
    assert result.backup_path is None


def test_idempotency(tmp_path):
    """Running apply() twice in a row is a no-op the second time."""
    from services.migrations.migration_v1 import apply, stamp_version
    env_path = _write_env(tmp_path, "LITELLM_PORT=63012\n")
    new_defaults = {"LITELLM_PORT": 63030}
    apply(env_path, new_defaults, base_port=63000)
    stamp_version(env_path, 1)
    # Second pass with already-rewritten values: nothing matches the V0 expected_old.
    result2 = apply(env_path, new_defaults, base_port=63000)
    assert result2.rewritten == {}


def test_stamp_version_appends_when_missing(tmp_path):
    """stamp_version() adds the sentinel when not present."""
    from services.migrations.migration_v1 import stamp_version
    env_path = _write_env(tmp_path, "LITELLM_PORT=63012\n")
    stamp_version(env_path, 1)
    assert "BOOTSTRAPPER_PORT_LAYOUT_VERSION=1" in env_path.read_text()
