"""Regression: ollama-pull retries a transient model-pull failure.

A default-active model (e.g. `qwen3-embedding:0.6b`) that hits a transient
registry/network blip must not be left unpulled after a single attempt.
`services/ollama/pull/scripts/pull.sh` wraps each model pull in a bounded retry
loop and only logs the terminal ERROR after all attempts fail — staying
non-fatal so the rest of the set still pulls. Shell scripts are not executed in
this suite, so this guards the retry structure by content (same approach as the
lightrag-init readiness guard).
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PULL_SH = REPO_ROOT / "services" / "ollama" / "pull" / "scripts" / "pull.sh"


def _src() -> str:
    return PULL_SH.read_text(encoding="utf-8")


def test_pull_has_bounded_retry_loop():
    src = _src()
    assert "max_attempts=3" in src, "pull.sh must cap the number of pull attempts"
    assert 'while [ "$attempt" -le "$max_attempts" ]' in src, "missing bounded retry loop"
    assert "/api/pull" in src
    assert "sleep" in src, "retries should back off between attempts"


def test_pull_retry_checks_both_exit_code_and_error_body():
    src = _src()
    # /api/pull can report failure in the NDJSON body with HTTP 200, so a
    # success must require BOTH a clean exit code AND no "error" line.
    assert '"$curl_exit_code" -eq 0' in src
    assert "grep -q '\"error\"'" in src
    assert "pulled=1" in src


def test_pull_failure_is_non_fatal_after_retries():
    src = _src()
    assert "after $max_attempts attempts" in src, "terminal ERROR must follow the retries"
    # The per-model failure branch logs and continues — it must NOT abort the
    # whole pull set, and the script always reaches its completion line.
    fail_branch = src.split('if [ "$pulled" -ne 1 ]; then', 1)[1].split("fi", 1)[0]
    assert "exit" not in fail_branch, "a failed pull must not exit the script"
    assert "Finished model pulling process" in src
