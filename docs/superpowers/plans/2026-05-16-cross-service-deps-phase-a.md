# Cross-service deps & diagrams — Phase A (Foundations) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the doc-standardization + manifest-driven diagram generator + folder-migration foundations that Phases B and C will run against, with a CI drift gate that prevents future divergence between manifests and generated artifacts.

**Architecture:** New `bootstrapper/docs/` Python module reads each manifest's `depends_on`, `runtime_adaptive.adapts_to`, and `runtime_deps.optional`, plus inverse-edges from all other manifests, into a `DepGraph` dataclass. Two render targets share that graph: a markdown writer (`deps_section_writer`) emits the "Current — Upstream/Downstream" tables in each service README; a Jinja-style template renderer (`diagram_renderer`) emits skill-compliant HTML+SVG. A CLI (`bootstrapper/docs/regen.py`) drives both; a pytest drift gate (`test_docs_drift.py`) calls it with `--check` to fail CI when committed artifacts diverge.

**Tech Stack:** Python 3.9+, `pyyaml`, `jsonschema` (already in `bootstrapper/pyproject.toml`), pytest. Standard-library `string.Template` for the SVG/HTML templates (no new dependencies). The plan introduces no new runtime deps.

**Spec reference:** `docs/superpowers/specs/2026-05-16-cross-service-deps-and-diagrams-design.md`, sections A.1 through A.7 and the Phase A acceptance gates.

---

## File structure

**New files (created during this phase):**

```
bootstrapper/docs/
├── __init__.py
├── deps_resolver.py          # manifests → DepGraph
├── diagram_renderer.py       # DepGraph → HTML+SVG
├── deps_section_writer.py    # DepGraph → markdown tables
├── regen.py                  # CLI: python -m bootstrapper.docs.regen
└── templates/
    ├── architecture.html.tmpl
    ├── svg_defs.tmpl
    ├── svg_box.tmpl
    ├── svg_edge.tmpl
    └── deps_section.md.tmpl

bootstrapper/tests/
├── test_deps_resolver.py
├── test_deps_section_writer.py
├── test_diagram_renderer.py
├── test_docs_drift.py
├── test_doc_links.py
└── fixtures/
    ├── hermes.architecture.svg     # golden snapshot
    └── hermes.deps_section.md      # golden snapshot

scripts/
├── check_doc_links.py        # cross-doc link validator
└── migrate_docs_to_folders.py # one-shot migration runner

docs/services/<name>/
├── README.md                 # 21 files (migrated from docs/services/<name>.md)
├── architecture.html         # 21 files (generated)
└── architecture.svg          # 21 files (generated)
```

**Modified files:**

- `bootstrapper/schemas/service.schema.json` — add `runtime_adaptive[*].failure_mode` and top-level optional `doc_extras` properties.
- `bootstrapper/services/manifests.py` — add `doc_extras` field to `Manifest` dataclass.
- `services/hermes/service.yml` — demonstrate `failure_mode` on its adaptive container (single example).
- `README.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`, `docs/CONTRIBUTING-services.md`, `docs/deployment/submodule-usage.md`, `docs/security/2026-05-06-dependabot-remediation-report.md`, `docs/superpowers/specs/2026-05-12-minio-service-design.md`, `docs/superpowers/plans/2026-05-12-minio-service.md`, and the new umbrella spec from 2026-05-16 — rewrite `docs/services/<name>.md` link references to `docs/services/<name>/README.md`.
- `bootstrapper/services/manifest_validator.py` — accept the new optional fields (no new invariants required for Phase A; just don't reject them).

**Files explicitly NOT touched in this phase:**

- `services/<name>/compose.yml` files (out of scope).
- The 7 placeholder docs' body content (deferred to Phase C).
- `services/<name>/README.md` files (those are upstream project READMEs, unrelated to `docs/services/`).
- Any `runtime_sc`, `runtime_deps`, or `depends_on` content beyond the Hermes `failure_mode` example.

---

## Pre-flight

- [ ] **Step 0: Verify worktree isolation**

If you were dispatched via `superpowers:using-git-worktrees`, confirm `pwd` lands in a worktree under `.claude/worktrees/`. If working directly on main, stop and create one:

```bash
git worktree add .claude/worktrees/phase-a -b phase-a-deps-foundations
cd .claude/worktrees/phase-a
```

- [ ] **Step 1: Verify Python environment**

Run: `cd bootstrapper && uv run python -c "import yaml, jsonschema; print('ok')"`
Expected: `ok`

If `uv` is missing, fall back to `python -m pip install pyyaml jsonschema pytest` inside a virtualenv pointed at `bootstrapper/`.

- [ ] **Step 2: Baseline test run**

Run: `cd bootstrapper && uv run pytest -q`
Expected: all existing tests pass. Capture pass count for sanity-check at the end of Phase A.

---

## Task 1: Manifest schema additions

**Files:**
- Modify: `bootstrapper/schemas/service.schema.json`
- Modify: `bootstrapper/services/manifests.py`
- Test: `bootstrapper/tests/test_manifests.py` (extend existing)

**Why first:** every other module reads manifests. Schema additions must land before consumers can rely on the new fields.

- [ ] **Step 1.1: Write the failing test for `failure_mode` parsing**

Append to `bootstrapper/tests/test_manifests.py`:

```python
def test_runtime_adaptive_failure_mode_round_trips(tmp_path):
    """A manifest declaring runtime_adaptive.<container>.failure_mode must
    parse without rejection and the value must be retrievable from the
    Manifest's runtime_adaptive dict."""
    from services.manifests import load_manifests

    services_dir = tmp_path / "services"
    svc = services_dir / "foo"
    svc.mkdir(parents=True)
    (svc / "service.yml").write_text(
        """
name: foo
label: Foo
category: data
env: []
runtime_adaptive:
  foo:
    adapts_to: [other]
    failure_mode: "Foo skips its lookup; warning logged."
""".strip()
    )

    manifests = load_manifests(services_dir)
    assert len(manifests) == 1
    assert manifests[0].runtime_adaptive["foo"]["failure_mode"] == \
        "Foo skips its lookup; warning logged."


def test_doc_extras_extra_consumers_round_trips(tmp_path):
    """A manifest with doc_extras.diagram.extra_consumers must load and
    expose the list via Manifest.doc_extras."""
    from services.manifests import load_manifests

    services_dir = tmp_path / "services"
    svc = services_dir / "bar"
    svc.mkdir(parents=True)
    (svc / "service.yml").write_text(
        """
name: bar
label: Bar
category: infra
env: []
doc_extras:
  diagram:
    extra_consumers: ["openclaw", "n8n"]
""".strip()
    )

    manifests = load_manifests(services_dir)
    assert manifests[0].doc_extras == {
        "diagram": {"extra_consumers": ["openclaw", "n8n"]}
    }
```

- [ ] **Step 1.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py::test_runtime_adaptive_failure_mode_round_trips tests/test_manifests.py::test_doc_extras_extra_consumers_round_trips -v`
Expected: FAIL — `failure_mode` is rejected by schema as unknown property OR `doc_extras` AttributeError on Manifest.

- [ ] **Step 1.3: Extend `service.schema.json`**

Open `bootstrapper/schemas/service.schema.json`. Locate the `runtime_adaptive` property block (search for `"runtime_adaptive"`). The current definition is `{"type": "object"}` (opaque mapping). Replace its value with:

```json
"runtime_adaptive": {
  "type": "object",
  "additionalProperties": {
    "type": "object",
    "additionalProperties": true,
    "properties": {
      "adapts_to": {
        "type": "array",
        "items": {"type": "string"}
      },
      "environment_adaptation": {"type": "object"},
      "extra_hosts_adaptation": {"type": ["string", "array"]},
      "failure_mode": {
        "type": "string",
        "description": "Single-sentence description of what happens when this adaptive dep is disabled or unreachable. Surfaced in the Dependencies & Integrations section's Failure mode column."
      }
    }
  },
  "description": "Per-container adaptive-service descriptors. Keyed by container name in containers[]."
}
```

Then locate the top-level `properties:` block and add a new sibling property `doc_extras` (alphabetically near `docs:`):

```json
"doc_extras": {
  "type": "object",
  "additionalProperties": false,
  "description": "Optional doc-generation hints. Not consumed at runtime.",
  "properties": {
    "diagram": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "extra_consumers": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Manual escape hatch — service names to draw on the downstream tier in this service's architecture diagram, for wiring not expressible in depends_on (e.g. Kong routing)."
        }
      }
    }
  }
},
```

- [ ] **Step 1.4: Extend the `Manifest` dataclass**

Open `bootstrapper/services/manifests.py`. Locate the `Manifest` dataclass (around line 109). Append a new field after `runtime_dependency_tiers`:

```python
    doc_extras: dict = field(default_factory=dict)
```

Then locate `_load_one` (search for `def _load_one`). Add `doc_extras=data.get("doc_extras", {}),` to the `Manifest(...)` constructor call.

- [ ] **Step 1.5: Re-run tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py -v`
Expected: PASS (including the two new tests + all pre-existing tests).

- [ ] **Step 1.6: Full test sweep**

Run: `cd bootstrapper && uv run pytest -q`
Expected: same pass count as Step 2 (baseline) plus the two new tests.

- [ ] **Step 1.7: Commit**

```bash
git add bootstrapper/schemas/service.schema.json \
        bootstrapper/services/manifests.py \
        bootstrapper/tests/test_manifests.py
git commit -m "manifests: add failure_mode + doc_extras optional fields"
```

---

## Task 2: Demonstrate `failure_mode` on Hermes

**Files:**
- Modify: `services/hermes/service.yml`

**Why:** establishes the pattern with a real example. Phase C will populate the rest; this task seeds one row so the snapshot test in Task 11 has real failure-mode text to verify.

- [ ] **Step 2.1: Edit Hermes manifest**

Open `services/hermes/service.yml`. Locate `runtime_adaptive.hermes-init.adapts_to` (around line 156). Add a `failure_mode` sibling on the `hermes-init` block:

```yaml
runtime_adaptive:
  hermes-init:
    adapts_to:
    - stt_provider
    - tts_provider
    - comfyui
    - searxng
    environment_adaptation:
      TTS_INTERNAL_URL: ${TTS_ENDPOINT}
      STT_INTERNAL_URL: ${STT_ENDPOINT}
      COMFYUI_INTERNAL_URL: ${COMFYUI_ENDPOINT}
      SEARXNG_INTERNAL_URL: http://searxng:8080
    extra_hosts_adaptation: none
    failure_mode: "Capability block omitted from config.yaml; Hermes runs without it."
  hermes:
    adapts_to:
    - llm_provider
    environment_adaptation:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
    extra_hosts_adaptation: inherit from llm_provider
    failure_mode: "Hermes preflight fails (LLM provider required); container exits."
```

- [ ] **Step 2.2: Verify manifest still loads**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -q`
Expected: all pass.

- [ ] **Step 2.3: Commit**

```bash
git add services/hermes/service.yml
git commit -m "hermes: seed failure_mode strings on runtime_adaptive containers"
```

---

## Task 3: Doc-link validator (`scripts/check_doc_links.py`)

**Files:**
- Create: `scripts/check_doc_links.py`
- Create: `bootstrapper/tests/test_doc_links.py`

**Why before migration:** the validator must exist before we move 21 files. We use it pre-migration (baseline: 0 broken links) and post-migration (must still be 0).

- [ ] **Step 3.1: Write the failing test**

Create `bootstrapper/tests/test_doc_links.py`:

```python
"""Tests for scripts/check_doc_links.py — internal-markdown-link validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "check_doc_links.py"


def _run(*paths: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(VALIDATOR), *(str(p) for p in paths)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def test_validator_passes_on_clean_tree(tmp_path):
    """A directory of markdown files with valid relative links exits 0."""
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("See [B](./b.md).")
    b.write_text("See [A](./a.md).")
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_validator_flags_broken_relative_link(tmp_path):
    """A relative link that doesn't resolve exits non-zero and names the link."""
    a = tmp_path / "a.md"
    a.write_text("See [B](./b.md).")
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "b.md" in result.stdout


def test_validator_ignores_external_links(tmp_path):
    """http(s) and mailto links are not checked."""
    a = tmp_path / "a.md"
    a.write_text(
        "[ext](https://example.com)\n"
        "[mail](mailto:me@example.com)\n"
    )
    result = _run(tmp_path)
    assert result.returncode == 0


def test_validator_ignores_anchors(tmp_path):
    """Bare `#anchor` and `./file.md#anchor` links don't require anchor existence."""
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("[same](#here) [other](./b.md#section)")
    b.write_text("body")
    result = _run(tmp_path)
    assert result.returncode == 0


def test_validator_resolves_relative_paths_with_parent_segments(tmp_path):
    """`../foo.md` is resolved relative to the source file."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "child.md").write_text("[parent](../sibling.md)")
    (tmp_path / "sibling.md").write_text("body")
    result = _run(tmp_path)
    assert result.returncode == 0


def test_validator_scans_repo_default_paths():
    """When invoked with no args, validator scans README.md + docs/ + CHANGELOG.md."""
    result = _run()
    # Whatever the current state is, the script must run end-to-end (exit
    # code 0 or 1 — but never crash). This guarantees Phase A's pre-migration
    # baseline can be captured.
    assert result.returncode in (0, 1), result.stdout + result.stderr
```

- [ ] **Step 3.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_doc_links.py -v`
Expected: FAIL — `scripts/check_doc_links.py` does not exist.

- [ ] **Step 3.3: Implement the validator**

Create `scripts/check_doc_links.py`:

```python
#!/usr/bin/env python3
"""Internal-markdown-link validator.

Scans markdown files for relative `[label](./path.md)` and `[label](path.md)`
links and asserts every target resolves to an existing file. External links
(http://, https://, mailto:) are skipped. Anchors (`#section`) are not
required to exist; the file half is still checked.

Default scan set when invoked with no args:
  - README.md
  - CHANGELOG.md (top-level if present)
  - docs/ (recursive, *.md only)

Exit codes:
  0 — every link resolves.
  1 — one or more broken links; details printed to stdout.
  2 — usage error (e.g. nonexistent input path).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Match `[label](target)` where target does NOT start with http://, https://,
# mailto:, or `#`. Greedy on label; non-greedy avoidance not needed because
# the link is opaque to label content (we only consume up to the matching `)`).
_LINK_RE = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<target>(?!https?://|mailto:|#)[^)]+)\)")


def _collect_md_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for r in roots:
        if r.is_file() and r.suffix == ".md":
            files.append(r)
        elif r.is_dir():
            files.extend(sorted(r.rglob("*.md")))
    return files


def _default_roots() -> list[Path]:
    """Repo-default scan set."""
    roots = []
    for candidate in (REPO_ROOT / "README.md", REPO_ROOT / "CHANGELOG.md", REPO_ROOT / "docs"):
        if candidate.exists():
            roots.append(candidate)
    return roots


def _check_file(md: Path) -> list[str]:
    """Return a list of broken-link error strings for this markdown file."""
    errors: list[str] = []
    text = md.read_text(encoding="utf-8", errors="replace")
    for m in _LINK_RE.finditer(text):
        target = m.group("target").strip()
        # Strip anchor suffix; we don't require anchor existence.
        file_part = target.split("#", 1)[0]
        if not file_part:
            # Pure anchor like `#section` — same-page, skip.
            continue
        resolved = (md.parent / file_part).resolve()
        if not resolved.exists():
            errors.append(f"{md}: broken link [{m.group('label')}]({target}) → {resolved}")
    return errors


def main(argv: list[str]) -> int:
    if argv:
        raw_paths = [Path(p) for p in argv]
        for p in raw_paths:
            if not p.exists():
                print(f"error: path does not exist: {p}", file=sys.stderr)
                return 2
        roots = raw_paths
    else:
        roots = _default_roots()
        if not roots:
            print("error: no default paths exist (README.md / CHANGELOG.md / docs/)", file=sys.stderr)
            return 2

    all_errors: list[str] = []
    for md in _collect_md_files(roots):
        all_errors.extend(_check_file(md))

    if all_errors:
        for e in all_errors:
            print(e)
        print(f"\n{len(all_errors)} broken link(s).")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Mark executable: `chmod +x scripts/check_doc_links.py`

- [ ] **Step 3.4: Run the tests — expect pass**

Run: `cd bootstrapper && uv run pytest tests/test_doc_links.py -v`
Expected: PASS (all six tests).

- [ ] **Step 3.5: Capture pre-migration baseline**

Run: `python scripts/check_doc_links.py`
Expected: exit 0 OR exit 1 with a list of *existing* (pre-migration) broken links. Record the output — this is the baseline. Post-migration must show the same set or fewer broken links (and definitely zero references to old `docs/services/<name>.md` paths).

Save the baseline:
```bash
python scripts/check_doc_links.py > /tmp/link-baseline-pre-migration.txt 2>&1 || true
```

- [ ] **Step 3.6: Commit**

```bash
git add scripts/check_doc_links.py bootstrapper/tests/test_doc_links.py
git commit -m "scripts: add doc-link validator + tests"
```

---

## Task 4: Migration script (`scripts/migrate_docs_to_folders.py`)

**Files:**
- Create: `scripts/migrate_docs_to_folders.py`
- Create: `bootstrapper/tests/test_doc_migration.py`

**Why:** the migration must be reproducible and reviewed in isolation — not done ad-hoc with `mv` commands. A script also lets reviewers verify the link-rewrite logic.

- [ ] **Step 4.1: Write the failing test**

Create `bootstrapper/tests/test_doc_migration.py`:

```python
"""Tests for scripts/migrate_docs_to_folders.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "migrate_docs_to_folders.py"


def _run_migration(target_repo: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--repo-root", str(target_repo), *flags]
    return subprocess.run(cmd, capture_output=True, text=True)


def _build_fake_repo(tmp_path: Path) -> Path:
    """Build a miniature repo: 2 service docs + 1 cross-doc + 1 top-level README."""
    repo = tmp_path / "repo"
    docs_services = repo / "docs" / "services"
    docs_services.mkdir(parents=True)
    (docs_services / "alpha.md").write_text("# Alpha\nBody.")
    (docs_services / "bravo.md").write_text("# Bravo\nBody.")

    (repo / "docs" / "other.md").write_text("See [Alpha](services/alpha.md).")
    (repo / "README.md").write_text("See [Bravo](docs/services/bravo.md).")
    return repo


def test_migration_moves_files_into_folders(tmp_path):
    repo = _build_fake_repo(tmp_path)
    result = _run_migration(repo)
    assert result.returncode == 0, result.stdout + result.stderr

    # Files moved to per-folder layout
    assert (repo / "docs" / "services" / "alpha" / "README.md").is_file()
    assert (repo / "docs" / "services" / "bravo" / "README.md").is_file()
    # Old flat files gone
    assert not (repo / "docs" / "services" / "alpha.md").exists()
    assert not (repo / "docs" / "services" / "bravo.md").exists()


def test_migration_rewrites_inbound_links(tmp_path):
    repo = _build_fake_repo(tmp_path)
    _run_migration(repo)

    other = (repo / "docs" / "other.md").read_text()
    readme = (repo / "README.md").read_text()
    assert "services/alpha/README.md" in other
    assert "services/alpha.md" not in other
    assert "docs/services/bravo/README.md" in readme
    assert "docs/services/bravo.md" not in readme


def test_migration_dry_run_makes_no_changes(tmp_path):
    repo = _build_fake_repo(tmp_path)
    result = _run_migration(repo, "--dry-run")
    assert result.returncode == 0

    # Files NOT moved
    assert (repo / "docs" / "services" / "alpha.md").is_file()
    assert not (repo / "docs" / "services" / "alpha").exists()
    # Links NOT rewritten
    assert "services/alpha.md" in (repo / "docs" / "other.md").read_text()


def test_migration_is_idempotent(tmp_path):
    repo = _build_fake_repo(tmp_path)
    r1 = _run_migration(repo)
    r2 = _run_migration(repo)
    assert r1.returncode == 0
    assert r2.returncode == 0
    # Re-running on already-migrated repo doesn't break or duplicate
    assert (repo / "docs" / "services" / "alpha" / "README.md").is_file()
```

- [ ] **Step 4.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_doc_migration.py -v`
Expected: FAIL — script doesn't exist.

- [ ] **Step 4.3: Implement the migration script**

Create `scripts/migrate_docs_to_folders.py`:

```python
#!/usr/bin/env python3
"""One-shot migration: docs/services/<name>.md → docs/services/<name>/README.md.

Also rewrites every inbound markdown link from the old path to the new path
across the whole repo. Idempotent: re-running on an already-migrated repo is
a no-op and exits 0.

Usage:
  python scripts/migrate_docs_to_folders.py [--repo-root PATH] [--dry-run]

Exit codes:
  0 — success (or dry-run with changes that would be applied).
  1 — error (couldn't move a file, target folder already non-empty, etc.).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _scan_flat_docs(services_dir: Path) -> list[Path]:
    """Find docs/services/*.md (NOT files inside subfolders)."""
    return sorted(p for p in services_dir.glob("*.md") if p.is_file())


def _move_one(md: Path, dry_run: bool) -> tuple[Path, Path]:
    """Plan: docs/services/foo.md → docs/services/foo/README.md.

    Returns (old_path, new_path). Performs the move if not dry_run.
    """
    target_dir = md.with_suffix("")
    target_file = target_dir / "README.md"
    if target_file.exists():
        # Already migrated; nothing to do.
        return md, target_file
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        md.rename(target_file)
    return md, target_file


# Captures: full match, label, target ending in /<service>.md (no slash before)
# Negative lookbehind on `/`: avoid double-rewriting an already-migrated path.
def _build_link_re(service_names: set[str]) -> re.Pattern[str]:
    """Match `[label](some/path/foo.md)` or `[label](services/foo.md)` etc.,
    where the basename (sans extension) is in service_names."""
    names = "|".join(sorted(re.escape(n) for n in service_names))
    # Capture group 1 = label, 2 = path-prefix-with-trailing-slash, 3 = service name.
    return re.compile(rf"\[([^\]]+)\]\(((?:[^)\s]*/)?)({names})\.md(#[^)]*)?\)")


def _rewrite_links_in_file(
    md: Path,
    pattern: re.Pattern[str],
    services_dir_relpath: str,
    dry_run: bool,
) -> int:
    """Rewrite inbound links in one markdown file. Returns count of substitutions."""

    text = md.read_text(encoding="utf-8", errors="replace")

    def _sub(m: re.Match[str]) -> str:
        label = m.group(1)
        prefix = m.group(2)  # e.g. "docs/services/" or "./" or "" or "../"
        name = m.group(3)
        anchor = m.group(4) or ""
        # Only rewrite when prefix points at services_dir (or is a bare service.md
        # next to a file already inside services/). Keep it simple: only rewrite
        # when the prefix is the empty string AND md is inside services_dir,
        # OR the prefix ends with "services/".
        if prefix.endswith("services/"):
            return f"[{label}]({prefix}{name}/README.md{anchor})"
        if prefix == "" and md.parent.name == services_dir_relpath.rsplit("/", 1)[-1]:
            return f"[{label}]({name}/README.md{anchor})"
        # Otherwise: leave alone (link is to something else named foo.md).
        return m.group(0)

    new_text, count = pattern.subn(_sub, text)
    if count and not dry_run:
        md.write_text(new_text, encoding="utf-8")
    return count


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    repo = args.repo_root.resolve()
    services_dir = repo / "docs" / "services"
    if not services_dir.is_dir():
        print(f"error: {services_dir} not found", file=sys.stderr)
        return 1

    flat = _scan_flat_docs(services_dir)
    if not flat:
        print("nothing to migrate (no flat docs/services/*.md files found)")
        return 0

    service_names = {p.stem for p in flat}
    print(f"migration plan: {len(flat)} doc(s) to relocate" + (" (dry-run)" if args.dry_run else ""))
    for p in flat:
        print(f"  {p.relative_to(repo)} → {p.relative_to(repo).with_suffix('')}/README.md")
        _move_one(p, args.dry_run)

    pattern = _build_link_re(service_names)
    total_subs = 0
    scan_roots = [
        repo / "README.md",
        repo / "docs",
    ]
    for root in scan_roots:
        if root.is_file() and root.suffix == ".md":
            total_subs += _rewrite_links_in_file(root, pattern, "docs/services", args.dry_run)
        elif root.is_dir():
            for md in sorted(root.rglob("*.md")):
                total_subs += _rewrite_links_in_file(md, pattern, "docs/services", args.dry_run)
    print(f"link rewrites: {total_subs}" + (" (dry-run; no files written)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4.4: Run the migration tests**

Run: `cd bootstrapper && uv run pytest tests/test_doc_migration.py -v`
Expected: PASS (all four tests).

- [ ] **Step 4.5: Dry-run the migration on the real repo**

Run from repo root: `python scripts/migrate_docs_to_folders.py --dry-run`
Expected: lists 21 migrations + N link rewrites; **no files changed**.

Verify: `ls docs/services/*.md | wc -l` still reports 21.

- [ ] **Step 4.6: Commit the script**

```bash
git add scripts/migrate_docs_to_folders.py bootstrapper/tests/test_doc_migration.py
git commit -m "scripts: add doc-folder migration runner + tests"
```

---

## Task 5: Run the migration

**Files:**
- Move: `docs/services/<name>.md` → `docs/services/<name>/README.md` (×21)
- Modify: all `*.md` files with inbound links

- [ ] **Step 5.1: Execute the migration**

Run from repo root: `python scripts/migrate_docs_to_folders.py`
Expected stdout summarizes 21 moves and a count of link rewrites.

- [ ] **Step 5.2: Verify post-migration state**

```bash
ls docs/services/                # should list 21 directories, NO .md files
ls docs/services/hermes/README.md  # should exist
ls docs/services/hermes.md 2>/dev/null && echo "FAIL: old file still present" || echo "ok: old file gone"
```

- [ ] **Step 5.3: Run link validator — must show no NEW breakage**

Run: `python scripts/check_doc_links.py > /tmp/link-baseline-post-migration.txt 2>&1; echo $?`
Expected: same exit code as `/tmp/link-baseline-pre-migration.txt` captured in Step 3.5.

Compare:
```bash
diff /tmp/link-baseline-pre-migration.txt /tmp/link-baseline-post-migration.txt
```
Expected: no lines mentioning `docs/services/<name>.md` paths should appear; if any do, the link-rewrite regex in Step 4.3 missed a pattern — fix and re-run.

- [ ] **Step 5.4: Run pre-existing test suite — must still pass**

Run: `cd bootstrapper && uv run pytest -q`
Expected: same pass count as baseline (Step 2).

- [ ] **Step 5.5: Commit**

```bash
git add docs/ README.md
# Add any other files the link-rewrite touched (check `git status`)
git commit -m "docs: migrate docs/services/<name>.md to per-service folder layout"
```

---

## Task 6: `deps_resolver.py` — DepGraph data model

**Files:**
- Create: `bootstrapper/docs/__init__.py`
- Create: `bootstrapper/docs/deps_resolver.py`
- Create: `bootstrapper/tests/test_deps_resolver.py`

- [ ] **Step 6.1: Write the failing test**

Create `bootstrapper/tests/test_deps_resolver.py`:

```python
"""Tests for bootstrapper.docs.deps_resolver."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

SERVICES_DIR = REPO_ROOT / "services"


def test_dep_graph_focus_is_service_name():
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    assert g.focus == "hermes"
    assert g.category == "agents"


def test_dep_graph_required_upstream_includes_litellm():
    """Hermes's depends_on.required: [litellm] should produce a required upstream edge."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    others = {e.other for e in g.upstream if e.kind == "required"}
    assert "litellm" in others


def test_dep_graph_adaptive_upstream_includes_tts_and_stt():
    """Hermes adapts_to: [stt_provider, tts_provider, ...] → adaptive edges."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    adaptive = {e.other for e in g.upstream if e.kind == "adaptive"}
    # Names depend on how aggregate manifests are resolved. Either explicit
    # provider names (parakeet, speaches, chatterbox) or aggregate handles
    # ("stt-provider", "tts-provider") are acceptable Phase-A outputs;
    # composite-focus aggregation (Task 7) normalizes these.
    assert adaptive  # at least one adaptive edge present
    assert any("stt" in a or a == "parakeet" or a == "speaches" for a in adaptive)


def test_dep_graph_downstream_includes_litellm_loop():
    """LiteLLM registers Hermes back as the `hermes-agent` model → bidirectional loop.

    For the resolver alone, this means: Hermes's downstream set includes
    LiteLLM, even though LiteLLM was already in upstream. The bidirectional
    flag must be True on both sides.
    """
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    bidir = [e for e in g.upstream if e.other == "litellm" and e.bidirectional]
    assert bidir, "expected Hermes↔LiteLLM marked bidirectional"


def test_dep_graph_failure_mode_populated_from_manifest():
    """The failure_mode string from Task 2 must propagate to adaptive upstream edges."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    # Look at the LiteLLM edge (required, marked failure_mode in Task 2)
    litellm_edge = next(e for e in g.upstream if e.other == "litellm")
    assert litellm_edge.failure_mode is not None
    assert "preflight" in litellm_edge.failure_mode.lower()


def test_dep_graph_init_containers_recorded():
    """hermes-init must be in init_containers, not in upstream/downstream."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    assert "hermes-init" in g.init_containers
    assert all(e.other != "hermes-init" for e in g.upstream)
    assert all(e.other != "hermes-init" for e in g.downstream)


def test_dep_graph_byte_deterministic():
    """Two builds of the same graph produce identical edge orderings."""
    from docs.deps_resolver import build_graph
    g1 = build_graph("hermes", SERVICES_DIR)
    g2 = build_graph("hermes", SERVICES_DIR)
    assert g1 == g2
```

- [ ] **Step 6.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_deps_resolver.py -v`
Expected: FAIL — `bootstrapper.docs` package missing.

- [ ] **Step 6.3: Create the package**

```bash
mkdir -p bootstrapper/docs/templates
touch bootstrapper/docs/__init__.py
```

Create `bootstrapper/docs/__init__.py` empty (just the package marker).

- [ ] **Step 6.4: Implement `deps_resolver.py`**

Create `bootstrapper/docs/deps_resolver.py`:

```python
"""Manifest-graph resolver.

For a given focus service, walks every manifest under services/ and builds
a DepGraph describing:
  - upstream edges (services this one depends on, classified as required /
    adaptive / optional)
  - downstream edges (services that depend on this one)
  - bidirectional loops (A → B and B → A collapsed)
  - init containers (recorded but excluded from edges per spec A.3 rule #7)

The resolver is byte-deterministic for the same manifest state. It is the
sole input to deps_section_writer and diagram_renderer.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.manifests import Manifest, load_manifests  # noqa: E402


EdgeKind = Literal["required", "optional", "adaptive"]
EdgeDirection = Literal["upstream", "downstream"]


@dataclass(frozen=True, order=True)
class DepEdge:
    """One edge on the focus service's dependency graph.

    Ordered tuple-comparable so (kind, other) sorts stably across runs.

    `other_category` carries the OTHER service's category so the renderer
    can stroke each box with its own category color without reloading
    manifests.
    """

    other: str
    kind: EdgeKind
    direction: EdgeDirection
    mechanism: str = ""
    failure_mode: str | None = None
    bidirectional: bool = False
    other_category: str = "external"


@dataclass(frozen=True)
class DepGraph:
    focus: str
    category: str
    port_var: str | None
    source: str
    upstream: tuple[DepEdge, ...] = ()
    downstream: tuple[DepEdge, ...] = ()
    init_containers: tuple[str, ...] = ()


# ─────────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────────


def build_graph(focus: str, services_root: Path) -> DepGraph:
    """Build the DepGraph for a single service."""

    manifests_by_name = {m.name: m for m in load_manifests(services_root)}
    if focus not in manifests_by_name:
        raise KeyError(f"no manifest for service '{focus}' under {services_root}")

    me = manifests_by_name[focus]

    upstream: list[DepEdge] = []
    upstream.extend(_required_upstream(me, manifests_by_name))
    upstream.extend(_adaptive_upstream(me, manifests_by_name))
    upstream.extend(_optional_upstream(me, manifests_by_name))

    downstream: list[DepEdge] = []
    for other_name, other_m in manifests_by_name.items():
        if other_name == focus:
            continue
        # Inverse-pass: does `other_m` declare focus as a dep?
        downstream.extend(_inverse_required(focus, other_m, manifests_by_name))
        downstream.extend(_inverse_adaptive(focus, other_m, manifests_by_name))
        downstream.extend(_inverse_optional(focus, other_m, manifests_by_name))

    # doc_extras.diagram.extra_consumers — manual escape hatch
    extras = me.doc_extras.get("diagram", {}).get("extra_consumers", [])
    for ex in extras:
        if ex in manifests_by_name and ex != focus:
            downstream.append(
                DepEdge(other=ex, kind="optional", direction="downstream",
                        mechanism="manual escape hatch (doc_extras.diagram.extra_consumers)",
                        other_category=_cat(manifests_by_name, ex))
            )

    # Bidirectional collapse
    upstream_names = {e.other for e in upstream}
    downstream_names = {e.other for e in downstream}
    both = upstream_names & downstream_names
    upstream = [
        DepEdge(**{**e.__dict__, "bidirectional": True}) if e.other in both else e
        for e in upstream
    ]
    downstream = [
        DepEdge(**{**e.__dict__, "bidirectional": True}) if e.other in both else e
        for e in downstream
    ]

    # Init containers: anything in containers that ends with "-init"
    init_containers = tuple(c for c in me.containers if c.endswith("-init"))

    # Identify the primary source variant for the focus box label
    source_label = me.sources.default if me.sources else "single"

    # Port (use the first port-bearing env var that exists)
    port_var = None
    for env in me.env:
        if env.name.endswith("_PORT") or env.name.endswith("_API_PORT"):
            port_var = env.name
            break

    return DepGraph(
        focus=focus,
        category=me.category,
        port_var=port_var,
        source=source_label,
        upstream=tuple(sorted(set(upstream), key=_edge_sort_key)),
        downstream=tuple(sorted(set(downstream), key=_edge_sort_key)),
        init_containers=init_containers,
    )


# Category ordering matches services.topology.CATEGORY_ORDER so lane sort
# is consistent with the wizard's grouping.
_CATEGORY_RANK = {"infra": 0, "data": 1, "llm": 2, "media": 3, "agents": 4, "apps": 5, "external": 6}


def _edge_sort_key(e: DepEdge) -> tuple[int, str]:
    """Stable sort within a tier (spec A.3 rule #5): by category, then alphabetically."""
    return (_CATEGORY_RANK.get(e.other_category, 99), e.other)


# ─────────────────────────────────────────────────────────────────────────
# Edge extraction helpers
# ─────────────────────────────────────────────────────────────────────────


def _cat(all_m: dict[str, Manifest], name: str) -> str:
    return all_m[name].category if name in all_m else "external"


def _required_upstream(me: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    edges: list[DepEdge] = []
    for dep in me.depends_on.required:
        if dep in all_m:
            edges.append(DepEdge(
                other=dep,
                kind="required",
                direction="upstream",
                mechanism=_extract_mechanism(me, dep, all_m),
                failure_mode=_extract_failure_mode(me, dep),
                other_category=_cat(all_m, dep),
            ))
    return edges


def _adaptive_upstream(me: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    edges: list[DepEdge] = []
    seen: set[str] = set()
    for container, block in (me.runtime_adaptive or {}).items():
        adapts_to = block.get("adapts_to", []) or []
        fm = block.get("failure_mode")
        for target in adapts_to:
            # adapts_to entries may be logical names ("llm_provider", "tts_provider")
            # OR concrete service names. For Phase A we record them verbatim;
            # Task 7 (composite-focus) resolves aggregate logical names to
            # underlying manifest names.
            if target in seen:
                continue
            seen.add(target)
            edges.append(DepEdge(
                other=target,
                kind="adaptive",
                direction="upstream",
                mechanism=_extract_adaptive_mechanism(block, target),
                failure_mode=fm,
                other_category=_cat(all_m, target),
            ))
    return edges


def _optional_upstream(me: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    edges: list[DepEdge] = []
    for container, block in (me.runtime_deps or {}).items():
        for dep in block.get("optional", []) or []:
            if dep in all_m and dep != me.name:
                edges.append(DepEdge(
                    other=dep,
                    kind="optional",
                    direction="upstream",
                    mechanism="(optional — wired conditionally; see manifest)",
                    other_category=_cat(all_m, dep),
                ))
    return edges


def _inverse_required(focus: str, other: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    if focus in other.depends_on.required:
        return [DepEdge(other=other.name, kind="required", direction="downstream",
                        mechanism=f"{other.name} declares {focus} in depends_on.required",
                        other_category=_cat(all_m, other.name))]
    return []


def _inverse_adaptive(focus: str, other: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    for container, block in (other.runtime_adaptive or {}).items():
        if focus in (block.get("adapts_to") or []):
            return [DepEdge(other=other.name, kind="adaptive", direction="downstream",
                            mechanism=f"{other.name} adapts_to {focus}",
                            other_category=_cat(all_m, other.name))]
    return []


def _inverse_optional(focus: str, other: Manifest, all_m: dict[str, Manifest]) -> list[DepEdge]:
    for container, block in (other.runtime_deps or {}).items():
        if focus in (block.get("optional") or []):
            return [DepEdge(other=other.name, kind="optional", direction="downstream",
                            mechanism=f"{other.name} lists {focus} as optional dep",
                            other_category=_cat(all_m, other.name))]
    return []


def _extract_mechanism(me: Manifest, dep: str, all_m: dict[str, Manifest]) -> str:
    """Best-effort mechanism string from env defaults."""
    # First: look for <DEP>_LOCALHOST_URL or <DEP>_ENDPOINT in the focus manifest's env
    for env in me.env:
        if env.name.startswith(dep.upper()) and (
            env.name.endswith("_LOCALHOST_URL") or env.name.endswith("_ENDPOINT")
        ):
            return str(env.default) or f"http://{dep}:<port>"
    # Fallback: container DNS
    return f"http://{dep}:<port>"


def _extract_adaptive_mechanism(block: dict, target: str) -> str:
    env_adapt = block.get("environment_adaptation") or {}
    # adapts_to "llm_provider" might have a corresponding LITELLM_*  in env_adapt
    for k, v in env_adapt.items():
        if target.split("_")[0].lower() in k.lower():
            return f"{k}={v}"
    if env_adapt:
        return next(iter(f"{k}={v}" for k, v in env_adapt.items()))
    return f"(adaptive; see manifest's runtime_adaptive block)"


def _extract_failure_mode(me: Manifest, dep: str) -> str | None:
    """If the focus declares a runtime_adaptive block where this dep appears as
    a required upstream, surface the failure_mode. Otherwise None for now;
    Task 7 + Phase C will broaden coverage."""
    for container, block in (me.runtime_adaptive or {}).items():
        adapts_to = block.get("adapts_to") or []
        if "llm_provider" in adapts_to and dep == "litellm":
            return block.get("failure_mode")
    return None
```

- [ ] **Step 6.5: Run the tests — expect pass**

Run: `cd bootstrapper && uv run pytest tests/test_deps_resolver.py -v`
Expected: PASS (all seven tests).

If failures appear:
- `test_dep_graph_failure_mode_populated_from_manifest` — Task 2's Hermes manifest edit may not have landed; verify with `grep failure_mode services/hermes/service.yml`.
- `test_dep_graph_downstream_includes_litellm_loop` — verify LiteLLM's manifest declares Hermes somewhere. If it doesn't (LiteLLM does `model_list` registration at init time, not via depends_on), use `doc_extras.diagram.extra_consumers: [hermes]` on LiteLLM's manifest as a Task-6 follow-up (the manifest is the canonical source of truth — this is the kind of escape hatch we shipped the field for).

- [ ] **Step 6.6: Commit**

```bash
git add bootstrapper/docs/__init__.py \
        bootstrapper/docs/deps_resolver.py \
        bootstrapper/tests/test_deps_resolver.py
git commit -m "docs: add DepGraph resolver for per-service deps"
```

---

## Task 7: Composite-focus aggregation (Spec A.7)

**Files:**
- Modify: `bootstrapper/docs/deps_resolver.py`
- Modify: `bootstrapper/tests/test_deps_resolver.py`

**Why:** the 21 doc folders don't 1:1 to manifests. Three aggregate doc folders (`doc-processor`, `stt-provider`, `tts-provider`) fold multiple manifests. The resolver needs to support a "doc folder" mode that unions edges across underlying manifests.

- [ ] **Step 7.1: Write the failing test**

Append to `bootstrapper/tests/test_deps_resolver.py`:

```python
def test_doc_folder_to_manifests_mapping():
    """Aggregate doc folders are recognized and map to underlying manifests."""
    from docs.deps_resolver import doc_folder_to_manifests
    assert doc_folder_to_manifests("hermes") == ("hermes",)
    # Aggregates fold:
    assert set(doc_folder_to_manifests("stt-provider")) >= {"parakeet", "speaches"}
    assert set(doc_folder_to_manifests("tts-provider")) >= {"chatterbox", "speaches"}
    assert set(doc_folder_to_manifests("doc-processor")) >= {"docling"}
    # multi2vec-clip has no manifest — empty tuple
    assert doc_folder_to_manifests("multi2vec-clip") == ()


def test_build_doc_graph_aggregates_edges():
    """build_doc_graph('stt-provider') unions parakeet + speaches edges and
    suppresses intra-aggregate edges."""
    from docs.deps_resolver import build_doc_graph
    g = build_doc_graph("stt-provider", SERVICES_DIR)
    assert g.focus == "stt-provider"
    # Hermes adapts_to stt_provider, so stt-provider has Hermes downstream
    assert any(e.other == "hermes" for e in g.downstream)
    # Internal edge: parakeet ↔ speaches must NOT appear (intra-aggregate
    # suppression)
    edge_others = {e.other for e in g.upstream} | {e.other for e in g.downstream}
    assert "parakeet" not in edge_others
    assert "speaches" not in edge_others


def test_build_doc_graph_singleton_passes_through():
    """Singleton doc folders (1:1 with manifest) behave like build_graph()."""
    from docs.deps_resolver import build_doc_graph, build_graph
    g1 = build_doc_graph("hermes", SERVICES_DIR)
    g2 = build_graph("hermes", SERVICES_DIR)
    assert g1.upstream == g2.upstream
    assert g1.downstream == g2.downstream


def test_build_doc_graph_multi2vec_clip_is_pointer_only():
    """multi2vec-clip has no manifest — build_doc_graph returns a sentinel
    DepGraph that signals 'no diagram, see weaviate'."""
    from docs.deps_resolver import build_doc_graph, DepGraph
    g = build_doc_graph("multi2vec-clip", SERVICES_DIR)
    assert isinstance(g, DepGraph)
    assert g.focus == "multi2vec-clip"
    assert g.upstream == ()
    assert g.downstream == ()
    assert g.init_containers == ()
```

- [ ] **Step 7.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_deps_resolver.py::test_doc_folder_to_manifests_mapping -v`
Expected: FAIL — function missing.

- [ ] **Step 7.3: Implement the mapping + aggregator**

Append to `bootstrapper/docs/deps_resolver.py`:

```python
# ─────────────────────────────────────────────────────────────────────────
# Doc-folder → manifests mapping (spec A.7)
# ─────────────────────────────────────────────────────────────────────────

# Hard-coded for now. If aggregate membership changes, edit this table.
# (Future refinement: derive from a `doc_folder:` field on each manifest.)
_AGGREGATE_DOC_FOLDERS: dict[str, tuple[str, ...]] = {
    "stt-provider":   ("parakeet", "speaches"),
    "tts-provider":   ("chatterbox", "speaches", "tts-provider"),
    "doc-processor":  ("docling",),
    "multi2vec-clip": (),     # no manifest; pointer doc only
}

# Doc folders without an explicit aggregate entry are 1:1 with the manifest
# of the same name. Validated at test time.
def doc_folder_to_manifests(doc_folder: str) -> tuple[str, ...]:
    if doc_folder in _AGGREGATE_DOC_FOLDERS:
        return _AGGREGATE_DOC_FOLDERS[doc_folder]
    # 1:1 default
    return (doc_folder,)


def build_doc_graph(doc_folder: str, services_root: Path) -> DepGraph:
    """Build a DepGraph for a doc folder. Folds aggregate manifests; for
    singleton doc folders, identical to build_graph()."""

    manifest_names = doc_folder_to_manifests(doc_folder)
    if not manifest_names:
        # Pointer-only doc (e.g., multi2vec-clip)
        return DepGraph(
            focus=doc_folder,
            category="data",  # multi2vec-clip is a Weaviate feature; data category
            port_var=None,
            source="(pointer doc — see weaviate)",
            upstream=(),
            downstream=(),
            init_containers=(),
        )

    if len(manifest_names) == 1 and manifest_names[0] == doc_folder:
        return build_graph(doc_folder, services_root)

    # Aggregate: build each underlying graph and merge.
    members = [build_graph(name, services_root) for name in manifest_names]
    member_set = set(manifest_names)

    merged_up: dict[tuple[str, str], DepEdge] = {}
    merged_down: dict[tuple[str, str], DepEdge] = {}
    for sub in members:
        for e in sub.upstream:
            if e.other in member_set:
                continue  # intra-aggregate edge — suppress
            key = (e.other, e.kind)
            # Prefer "required" over "adaptive" over "optional" on collision
            if key not in merged_up or _kind_rank(e.kind) < _kind_rank(merged_up[key].kind):
                merged_up[key] = e
        for e in sub.downstream:
            if e.other in member_set:
                continue
            key = (e.other, e.kind)
            if key not in merged_down or _kind_rank(e.kind) < _kind_rank(merged_down[key].kind):
                merged_down[key] = e

    # Use the first member's category as canonical for the aggregate.
    category = members[0].category
    init_containers = tuple(sorted({c for m in members for c in m.init_containers}))

    return DepGraph(
        focus=doc_folder,
        category=category,
        port_var=None,
        source="(aggregate)",
        upstream=tuple(sorted(merged_up.values(), key=_edge_sort_key)),
        downstream=tuple(sorted(merged_down.values(), key=_edge_sort_key)),
        init_containers=init_containers,
    )


def _kind_rank(kind: str) -> int:
    return {"required": 0, "adaptive": 1, "optional": 2}.get(kind, 3)
```

- [ ] **Step 7.4: Run the tests — expect pass**

Run: `cd bootstrapper && uv run pytest tests/test_deps_resolver.py -v`
Expected: all eleven tests pass.

- [ ] **Step 7.5: Commit**

```bash
git add bootstrapper/docs/deps_resolver.py bootstrapper/tests/test_deps_resolver.py
git commit -m "docs: add composite-focus aggregation for stt/tts/doc-processor"
```

---

## Task 8: `deps_section_writer.py` — markdown tables + future placeholders

**Files:**
- Create: `bootstrapper/docs/deps_section_writer.py`
- Create: `bootstrapper/docs/templates/deps_section.md.tmpl`
- Create: `bootstrapper/tests/test_deps_section_writer.py`
- Create: `bootstrapper/tests/fixtures/hermes.deps_section.md` (golden snapshot)

- [ ] **Step 8.1: Write the failing test**

Create `bootstrapper/tests/test_deps_section_writer.py`:

```python
"""Tests for bootstrapper.docs.deps_section_writer."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

SERVICES_DIR = REPO_ROOT / "services"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_section_for_hermes_matches_golden():
    """The deps section for Hermes is byte-stable against a committed fixture."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import build_doc_graph

    g = build_doc_graph("hermes", SERVICES_DIR)
    rendered = render_section(g)

    golden = (FIXTURE_DIR / "hermes.deps_section.md").read_text()
    assert rendered == golden, (
        "Hermes deps section drift. To accept the new output:\n"
        f"  bootstrapper/tests/fixtures/hermes.deps_section.md\n"
        "Diff against current rendered text and update if intentional."
    )


def test_section_contains_canonical_headings():
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import build_doc_graph

    g = build_doc_graph("hermes", SERVICES_DIR)
    text = render_section(g)
    for heading in (
        "## Dependencies & Integrations",
        "### Current — Upstream",
        "### Current — Downstream",
        "### Architecture diagram",
        "### Future — Missing pair integrations",
        "### Future — Candidate new services",
        "### Future — Unused features in this service",
    ):
        assert heading in text, f"missing heading: {heading}"


def test_section_emits_empty_table_placeholder():
    """A graph with no upstream emits an explicit `_No upstream dependencies._` line."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import DepGraph

    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    text = render_section(g)
    assert "_No upstream dependencies._" in text
    assert "_No downstream consumers._" in text


def test_section_emits_no_high_confidence_placeholder_in_future():
    """Future subsections render `_No high-confidence opportunities identified._`
    until Phase C populates them."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import DepGraph

    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    text = render_section(g)
    assert text.count("_No high-confidence opportunities identified._") >= 3
```

- [ ] **Step 8.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_deps_section_writer.py -v`
Expected: FAIL — module missing, fixture missing.

- [ ] **Step 8.3: Implement the writer**

Create `bootstrapper/docs/deps_section_writer.py`:

```python
"""DepGraph → markdown deps section."""

from __future__ import annotations

from .deps_resolver import DepEdge, DepGraph


def render_section(graph: DepGraph) -> str:
    """Render the canonical 'Dependencies & Integrations' section for one
    service's README. Output is byte-deterministic for the same DepGraph.

    The Future-* subsections emit a placeholder line until Phase C
    populates them.
    """

    lines: list[str] = []
    lines.append("## Dependencies & Integrations")
    lines.append("")
    lines.append(
        "> Auto-generated section — the **Current** subsections are derived from "
        f"`services/{graph.focus}/service.yml`. Re-run "
        f"`python -m bootstrapper.docs.regen {graph.focus}` after manifest changes."
    )
    lines.append("")

    # Current — Upstream
    lines.append("### Current — Upstream (this service depends on)")
    lines.append("")
    if graph.upstream:
        lines.append("| Service | Type | Mechanism | Failure mode |")
        lines.append("|---|---|---|---|")
        for e in graph.upstream:
            lines.append(_upstream_row(e))
    else:
        lines.append("_No upstream dependencies._")
    lines.append("")

    # Current — Downstream
    lines.append("### Current — Downstream (services that depend on this)")
    lines.append("")
    if graph.downstream:
        lines.append("| Service | Type | Mechanism |")
        lines.append("|---|---|---|")
        for e in graph.downstream:
            lines.append(_downstream_row(e))
    else:
        lines.append("_No downstream consumers._")
    lines.append("")

    # Diagram embed
    lines.append("### Architecture diagram")
    lines.append("")
    lines.append(f"![{graph.focus} architecture](./architecture.svg)")
    lines.append("")
    lines.append("[Open the interactive HTML diagram](./architecture.html) for a full-screen view.")
    lines.append("")

    # Future-* placeholders
    for heading in (
        "### Future — Missing pair integrations",
        "### Future — Candidate new services",
        "### Future — Unused features in this service",
    ):
        lines.append(heading)
        lines.append("")
        lines.append("_No high-confidence opportunities identified._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _upstream_row(e: DepEdge) -> str:
    return (
        f"| {e.other} | {e.kind} | "
        f"`{_escape_mechanism(e.mechanism)}` | "
        f"{e.failure_mode or '_unspecified_'} |"
    )


def _downstream_row(e: DepEdge) -> str:
    return f"| {e.other} | {e.kind} | {_escape_mechanism(e.mechanism)} |"


def _escape_mechanism(s: str) -> str:
    # Pipe characters break markdown tables. The mechanism field rarely
    # contains pipes, but guard anyway.
    return (s or "").replace("|", r"\|")
```

- [ ] **Step 8.4: Generate the golden fixture**

Run from repo root:

```bash
mkdir -p bootstrapper/tests/fixtures
PYTHONPATH=bootstrapper python -c "
from docs.deps_resolver import build_doc_graph
from docs.deps_section_writer import render_section
import pathlib
g = build_doc_graph('hermes', pathlib.Path('services'))
out = render_section(g)
print(out)
" > bootstrapper/tests/fixtures/hermes.deps_section.md
```

Open `bootstrapper/tests/fixtures/hermes.deps_section.md` and visually verify:
- Has all seven canonical headings.
- Upstream table includes LiteLLM with a failure_mode populated.
- Downstream table includes (at minimum) open-webui, n8n, openclaw, backend, jupyterhub (all consume `hermes-agent` model via LiteLLM's model_list).

If the downstream table is missing those consumers, that's correct **for Phase A** — they're wired via `litellm-init`'s model_list registration, not via depends_on. Task 12 will document this as a known limitation; Phase C may add `doc_extras.diagram.extra_consumers` on hermes' manifest as a follow-up.

- [ ] **Step 8.5: Run the test — expect pass**

Run: `cd bootstrapper && uv run pytest tests/test_deps_section_writer.py -v`
Expected: PASS.

- [ ] **Step 8.6: Commit**

```bash
git add bootstrapper/docs/deps_section_writer.py \
        bootstrapper/tests/test_deps_section_writer.py \
        bootstrapper/tests/fixtures/hermes.deps_section.md
git commit -m "docs: add deps-section markdown writer + Hermes golden snapshot"
```

---

## Task 9: SVG box + edge templates

**Files:**
- Create: `bootstrapper/docs/templates/svg_box.tmpl`
- Create: `bootstrapper/docs/templates/svg_edge.tmpl`
- Create: `bootstrapper/docs/templates/svg_defs.tmpl`

- [ ] **Step 9.1: Create `svg_defs.tmpl`** (grid pattern + arrow marker; shared)

```svg
<defs>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.5"/>
  </pattern>
  <marker id="arrowhead-solid" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#64748b"/>
  </marker>
  <marker id="arrowhead-dashed" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#fbbf24"/>
  </marker>
</defs>
```

- [ ] **Step 9.2: Create `svg_box.tmpl`** (Python `string.Template` placeholders)

```svg
<g class="box-$kind">
  <rect x="$x" y="$y" width="$w" height="$h" rx="6" fill="#0f172a"/>
  <rect x="$x" y="$y" width="$w" height="$h" rx="6"
        fill="$fill" stroke="$stroke" stroke-width="1.5"/>
  <text x="$cx" y="$ty" fill="white" font-size="$ts" font-weight="600" text-anchor="middle">$label</text>
  <text x="$cx" y="$sy" fill="#94a3b8" font-size="9" text-anchor="middle">$sublabel</text>
</g>
```

- [ ] **Step 9.3: Create `svg_edge.tmpl`** (three edge variants)

```svg
<line x1="$x1" y1="$y1" x2="$x2" y2="$y2"
      stroke="$stroke" stroke-width="$width" $dash
      marker-end="url(#$marker)"
      $title_attr>
  $title_elem
</line>
```

- [ ] **Step 9.4: Commit (template scaffolds; no tests until renderer wires them)**

```bash
git add bootstrapper/docs/templates/svg_box.tmpl \
        bootstrapper/docs/templates/svg_edge.tmpl \
        bootstrapper/docs/templates/svg_defs.tmpl
git commit -m "docs: add SVG templates for diagram renderer"
```

---

## Task 10: `diagram_renderer.py` + HTML wrapper template

**Files:**
- Create: `bootstrapper/docs/templates/architecture.html.tmpl`
- Create: `bootstrapper/docs/diagram_renderer.py`
- Create: `bootstrapper/tests/test_diagram_renderer.py`
- Create: `bootstrapper/tests/fixtures/hermes.architecture.svg`

- [ ] **Step 10.1: Create the HTML wrapper template**

`bootstrapper/docs/templates/architecture.html.tmpl`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>$focus — Architecture (genai-vanilla)</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { margin: 0; background: #020617; font-family: 'JetBrains Mono', monospace; color: #c0caf5; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 32px; }
    h1 { font-size: 22px; margin: 0 0 4px 0; display: flex; align-items: center; gap: 8px; }
    h1 .dot { width: 10px; height: 10px; border-radius: 50%; background: $cat_color; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.4 } }
    .subtitle { color: #94a3b8; font-size: 12px; margin-bottom: 24px; }
    .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; }
    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 24px; }
    .cards h3 { margin: 0 0 8px 0; font-size: 12px; color: #94a3b8; }
    .cards .num { font-size: 24px; font-weight: 700; }
    footer { color: #475569; font-size: 10px; margin-top: 24px; text-align: center; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1><span class="dot"></span> $focus — Architecture</h1>
    <div class="subtitle">$subtitle</div>
    <div class="card">$svg</div>
    <div class="cards">
      <div class="card"><h3>Required deps</h3><div class="num">$n_required</div></div>
      <div class="card"><h3>Optional/adaptive deps</h3><div class="num">$n_optional</div></div>
      <div class="card"><h3>Consumers</h3><div class="num">$n_consumers</div></div>
    </div>
    <footer>$footer</footer>
  </div>
</body>
</html>
```

- [ ] **Step 10.2: Write the failing test for renderer**

Create `bootstrapper/tests/test_diagram_renderer.py`:

```python
"""Tests for bootstrapper.docs.diagram_renderer."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

SERVICES_DIR = REPO_ROOT / "services"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_renders_svg_with_focus_label():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    assert svg.startswith("<svg")
    assert "hermes" in svg.lower()


def test_renders_html_includes_jetbrains_mono():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_html
    g = build_doc_graph("hermes", SERVICES_DIR)
    html = render_html(g)
    assert "JetBrains+Mono" in html
    assert "<svg" in html


def test_svg_has_no_volatile_content():
    """The SVG body must NOT contain a generation timestamp (HTML footer only)."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    # Common timestamp patterns we explicitly forbid in SVG body
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", svg)
    assert "generated:" not in svg.lower()


def test_svg_byte_deterministic():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    a = render_svg(g)
    b = render_svg(g)
    assert a == b


def test_svg_matches_golden_snapshot():
    """Hermes is the snapshot — most complex graph. Fixture lives at
    bootstrapper/tests/fixtures/hermes.architecture.svg."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("hermes", SERVICES_DIR)
    rendered = render_svg(g)
    golden = (FIXTURE_DIR / "hermes.architecture.svg").read_text()
    assert rendered == golden, (
        "Hermes SVG drift. To accept the new output:\n"
        "  PYTHONPATH=bootstrapper python -c \"from docs.deps_resolver "
        "import build_doc_graph; from docs.diagram_renderer import render_svg; "
        "from pathlib import Path; "
        "Path('bootstrapper/tests/fixtures/hermes.architecture.svg').write_text("
        "render_svg(build_doc_graph('hermes', Path('services'))))\"\n"
    )


def test_empty_lanes_drawn_explicitly():
    """A focus with empty upstream/downstream gets explicit 'no deps' placeholders."""
    from docs.deps_resolver import DepGraph
    from docs.diagram_renderer import render_svg

    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    svg = render_svg(g)
    assert "no upstream" in svg.lower() or "no upstream deps" in svg.lower()
    assert "no downstream" in svg.lower() or "no downstream consumers" in svg.lower()


def test_aggregate_focus_renders_parent_box():
    """Aggregate doc folders (stt-provider, tts-provider) render a parent
    boundary rectangle wrapping inner member boxes."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("stt-provider", SERVICES_DIR)
    svg = render_svg(g)
    # Aggregate boundary marker: a dashed RECT with rose stroke (per spec A.7).
    # Look for both signals together — dashed strokes also appear on adaptive
    # edges, so we need the rose color too.
    assert "#fb7185" in svg
    assert "stroke-dasharray=\"4,4\"" in svg


def test_non_aggregate_has_no_rose_boundary():
    """Singleton focus (e.g. hermes) does NOT emit the rose aggregate boundary."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    assert "#fb7185" not in svg
```

- [ ] **Step 10.3: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_diagram_renderer.py -v`
Expected: FAIL — module missing.

- [ ] **Step 10.4: Implement the renderer**

Create `bootstrapper/docs/diagram_renderer.py`:

```python
"""DepGraph → HTML+SVG renderer.

Applies the architecture-diagram skill's design system programmatically.
Output is byte-deterministic for the same DepGraph (no timestamps in SVG
body; timestamps live in the HTML footer only).
"""

from __future__ import annotations

import sys
from pathlib import Path
from string import Template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.topology import CATEGORY_COLORS  # noqa: E402

from .deps_resolver import DepEdge, DepGraph

TEMPLATE_DIR = Path(__file__).parent / "templates"

# ───── Geometry constants ────────────────────────────────────────────────
LANE_W = 240
BOX_W = 200
BOX_H = 60
BOX_GAP = 40
LANE_X = {
    "upstream":   60,
    "focus":      60 + LANE_W + 60,
    "downstream": 60 + LANE_W + 60 + 200 + 60,  # focus is 200 wide
}
FOCUS_W = 200
FOCUS_H = 120
LANE_HEADER_Y = 36
ROWS_TOP_Y = 80


def render_svg(graph: DepGraph) -> str:
    """Render the architecture SVG. Pure function of graph state."""

    defs = (TEMPLATE_DIR / "svg_defs.tmpl").read_text()
    rows = max(len(graph.upstream), len(graph.downstream), 1)
    height = ROWS_TOP_Y + rows * (BOX_H + BOX_GAP) + 40
    width = LANE_X["downstream"] + BOX_W + 60

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">')
    parts.append(defs)
    parts.append(f'<rect width="{width}" height="{height}" fill="url(#grid)"/>')

    # Lane headers
    parts.append(_text(LANE_X["upstream"] + LANE_W // 2 - 80, LANE_HEADER_Y, "UPSTREAM (deps)", size=11, weight=600, color="#94a3b8", anchor="middle"))
    parts.append(_text(LANE_X["focus"] + FOCUS_W // 2, LANE_HEADER_Y, "FOCUS", size=11, weight=600, color="#94a3b8", anchor="middle"))
    parts.append(_text(LANE_X["downstream"] + BOX_W // 2, LANE_HEADER_Y, "DOWNSTREAM (consumers)", size=11, weight=600, color="#94a3b8", anchor="middle"))

    # Edges first (drawn before boxes so they render behind)
    parts.extend(_edges(graph))

    # Upstream boxes
    if graph.upstream:
        for i, e in enumerate(graph.upstream):
            y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP)
            parts.append(_box(LANE_X["upstream"], y, BOX_W, BOX_H, e.other, _sublabel(e), e.kind, _color_for(e)))
    else:
        parts.append(_placeholder(LANE_X["upstream"], ROWS_TOP_Y, "no upstream deps"))

    # Focus
    focus_y = ROWS_TOP_Y + (max(rows, 1) * (BOX_H + BOX_GAP) - FOCUS_H) // 2
    focus_color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    parts.append(_box(
        LANE_X["focus"], focus_y, FOCUS_W, FOCUS_H,
        graph.focus.upper(),
        f"{graph.category} · {graph.source}",
        "focus",
        focus_color,
        big=True,
    ))

    # Downstream boxes
    if graph.downstream:
        for i, e in enumerate(graph.downstream):
            y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP)
            parts.append(_box(LANE_X["downstream"], y, BOX_W, BOX_H, e.other, _sublabel(e), e.kind, _color_for(e)))
    else:
        parts.append(_placeholder(LANE_X["downstream"], ROWS_TOP_Y, "no downstream consumers"))

    # Aggregate boundary box (for composite focus per spec A.7)
    if graph.source == "(aggregate)":
        parts.append(_aggregate_boundary(LANE_X["focus"], focus_y, FOCUS_W, FOCUS_H))

    parts.append("</svg>")
    return "\n".join(parts)


def render_html(graph: DepGraph) -> str:
    tmpl = Template((TEMPLATE_DIR / "architecture.html.tmpl").read_text())
    svg = render_svg(graph)
    cat_color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    n_required = sum(1 for e in graph.upstream if e.kind == "required")
    n_optional = sum(1 for e in graph.upstream if e.kind in ("optional", "adaptive"))
    n_consumers = len(graph.downstream)
    return tmpl.substitute(
        focus=graph.focus,
        subtitle=f"category: {graph.category} · source: {graph.source}",
        cat_color=cat_color,
        svg=svg,
        n_required=n_required,
        n_optional=n_optional,
        n_consumers=n_consumers,
        footer=f"Regenerate: python -m bootstrapper.docs.regen {graph.focus}",
    )


# ───── Internal helpers ──────────────────────────────────────────────────


def _color_for(e: DepEdge) -> str:
    """Spec A.3 rule #3: each box uses its category's palette token."""
    return CATEGORY_COLORS.get(e.other_category, "#94a3b8")


def _box(x: int, y: int, w: int, h: int, label: str, sublabel: str, kind: str, stroke: str, *, big: bool = False) -> str:
    fill = "rgba(15, 23, 42, 0.7)"
    cx = x + w // 2
    ty = y + 24 if big else y + 22
    sy = y + 44 if big else y + 38
    ts = 14 if big else 11
    return Template((TEMPLATE_DIR / "svg_box.tmpl").read_text()).substitute(
        x=x, y=y, w=w, h=h, kind=kind, fill=fill, stroke=stroke,
        cx=cx, ty=ty, sy=sy, ts=ts, label=label, sublabel=sublabel or "",
    )


def _placeholder(x: int, y: int, text: str) -> str:
    return f'<text x="{x + BOX_W // 2}" y="{y + BOX_H // 2}" fill="#475569" font-size="10" text-anchor="middle" font-style="italic">— {text} —</text>'


def _aggregate_boundary(x: int, y: int, w: int, h: int) -> str:
    pad = 14
    return (
        f'<rect x="{x - pad}" y="{y - pad}" width="{w + 2 * pad}" height="{h + 2 * pad}" '
        f'rx="12" fill="none" stroke="#fb7185" stroke-width="1.5" stroke-dasharray="4,4"/>'
    )


def _edges(graph: DepGraph) -> list[str]:
    out: list[str] = []
    fy_focus = ROWS_TOP_Y + (max(len(graph.upstream), len(graph.downstream), 1) * (BOX_H + BOX_GAP)) // 2
    for i, e in enumerate(graph.upstream):
        y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP) + BOX_H // 2
        out.append(_edge(LANE_X["upstream"] + BOX_W, y, LANE_X["focus"], fy_focus, e))
        if e.bidirectional:
            # Second arrow, offset by 6px to disambiguate from the first
            out.append(_edge(LANE_X["focus"], fy_focus + 6, LANE_X["upstream"] + BOX_W, y + 6, e))
    for i, e in enumerate(graph.downstream):
        y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP) + BOX_H // 2
        out.append(_edge(LANE_X["focus"] + FOCUS_W, fy_focus, LANE_X["downstream"], y, e))
    return out


def _edge(x1: int, y1: int, x2: int, y2: int, e: DepEdge) -> str:
    if e.kind == "required":
        stroke, marker, dash = "#64748b", "arrowhead-solid", ""
    elif e.kind == "adaptive":
        stroke, marker, dash = "#fbbf24", "arrowhead-dashed", 'stroke-dasharray="4,4"'
    else:
        stroke, marker, dash = "#94a3b8", "arrowhead-solid", 'stroke-dasharray="2,3"'
    title = f"<title>{e.kind} · {e.failure_mode or e.mechanism}</title>" if e.failure_mode or e.mechanism else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="1.5" {dash} marker-end="url(#{marker})">'
        f'{title}</line>'
    )


def _text(x: int, y: int, text: str, *, size: int = 11, weight: int = 400, color: str = "#fff", anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{text}</text>'


def _sublabel(e: DepEdge) -> str:
    suffix = " · ↔" if e.bidirectional else ""
    return f"{e.kind}{suffix}"
```

- [ ] **Step 10.5: Generate the golden SVG fixture**

```bash
PYTHONPATH=bootstrapper python -c "
from docs.deps_resolver import build_doc_graph
from docs.diagram_renderer import render_svg
import pathlib
g = build_doc_graph('hermes', pathlib.Path('services'))
pathlib.Path('bootstrapper/tests/fixtures/hermes.architecture.svg').write_text(render_svg(g))
"
```

Open `bootstrapper/tests/fixtures/hermes.architecture.svg` in a browser (or `open` on macOS) and visually verify:
- Three lanes present.
- Focus box reads "HERMES".
- Upstream lane has at least LiteLLM + a few adaptive entries.
- Edge styling: required = solid slate, adaptive = dashed amber.

- [ ] **Step 10.6: Run all renderer tests — expect pass**

Run: `cd bootstrapper && uv run pytest tests/test_diagram_renderer.py -v`
Expected: PASS (all seven tests).

- [ ] **Step 10.7: Commit**

```bash
git add bootstrapper/docs/diagram_renderer.py \
        bootstrapper/docs/templates/architecture.html.tmpl \
        bootstrapper/tests/test_diagram_renderer.py \
        bootstrapper/tests/fixtures/hermes.architecture.svg
git commit -m "docs: add SVG+HTML diagram renderer + Hermes golden snapshot"
```

---

## Task 11: `regen.py` CLI

**Files:**
- Create: `bootstrapper/docs/regen.py`
- Create: `bootstrapper/tests/test_regen.py`

- [ ] **Step 11.1: Write the failing test**

Create `bootstrapper/tests/test_regen.py`:

```python
"""Tests for bootstrapper.docs.regen CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "docs.regen", *args]
    env = {"PYTHONPATH": str(REPO_ROOT / "bootstrapper")}
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env={**__import__('os').environ, **env})


def test_help_works():
    r = _run("--help")
    assert r.returncode == 0
    assert "usage" in r.stdout.lower()


def test_single_service_writes_three_files(tmp_path, monkeypatch):
    """regen hermes writes README.md (deps section), architecture.html, .svg."""
    # Run against repo's real services/ but redirect output to tmp_path.
    r = _run("hermes", "--out-root", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "hermes" / "README.md").is_file()
    assert (tmp_path / "hermes" / "architecture.html").is_file()
    assert (tmp_path / "hermes" / "architecture.svg").is_file()


def test_section_only_skips_diagrams(tmp_path):
    r = _run("hermes", "--out-root", str(tmp_path), "--section-only")
    assert r.returncode == 0
    assert (tmp_path / "hermes" / "README.md").is_file()
    assert not (tmp_path / "hermes" / "architecture.svg").exists()


def test_dry_run_writes_nothing(tmp_path):
    r = _run("hermes", "--out-root", str(tmp_path), "--dry-run")
    assert r.returncode == 0
    assert not (tmp_path / "hermes").exists()
    assert "would write" in r.stdout.lower()


def test_check_mode_exits_2_on_drift(tmp_path):
    """--check returns 2 if any committed artifact disagrees with current manifests."""
    # Set out-root to tmp_path (empty) — any service is "drifted" because the
    # committed file doesn't exist there.
    r = _run("hermes", "--out-root", str(tmp_path), "--check")
    assert r.returncode == 2, f"expected drift exit code 2, got {r.returncode}: {r.stdout}"


def test_all_processes_21_doc_folders(tmp_path):
    """--all iterates every doc folder under docs/services/ and writes
    artifacts to <out-root>/<doc-folder>/."""
    r = _run("--all", "--out-root", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    written = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    # Sanity: at least 20 service folders (allows for multi2vec-clip pointer)
    assert len(written) >= 20
```

- [ ] **Step 11.2: Run the test — expect failure**

Run: `cd bootstrapper && uv run pytest tests/test_regen.py -v`
Expected: FAIL — module missing.

- [ ] **Step 11.3: Implement the CLI**

Create `bootstrapper/docs/regen.py`:

```python
"""Per-service docs + diagram regenerator.

Usage:
  python -m bootstrapper.docs.regen <service> [--out-root PATH] [--dry-run]
                                              [--section-only] [--check]
  python -m bootstrapper.docs.regen --all     [same flags]

Exit codes:
  0 — success.
  1 — manifest error.
  2 — drift detected (--check mode only).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .deps_resolver import build_doc_graph, doc_folder_to_manifests
from .deps_section_writer import render_section
from .diagram_renderer import render_html, render_svg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_SERVICES = REPO_ROOT / "docs" / "services"
SERVICES_DIR = REPO_ROOT / "services"

DEPS_HEADER = "## Dependencies & Integrations"
DEPS_SECTION_FENCE_RE = re.compile(
    r"^## Dependencies & Integrations\b.*?(?=^## |\Z)",
    re.DOTALL | re.MULTILINE,
)


def _enumerate_doc_folders() -> list[str]:
    return sorted(
        p.name for p in DOCS_SERVICES.iterdir()
        if p.is_dir() and (p / "README.md").exists()
    )


def _upsert_section(readme_text: str, section: str) -> str:
    """Replace an existing Dependencies section, or append it if missing."""
    if DEPS_HEADER in readme_text:
        return DEPS_SECTION_FENCE_RE.sub(section.rstrip() + "\n\n", readme_text, count=1).rstrip() + "\n"
    return readme_text.rstrip() + "\n\n" + section


def _process(name: str, out_root: Path, dry_run: bool, section_only: bool, check: bool) -> int:
    graph = build_doc_graph(name, SERVICES_DIR)
    target_dir = out_root / name
    section = render_section(graph)

    # README.md
    readme_path = target_dir / "README.md"
    existing_readme = readme_path.read_text() if readme_path.exists() else ""
    new_readme = _upsert_section(existing_readme, section)

    artifacts: list[tuple[Path, str]] = [(readme_path, new_readme)]
    if not section_only:
        artifacts.append((target_dir / "architecture.svg", render_svg(graph)))
        artifacts.append((target_dir / "architecture.html", render_html(graph)))

    drift = 0
    for path, content in artifacts:
        existing = path.read_text() if path.exists() else ""
        if existing != content:
            if check:
                drift += 1
                print(f"DRIFT: {path}")
            elif dry_run:
                print(f"would write {path}")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
    return drift


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="bootstrapper.docs.regen")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("service", nargs="?", help="Single doc folder name (e.g. hermes).")
    grp.add_argument("--all", action="store_true", help="Process every doc folder under docs/services/.")
    ap.add_argument("--out-root", type=Path, default=DOCS_SERVICES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--section-only", action="store_true", help="Only write README's deps section; skip HTML+SVG.")
    ap.add_argument("--check", action="store_true", help="Exit 2 if any artifact would change. Implies --dry-run.")
    args = ap.parse_args(argv)

    targets = _enumerate_doc_folders() if args.all else [args.service]
    if not args.all and args.service not in _enumerate_doc_folders():
        # Allow regen of a doc folder before its README exists (initial run).
        if args.service not in {f.split("/")[-1] for f in _enumerate_doc_folders()}:
            # As long as build_doc_graph won't raise — give it a shot
            pass

    total_drift = 0
    for name in targets:
        try:
            total_drift += _process(name, args.out_root, args.dry_run, args.section_only, args.check)
        except KeyError as e:
            print(f"manifest error for {name}: {e}", file=sys.stderr)
            return 1

    if args.check and total_drift:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 11.4: Run the regen tests**

Run: `cd bootstrapper && uv run pytest tests/test_regen.py -v`
Expected: PASS.

- [ ] **Step 11.5: Commit**

```bash
git add bootstrapper/docs/regen.py bootstrapper/tests/test_regen.py
git commit -m "docs: add regen CLI (per-service + --all + --check drift gate)"
```

---

## Task 12: CI drift gate (`test_docs_drift.py`)

**Files:**
- Create: `bootstrapper/tests/test_docs_drift.py`

- [ ] **Step 12.1: Write the test**

Create `bootstrapper/tests/test_docs_drift.py`:

```python
"""CI gate: committed README deps sections + architecture artifacts must
match what `python -m docs.regen --all --check` would produce.

Parallels test_env_example_consistency. Fails if any manifest change leaves
generated artifacts stale.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_no_drift_between_manifests_and_committed_artifacts():
    cmd = [sys.executable, "-m", "docs.regen", "--all", "--check"]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "bootstrapper")}
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)
    if result.returncode == 2:
        pytest.fail(
            "Drift between committed docs and current manifests. Run:\n"
            "  python -m bootstrapper.docs.regen --all\n"
            "and commit the result.\n\n" + result.stdout
        )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 12.2: Run the test — expect failure (no artifacts written yet)**

Run: `cd bootstrapper && uv run pytest tests/test_docs_drift.py -v`
Expected: FAIL — drift detected (no `architecture.svg` files committed yet).

This failure is informative — Task 13 fixes it by regenerating + committing the artifacts.

- [ ] **Step 12.3: Commit the test (leaving it failing — will pass after Task 13)**

```bash
git add bootstrapper/tests/test_docs_drift.py
git commit -m "tests: add docs drift gate (failing until Task 13 regen runs)"
```

---

## Task 13: Run `regen --all` and commit the artifacts

**Files:**
- Modify: 21 × `docs/services/<name>/README.md`
- Create: 20 × `docs/services/<name>/architecture.html`
- Create: 20 × `docs/services/<name>/architecture.svg`

(20 not 21 — multi2vec-clip is the pointer-only case and gets no SVG.)

- [ ] **Step 13.1: Dry-run first to preview**

Run: `python -m bootstrapper.docs.regen --all --dry-run` (with `PYTHONPATH=bootstrapper`)

Expected: a list of `would write` lines covering 21 READMEs + 20 HTML files + 20 SVG files.

- [ ] **Step 13.2: Run for real**

Run: `PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all`

Expected: silent success (or a one-line summary). Inspect a sample:

```bash
ls docs/services/hermes/
ls docs/services/kong/
ls docs/services/multi2vec-clip/    # README only — no SVG/HTML
```

- [ ] **Step 13.3: Open three SVGs in a browser, eyeball them**

```bash
open docs/services/hermes/architecture.html
open docs/services/kong/architecture.html
open docs/services/stt-provider/architecture.html
```

Verify visually:
- Three lanes labeled correctly.
- Focus box centered.
- Edges look right; no overlapping boxes.
- Aggregate boundary (rose dashed) wraps the stt-provider focus.

- [ ] **Step 13.4: Run the drift gate — expect pass**

Run: `cd bootstrapper && uv run pytest tests/test_docs_drift.py -v`
Expected: PASS.

- [ ] **Step 13.5: Run the full bootstrapper test suite**

Run: `cd bootstrapper && uv run pytest -q`
Expected: all tests pass (baseline + new tests from Phase A).

- [ ] **Step 13.6: Run the link validator**

Run: `python scripts/check_doc_links.py`
Expected: exit 0 (no broken internal links). Specifically: zero references to the old `docs/services/<name>.md` paths.

- [ ] **Step 13.7: Commit the generated artifacts**

```bash
git add docs/services/
git commit -m "docs: regenerate all 21 service deps sections + architecture diagrams"
```

---

## Task 14: CHANGELOG + verification of Phase A acceptance gates

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 14.1: Append CHANGELOG entry**

Open `docs/CHANGELOG.md`. Add a new entry at the top following the existing convention (terse, third-person verb, no Co-Authored-By trailer). Use the project's standard format:

```markdown
## Unreleased

### Docs / Infra

- Migrated `docs/services/<name>.md` → `docs/services/<name>/README.md` (per-service folders).
- Added standardized **Dependencies & Integrations** subsection to every service README, with Current (manifest-derived) tables and Future (placeholder) subsections.
- Added per-service architecture diagrams (`architecture.html` + `architecture.svg`) under each service folder, generated from manifests via `python -m bootstrapper.docs.regen`.
- Added CI drift gate (`bootstrapper/tests/test_docs_drift.py`) that fails when committed deps sections or diagrams diverge from manifest state.
- Added internal-link validator (`scripts/check_doc_links.py`) covering README, CHANGELOG, and the whole `docs/` tree.
- New optional manifest fields: `runtime_adaptive.<container>.failure_mode` (string) and `doc_extras.diagram.extra_consumers` (list of service names).
```

- [ ] **Step 14.2: Verify Phase A acceptance gates** (spec §"Phase A acceptance gates")

Run each:

```bash
# Gate 1: regen --all runs clean
PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all
echo "Gate 1 exit: $?"   # expect 0

# Gate 2: drift test passes
cd bootstrapper && uv run pytest tests/test_docs_drift.py -v
# expect: 1 passed

cd $REPO_ROOT  # back to repo root

# Gate 3: Hermes golden-snapshot matches
cd bootstrapper && uv run pytest tests/test_diagram_renderer.py::test_svg_matches_golden_snapshot -v
# expect: 1 passed

cd $REPO_ROOT

# Gate 4: per-service folders exist with all three files
for d in docs/services/*/; do
  test -f "$d/README.md" || echo "MISSING: $d/README.md"
done
for d in docs/services/*/; do
  test "$(basename "$d")" = "multi2vec-clip" && continue
  test -f "$d/architecture.svg" || echo "MISSING: $d/architecture.svg"
  test -f "$d/architecture.html" || echo "MISSING: $d/architecture.html"
done
# expect: no MISSING lines

# Gate 5: no stale links to docs/services/<name>.md
python scripts/check_doc_links.py
echo "Gate 5 exit: $?"   # expect 0
grep -rE 'docs/services/[a-z-]+\.md' README.md docs/ || echo "ok: no stale paths"
# expect: ok line

# Gate 6: every README contains the deps section heading
for d in docs/services/*/; do
  grep -q "^## Dependencies & Integrations$" "$d/README.md" || echo "MISSING SECTION: $d/README.md"
done
# expect: no MISSING SECTION lines

# Gate 7: schema additions validate
cd bootstrapper && uv run pytest tests/test_manifests.py -v
# expect: all pass
```

- [ ] **Step 14.3: Commit CHANGELOG + close out Phase A**

```bash
git add docs/CHANGELOG.md
git commit -m "docs: changelog entry for cross-service deps + diagrams Phase A"
```

- [ ] **Step 14.4: Tag the Phase A landing point (optional but recommended)**

```bash
git tag phase-a-deps-foundations -m "Phase A complete: deps standardization + manifest-driven diagram generator"
```

---

## Phase A complete

You have shipped:

1. A new `bootstrapper/docs/` Python package with three modules + templates.
2. A `regen` CLI that produces deps sections, SVG diagrams, and HTML wrappers from manifests deterministically.
3. A CI drift gate (`test_docs_drift.py`) that prevents future drift.
4. A migration runner that converted `docs/services/<name>.md` to per-service folder layout.
5. A link validator (`scripts/check_doc_links.py`) covering the whole repo.
6. Two new optional manifest fields (`failure_mode`, `doc_extras.diagram.extra_consumers`).
7. 21 standardized service READMEs (with placeholder Future subsections, ready for Phase B/C to populate).
8. 20 per-service architecture diagrams (HTML + SVG).
9. A golden-snapshot test for Hermes pinning the visual style.
10. A CHANGELOG entry describing the migration.

**Phases B and C can now dispatch in parallel** against this foundation. Phase B's 21 subagents will fill `docs/research/rows/<name>.md`; Phase C will translate those into the Future subsections that today render the `_No high-confidence opportunities identified._` placeholder.
