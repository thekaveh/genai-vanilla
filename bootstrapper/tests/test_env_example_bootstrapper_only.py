"""Tests for the `bootstrapper_only: true` field on env entries.

When set, the var is not emitted into .env.example (it is only meaningful
to the host-side bootstrapper; compose interpolation never reads it).
"""
from __future__ import annotations

from services.env_assembler import assemble_env_example
from services.manifests import EnvVarDecl, Manifest


def _manifest(env: list[EnvVarDecl]) -> Manifest:
    """Return a minimal Manifest with the given env list."""
    return Manifest(name="fake", label="Fake", category="data", env=env)


def test_bootstrapper_only_var_excluded():
    """A var with bootstrapper_only=True must not appear in .env.example output."""
    m = _manifest([
        EnvVarDecl(name="FAKE_NORMAL", default="x"),
        EnvVarDecl(name="FAKE_BOOTSTRAPPER", default="y", bootstrapper_only=True),
    ])
    out = assemble_env_example([m])
    assert "FAKE_NORMAL=" in out
    assert "FAKE_BOOTSTRAPPER" not in out


def test_normal_var_emitted():
    """A plain env var (no special flags) is always emitted."""
    m = _manifest([EnvVarDecl(name="NORMAL", default="z")])
    out = assemble_env_example([m])
    assert "NORMAL=z" in out


def test_bootstrapper_only_does_not_affect_surrounding_vars():
    """Presence of a bootstrapper_only entry must not suppress surrounding vars."""
    m = _manifest([
        EnvVarDecl(name="BEFORE", default="1"),
        EnvVarDecl(name="SKIP_ME", default="x", bootstrapper_only=True),
        EnvVarDecl(name="AFTER", default="2"),
    ])
    out = assemble_env_example([m])
    assert "BEFORE=1" in out
    assert "SKIP_ME" not in out
    assert "AFTER=2" in out
    assert out.index("BEFORE=1") < out.index("AFTER=2")
