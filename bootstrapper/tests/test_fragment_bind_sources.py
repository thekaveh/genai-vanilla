"""Static guard against the `services/<X>/services/<X>/` doubled-path
regression that broke the observability bundle in PR #29.

Compose v2's `include:` directive resolves relative paths in an included
fragment relative to the **fragment's own directory**, not the parent
compose file. A fragment at `services/<X>/compose.yml` that writes a
source like `./services/<X>/config/foo.yml` — expecting repo-root
resolution — silently produces:

    services/<X>/services/<X>/config/foo.yml

On first launch Docker auto-creates the missing source as a *directory*,
and the SECOND launch fails with `not a directory` because the mount
target expects a file. PR #29 shipped exactly this bug for both
`services/prometheus/compose.yml` and `services/grafana/compose.yml`,
and `test_fragment_equivalence.py` happily passed it because the
committed baseline contained the same doubled paths.

This test catches the regression class by direct structural pattern
match: a source whose resolved path contains `services/<X>/services/<X>/`
is fundamentally never correct. The check runs without Docker (lives in
the existing unit-test CI job) and is independent of any baseline, so a
buggy fragment cannot pass by accidentally matching a buggy fixture.

Why not check that every resolved path *exists* on disk? Several
fragments legitimately mount runtime-generated paths that aren't on disk
in a fresh checkout (litellm's `volumes/litellm/config.yaml`, neo4j's
`build/snapshot`, supabase's `db/snapshot`, kong's
`volumes/api/kong-dynamic.yml`). An existence check produces false
positives for those without catching anything the structural check
misses for the PR #29 class.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES_ROOT = REPO_ROOT / "services"


def _iter_fragment_files() -> list[Path]:
    return sorted(SERVICES_ROOT.glob("*/compose.yml"))


def _iter_bind_sources(fragment_path: Path):
    """Yield (service_name, raw_source, resolved_path) for every relative
    bind-mount source declared in the fragment.

    Skips named volumes, host-absolute paths, and `${VAR}` interpolations
    — none of those expose the doubling-bug surface.
    """
    doc = yaml.safe_load(fragment_path.read_text(encoding="utf-8")) or {}
    fragment_dir = fragment_path.parent

    for svc_name, svc_block in (doc.get("services") or {}).items():
        for entry in svc_block.get("volumes") or []:
            # Compose accepts short-form ("./a:/b:ro") or long-form
            # ({"type": "bind", "source": "./a", "target": "/b"}).
            if isinstance(entry, dict):
                if entry.get("type") not in (None, "bind"):
                    continue
                raw = entry.get("source")
            elif isinstance(entry, str):
                raw = entry.split(":", 1)[0]
            else:
                continue

            if not raw:
                continue
            if raw.startswith("/") or raw.startswith("${"):
                continue
            if not (raw.startswith("./") or raw.startswith("../")):
                # Bare names like "prometheus-data" — that's a named volume.
                continue

            yield svc_name, raw, (fragment_dir / raw).resolve()


@pytest.mark.parametrize(
    "fragment", _iter_fragment_files(), ids=lambda p: p.parent.name
)
def test_fragment_bind_sources_dont_self_double(fragment: Path) -> None:
    """No bind-mount source in `fragment` resolves to a path that contains
    `services/<X>/services/<X>/`, where `<X>` is the fragment's own
    directory name. See module docstring for the failure mode.
    """
    svc_dir_name = fragment.parent.name
    self_doubling_marker = f"services/{svc_dir_name}/services/{svc_dir_name}/"

    offenders: list[str] = []
    for svc_name, raw, resolved in _iter_bind_sources(fragment):
        if self_doubling_marker in str(resolved):
            offenders.append(f"  - {svc_name}: '{raw}' → {resolved}")

    if offenders:
        rel = fragment.relative_to(REPO_ROOT)
        joined = "\n".join(offenders)
        pytest.fail(
            f"{rel}: bind-mount source(s) produce a doubled "
            f"`services/{svc_dir_name}/services/{svc_dir_name}/` path.\n"
            f"Compose v2 resolves relative paths in included fragments "
            f"from the fragment's own directory "
            f"({fragment.parent.relative_to(REPO_ROOT)}/), NOT the repo "
            f"root. Strip the leading `services/{svc_dir_name}/` from "
            f"each offending source:\n{joined}"
        )


def test_at_least_one_fragment_has_relative_bind_sources() -> None:
    """Sanity check that iteration discovered some bind-mount sources —
    otherwise the parametrised test above would pass vacuously across
    every fragment if `_iter_bind_sources` regressed to yielding nothing.
    """
    total = sum(
        1
        for fragment in _iter_fragment_files()
        for _ in _iter_bind_sources(fragment)
    )
    assert total > 0, (
        "No relative bind-mount sources found across any fragment — "
        "the discovery logic in _iter_bind_sources is likely broken."
    )
