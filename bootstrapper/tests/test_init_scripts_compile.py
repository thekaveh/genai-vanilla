"""Every Python init script under `services/*/init/scripts/*.py` must
parse cleanly via `py_compile`; every shell init script under
`services/*/init/scripts/*.sh` must parse cleanly via `bash -n`.

The init container is the production loader — Python imports / bash
sources those files at container start. A purely-syntactic error
(duplicate kwarg, unclosed paren, mistyped indent, missing `fi`) lives
undetected until `docker compose up`, because nothing in the local
pytest suite imports them (they live outside the bootstrapper package).

PR #67's `fix(open-webui): timeouts + try/finally cleanup` introduced a
duplicate `timeout=30` kwarg in `register-tools.py:create_admin_user`;
the script crashed at module-import time on every open-webui-init
boot until 2026-06-08 when the audit caught it. This test is the
permanent guard.

Tests intentionally use `py_compile.compile` (not `importlib`) so they
do NOT execute module-top-level code (init scripts read DATABASE_URL,
WEBUI_SECRET_KEY, etc. at import time and would crash in a clean
bootstrapper venv). Bash scripts use `bash -n` for the same reason
(parse-only, no execution).
"""
from __future__ import annotations

import ast
import py_compile
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _discover_init_scripts() -> list[Path]:
    return sorted(REPO_ROOT.glob("services/*/init/scripts/*.py"))


def _discover_shell_init_scripts() -> list[Path]:
    return sorted(REPO_ROOT.glob("services/*/init/scripts/*.sh"))


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


@pytest.mark.parametrize(
    "script_path",
    _discover_shell_init_scripts(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_shell_init_script_parses(script_path: Path) -> None:
    """Every `.sh` init script must pass `bash -n` (parse-only).
    Catches unclosed `if`/`for`/`while`, mismatched quotes, missing
    `fi`/`done`. Skipped if `bash` is not on PATH (Windows CI).
    """
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not on PATH")
    result = subprocess.run(
        [bash, "-n", str(script_path)],
        capture_output=True, text=True, check=False, timeout=10,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, (
        f"{script_path.relative_to(REPO_ROOT)} does not parse:\n"
        f"{result.stderr}"
    )


@pytest.mark.parametrize(
    "script_path",
    _discover_init_scripts(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_init_script_no_duplicate_keyword_args(script_path: Path) -> None:
    """AST-walk every `Call` node, assert no keyword name appears twice in
    the same call.

    Belt-and-suspenders against the PR #67 duplicate `timeout=30` bug
    class. `py_compile` (in `test_init_script_compiles`) already catches
    duplicate kwargs with a `SyntaxError: keyword argument repeated: X`,
    but this AST test gives a clearer per-script failure message that
    names the duplicated kwarg, the line number, and the function being
    called — easier to triage than a bare SyntaxError from the parser.
    """
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kwarg_names = [k.arg for k in node.keywords if k.arg is not None]
        seen: set[str] = set()
        for name in kwarg_names:
            if name in seen:
                violations.append(
                    f"  line {node.lineno}: duplicate kwarg '{name}' "
                    f"on Call to {ast.dump(node.func)[:60]}"
                )
            seen.add(name)
    assert not violations, (
        f"{script_path.relative_to(REPO_ROOT)} has duplicate kwargs:\n"
        + "\n".join(violations)
    )
