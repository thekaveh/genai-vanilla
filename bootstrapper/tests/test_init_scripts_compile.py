"""Every Python init script under `services/*/init/scripts/*.py` must
parse cleanly via `py_compile`.

The init container is the production loader — Python imports those
files at container start. A purely-syntactic error (duplicate kwarg,
unclosed paren, mistyped indent) lives undetected until `docker
compose up`, because nothing in the local pytest suite imports them
(they live outside the bootstrapper package). PR #67's
`fix(open-webui): timeouts + try/finally cleanup` introduced a
duplicate `timeout=30` kwarg in `register-tools.py:create_admin_user`;
the script crashed at module-import time on every open-webui-init
boot until 2026-06-08 when the audit caught it. This test is the
permanent guard.

Tests intentionally use `py_compile.compile` (not `importlib`) so they
do NOT execute module-top-level code (init scripts read DATABASE_URL,
WEBUI_SECRET_KEY, etc. at import time and would crash in a clean
bootstrapper venv).
"""
from __future__ import annotations

import py_compile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _discover_init_scripts() -> list[Path]:
    return sorted(REPO_ROOT.glob("services/*/init/scripts/*.py"))


@pytest.mark.parametrize(
    "script_path",
    _discover_init_scripts(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_init_script_compiles(script_path: Path) -> None:
    """The script must pass `py_compile` — catches syntax-class bugs
    (duplicate kwargs, missing parens, mistyped indent) without
    executing any module-top-level code.
    """
    try:
        py_compile.compile(str(script_path), doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(
            f"{script_path.relative_to(REPO_ROOT)} does not parse:\n{e.msg}"
        )


def test_at_least_one_script_discovered() -> None:
    """Belt-and-suspenders: if the glob ever returns nothing (the
    `services/*/init/scripts/` layout changed), this test fails loudly
    instead of trivially passing with zero parametrized cases.
    """
    scripts = _discover_init_scripts()
    assert scripts, (
        "No init scripts discovered under services/*/init/scripts/*.py — "
        "the layout may have changed; update this test's glob."
    )
