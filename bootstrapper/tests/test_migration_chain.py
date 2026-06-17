"""End-to-end .env migration chain (v0 -> v1 -> v2 -> v3).

Each migration step is unit-tested in isolation (test_port_migration,
test_migration_v2, test_migration_v3), but their *composition* on a
single legacy v0 .env -- the exact upgrade path for a user on an old
checkout who hasn't run the bootstrapper since the topology refactor --
was not. ``run_port_migration`` chains the three steps behind sequential
``_needs_vN`` gates; this test feeds one legacy file through a single
call and asserts all three sentinels advance and every schema rewrite
lands.
"""

from __future__ import annotations

from pathlib import Path

from services.migrations.migration_v1 import V0_OFFSETS
from services.migrations.migration_v1 import needs_migration as needs_v1
from services.migrations.migration_v2 import needs_migration as needs_v2
from services.migrations.migration_v3 import needs_migration as needs_v3


def _legacy_v0_env(tmp_path: Path) -> Path:
    """A v0 .env: no layout sentinel, a port at its v0 default, a legacy
    ``*_LOCALHOST_URL`` line (v2 fodder), and ``COMFYUI_MODEL_SET`` (v3)."""
    port_var, offset = next(iter(V0_OFFSETS.items()))
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "BASE_PORT=63000",
                f"{port_var}={63000 + offset}",
                "COMFYUI_LOCALHOST_URL=http://localhost:11434",
                "COMFYUI_MODEL_SET=sdxl",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return env


def test_v0_env_migrates_through_the_full_chain(tmp_path):
    env = _legacy_v0_env(tmp_path)
    (tmp_path / ".env.example").write_text("BASE_PORT=63000\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    # Sanity: a true v0 file needs all three migrations before we start.
    assert needs_v1(env) and needs_v2(env) and needs_v3(env)

    from start import AtlasStarter

    starter = AtlasStarter()
    starter.config_parser.env_file_path = env
    starter.config_parser.env_example_path = tmp_path / ".env.example"

    starter.run_port_migration(no_port_migrate=False)

    # The composition invariant: every step's sentinel advanced, so the
    # chain ran end to end in order.
    assert not needs_v1(env)
    assert not needs_v2(env)
    assert not needs_v3(env)

    text = env.read_text(encoding="utf-8")
    # v2: URL schema rewritten to the PORT schema.
    assert "COMFYUI_LOCALHOST_PORT" in text
    # v3: old enum translated and removed.
    assert "COMFYUI_MODEL_SET=" not in text
    assert "COMFYUI_USER_MODELS" in text


def test_chain_is_idempotent_on_second_run(tmp_path):
    """A second ``run_port_migration`` on the already-migrated file is a
    no-op: the sentinels stay at their terminal state."""
    env = _legacy_v0_env(tmp_path)
    (tmp_path / ".env.example").write_text("BASE_PORT=63000\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    from start import AtlasStarter

    starter = AtlasStarter()
    starter.config_parser.env_file_path = env
    starter.config_parser.env_example_path = tmp_path / ".env.example"

    starter.run_port_migration(no_port_migrate=False)
    first = env.read_text(encoding="utf-8")
    starter.run_port_migration(no_port_migrate=False)
    second = env.read_text(encoding="utf-8")

    assert first == second
    assert not (needs_v1(env) or needs_v2(env) or needs_v3(env))
