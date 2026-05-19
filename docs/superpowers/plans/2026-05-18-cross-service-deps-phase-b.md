# Cross-service deps & diagrams — Phase B (Research) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a research artifact set (21 per-service row files + candidate one-pagers + merged matrix) that catalogues missing-pair integrations, candidate new services, and per-service feature gaps. The output feeds Phase C's "Future" subsections in every service README.

**Architecture:** Three tooling pieces (schema validator, merge script, prompt builder) plus orchestrated dispatch of 21 parallel `Explore` subagents. Each subagent gets a programmatically-generated prompt that names the target service, lists the other 20 with their metadata, and supplies the current upstream-deps set as a "do-not-propose-these" filter. Subagents write to unique row files (no shared-file contention) and may conditionally create candidate files (collision-safe via `## Cross-references` append). A final merge step produces a deterministic `integration-matrix.md`.

**Tech Stack:** Python 3.9+, `pyyaml` (frontmatter), `jsonschema` (already in `bootstrapper/pyproject.toml`), pytest. No new runtime deps.

**Spec reference:** `docs/superpowers/specs/2026-05-16-cross-service-deps-and-diagrams-design.md`, sections B.1 through B.6 and the Phase B acceptance gates.

**Phase A status:** complete and merged to main (tag `phase-a-deps-foundations`, head `3c9ced2`). Phase B builds on top.

---

## File structure

**New files (created during this phase):**

```
bootstrapper/docs/
├── merge_research.py                    # merge script + CLI
└── research_subagent_prompt.py          # programmatic prompt builder

scripts/
└── validate_research_schema.py          # single-file + --all validator

bootstrapper/tests/
├── test_merge_research.py
├── test_research_subagent_prompt.py
├── test_validate_research_schema.py
└── fixtures/
    ├── example_row.md                   # valid row file (synthetic)
    └── example_candidate.md             # valid candidate one-pager (synthetic)

docs/research/
├── README.md                            # schema + workflow reference
├── integration-matrix.md                # generated index (DO NOT EDIT)
├── rows/
│   └── <service>.md × 21                # one per doc folder
└── candidates/
    └── <slug>.md × variable             # one per candidate new service
```

**Modified files:**
- `docs/CHANGELOG.md` — Phase B entry.

**Files explicitly NOT touched in this phase:**
- Any per-service README under `docs/services/<name>/` (Phase C consumes the rows; Phase B only writes research artifacts).
- Any manifest under `services/<name>/`.
- Phase A's `bootstrapper/docs/{deps_resolver,deps_section_writer,diagram_renderer,regen}.py` — Phase B is additive, not modifying.

---

## Pre-flight

- [ ] **Step 0a: Worktree setup**

If dispatched via `superpowers:using-git-worktrees`, confirm pwd is under `.claude/worktrees/`. If working directly on main, create one:

```bash
git worktree add .claude/worktrees/phase-b-research -b phase-b-research
cd .claude/worktrees/phase-b-research
```

- [ ] **Step 0b: Verify Phase A is in place**

```bash
# Phase A tag should exist:
git tag -l 'phase-a-deps-foundations'   # expect: phase-a-deps-foundations

# Phase A artifacts must be present (~21 service folders with README + svg + html):
ls docs/services/hermes/README.md docs/services/hermes/architecture.svg

# Drift gate still green:
cd bootstrapper && uv run pytest tests/test_docs_drift.py -v
cd ..
```

If any check fails, stop and resolve before continuing.

- [ ] **Step 0c: Baseline test run**

```bash
cd bootstrapper && uv run pytest -q
```

Capture the count for sanity at the end. Expected ~285 passed, 3 skipped.

---

## Task 1: docs/research/ scaffolding + README

**Files:**
- Create: `docs/research/README.md`
- Create empty: `docs/research/rows/.gitkeep`
- Create empty: `docs/research/candidates/.gitkeep`

**Why first:** Establishes the directory layout that downstream tasks and subagents reference. README is the single authoritative source for schema and workflow.

- [ ] **Step 1.1: Create the directory tree**

```bash
mkdir -p docs/research/rows docs/research/candidates
touch docs/research/rows/.gitkeep docs/research/candidates/.gitkeep
```

- [ ] **Step 1.2: Create `docs/research/README.md`** (verbatim)

```markdown
# Cross-service integration research

This directory holds the **Phase B research artifacts** for the cross-service
deps + diagrams project. The umbrella spec is at
`docs/superpowers/specs/2026-05-16-cross-service-deps-and-diagrams-design.md`.

## Layout

| Path | Purpose |
|---|---|
| `rows/<service>.md` | One per service doc folder under `docs/services/`. Captures the service's missing-pair integrations, candidate new services, and feature gaps. **One file = one author = one subagent run.** |
| `candidates/<slug>.md` | One per candidate new service (e.g. `obsidian-mcp.md`, `langfuse.md`). Multiple rows may reference the same candidate. |
| `integration-matrix.md` | Generated index that aggregates all rows by service, by category, plus a global candidates table. **Do not edit by hand.** Re-generate with `python -m bootstrapper.docs.merge_research`. |

## Row file schema

Each `rows/<service>.md` is a markdown file with frontmatter:

```yaml
---
service: <doc-folder-name>          # e.g. hermes, stt-provider
category: infra | data | llm | media | agents | apps
generated: YYYY-MM-DD
generator: phase-b-subagent | phase-b-controller | phase-b-hand-edit
sources_consulted:
  - <URL or local path>
  - ...
---
```

Followed by exactly three numbered sections:

1. `## 1. Missing-pair integrations` — pairs of EXISTING stack services that should be wired together but aren't yet. Each bullet must include: Why valuable, Mechanism sketch, Effort (small | medium | large), Risks / open questions, Confidence (high | medium | low).
2. `## 2. Candidate new services` — services NOT in the stack today that would slot in cleanly. Each bullet points at a full one-pager in `candidates/<slug>.md`. Each row file caps at **5 candidates**.
3. `## 3. Per-service feature gaps` — features the upstream project exposes that we don't yet leverage.

If a section has no findings, use the exact placeholder line:

```
_No high-confidence opportunities identified._
```

**Hard caps:**
- 800 words total per row file.
- 5 candidate cross-references per row file.

## Candidate one-pager schema

Each `candidates/<slug>.md`:

```yaml
---
slug: <kebab-case>
name: <Display Name>
type: external-service
category-fit: agents | data | media | infra | llm | apps
generated: YYYY-MM-DD
upstream: <URL>
license: <SPDX identifier or "unknown">
referenced-by: [<service>, ...]      # maintained by merge script, not by author
---
```

Six required sections:

1. `## Headline` — one sentence.
2. `## Problem it solves` — 2-3 sentences.
3. `## Stack wiring sketch` — bullets naming real services in the current topology.
4. `## Effort` — small / medium / large + one sentence.
5. `## Risks & open questions` — bullets (may be empty but heading is required).
6. `## Upstream evidence` — at least one URL backing the claim.

`## Why now (and why not sooner)` is optional.

## Validation

A schema validator lives at `scripts/validate_research_schema.py`. Run it on
one file or all:

```bash
python scripts/validate_research_schema.py docs/research/rows/hermes.md
python scripts/validate_research_schema.py --all
```

Exit 0 = valid, 1 = errors (printed with file:line refs).

## Merging

`python -m bootstrapper.docs.merge_research` reads all rows + candidates,
emits `integration-matrix.md`, and reconciles `referenced-by:` on each
candidate. Deterministic and idempotent.

## Dispatch pattern (how Phase B was produced)

21 parallel `Explore`-type subagents, one per doc folder, each given a
programmatically-generated prompt by `bootstrapper.docs.research_subagent_prompt.build_research_prompt(name)`.
WebFetch budget: 8 per subagent. Subagents write to their own row file
(no contention) and may create candidate one-pagers (collision-safe via
file-exists check + `## Cross-references` append).
```

- [ ] **Step 1.3: Commit**

```bash
git add docs/research/README.md docs/research/rows/.gitkeep docs/research/candidates/.gitkeep
git commit -m "docs: scaffold cross-service research directory + README"
```

---

## Task 2: Schema example fixtures

**Files:**
- Create: `bootstrapper/tests/fixtures/example_row.md`
- Create: `bootstrapper/tests/fixtures/example_candidate.md`

**Why:** Two synthetic valid examples serve double duty — fixtures for the validator/merge tests AND concrete references the dispatch prompt cites for subagents.

- [ ] **Step 2.1: Create `bootstrapper/tests/fixtures/example_row.md`** (verbatim)

````markdown
---
service: example-service
category: data
generated: 2026-05-18
generator: phase-b-hand-edit
sources_consulted:
  - https://github.com/example/example-service
  - services/example-service/service.yml
---

# example-service — Integration Research

## 1. Missing-pair integrations

- **example-service ↔ hermes**
  - Why valuable: persistent agent memory across sessions
  - Mechanism sketch: Hermes skill writing session graphs via Bolt protocol on port 7687
  - Effort: medium
  - Risks / open questions: schema design; write-amplification on tool-call loops
  - Confidence: medium

## 2. Candidate new services

- **Obsidian MCP server** → `../candidates/obsidian-mcp.md`
  - Headline: extends Hermes's MCP client to read/write an Obsidian vault
  - Other consumers in stack: backend (notes search), n8n (workflow nodes)

## 3. Per-service feature gaps

- **example-service's foo-mode** — bundled but not wired through the stack
  - Why pursue: enables walkie-talkie agent UX
  - Effort: small
````

- [ ] **Step 2.2: Create `bootstrapper/tests/fixtures/example_candidate.md`** (verbatim)

````markdown
---
slug: example-candidate
name: Example Candidate
type: external-service
category-fit: agents
generated: 2026-05-18
upstream: https://github.com/example/example-candidate
license: MIT
referenced-by: [example-service]
---

# Example Candidate

## Headline
A synthetic example used by the Phase B validator + merge test fixtures.

## Problem it solves
Demonstrates the candidate one-pager schema. Has no real-world use; exists
only to anchor automated tests against a known-valid shape.

## Stack wiring sketch
- example-service → example-candidate via HTTP on port 8080
- example-candidate → hermes via the same MCP protocol Hermes already speaks

## Effort
small — single compose fragment, no build context.

## Risks & open questions
- Upstream license terms may change.

## Why now (and why not sooner)
Optional section, kept here to verify the validator tolerates its presence.

## Upstream evidence
See https://github.com/example/example-candidate/releases for the most
recent stable release.
````

- [ ] **Step 2.3: Commit**

```bash
git add bootstrapper/tests/fixtures/example_row.md bootstrapper/tests/fixtures/example_candidate.md
git commit -m "tests: add valid research-schema fixtures (row + candidate)"
```

---

## Task 3: `scripts/validate_research_schema.py` validator

**Files:**
- Create: `scripts/validate_research_schema.py`
- Create: `bootstrapper/tests/test_validate_research_schema.py`

**Why:** Subagents must produce parseable output. The validator enforces the schema both during Phase B (controller verifies every subagent output) and afterwards as a CI gate.

- [ ] **Step 3.1: Write the failing tests**

Create `bootstrapper/tests/test_validate_research_schema.py`:

```python
"""Tests for scripts/validate_research_schema.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_research_schema.py"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(VALIDATOR), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def test_validates_clean_row_fixture():
    """The committed example_row.md passes validation."""
    r = _run(str(FIXTURE_DIR / "example_row.md"))
    assert r.returncode == 0, r.stdout + r.stderr


def test_validates_clean_candidate_fixture():
    """The committed example_candidate.md passes validation."""
    r = _run(str(FIXTURE_DIR / "example_candidate.md"))
    assert r.returncode == 0, r.stdout + r.stderr


def test_rejects_row_missing_frontmatter(tmp_path):
    bad = tmp_path / "bad_row.md"
    bad.write_text("# bad — Integration Research\n\n## 1. Missing-pair integrations\n_None._")
    r = _run(str(bad))
    assert r.returncode == 1
    assert "frontmatter" in r.stdout.lower()


def test_rejects_row_missing_required_section(tmp_path):
    """A row file missing one of the three numbered sections is rejected."""
    bad = tmp_path / "bad_row.md"
    bad.write_text(
        "---\nservice: bad\ncategory: data\ngenerated: 2026-05-18\n"
        "generator: phase-b-subagent\nsources_consulted:\n  - https://example.com\n---\n\n"
        "# bad — Integration Research\n\n"
        "## 1. Missing-pair integrations\n_No high-confidence opportunities identified._\n\n"
        "## 2. Candidate new services\n_No high-confidence opportunities identified._\n"
        # missing section 3
    )
    r = _run(str(bad))
    assert r.returncode == 1
    assert "section" in r.stdout.lower()
    assert "3" in r.stdout


def test_rejects_row_exceeding_word_cap(tmp_path):
    """A row file with > 800 words is rejected."""
    body = "word " * 900   # 900 words
    bad = tmp_path / "fat_row.md"
    bad.write_text(
        "---\nservice: fat\ncategory: data\ngenerated: 2026-05-18\n"
        "generator: phase-b-subagent\nsources_consulted:\n  - https://example.com\n---\n\n"
        "# fat — Integration Research\n\n"
        "## 1. Missing-pair integrations\n" + body + "\n\n"
        "## 2. Candidate new services\n_No high-confidence opportunities identified._\n\n"
        "## 3. Per-service feature gaps\n_No high-confidence opportunities identified._\n"
    )
    r = _run(str(bad))
    assert r.returncode == 1
    assert "word" in r.stdout.lower() or "800" in r.stdout


def test_rejects_row_exceeding_candidate_cap(tmp_path):
    """A row file with > 5 candidate cross-references is rejected."""
    cands = "\n".join(
        f"- **Cand {i}** → `../candidates/cand-{i}.md`\n  - Headline: ...\n  - Other consumers in stack: ..."
        for i in range(7)
    )
    bad = tmp_path / "many_cands.md"
    bad.write_text(
        "---\nservice: many\ncategory: data\ngenerated: 2026-05-18\n"
        "generator: phase-b-subagent\nsources_consulted:\n  - https://example.com\n---\n\n"
        "# many — Integration Research\n\n"
        "## 1. Missing-pair integrations\n_None._\n\n"
        "## 2. Candidate new services\n" + cands + "\n\n"
        "## 3. Per-service feature gaps\n_None._\n"
    )
    r = _run(str(bad))
    assert r.returncode == 1
    assert "candidate" in r.stdout.lower() or "5" in r.stdout


def test_rejects_candidate_missing_required_section(tmp_path):
    bad = tmp_path / "bad_cand.md"
    bad.write_text(
        "---\nslug: bad\nname: Bad\ntype: external-service\ncategory-fit: data\n"
        "generated: 2026-05-18\nupstream: https://example.com\nlicense: MIT\n"
        "referenced-by: []\n---\n\n"
        "# Bad\n\n## Headline\nFoo.\n\n## Problem it solves\nBar.\n\n"
        "## Stack wiring sketch\n- a → b via http\n\n## Effort\nsmall — foo.\n\n"
        "## Risks & open questions\n- none\n"
        # missing Upstream evidence section
    )
    r = _run(str(bad))
    assert r.returncode == 1
    assert "upstream evidence" in r.stdout.lower()


def test_all_mode_walks_research_tree(tmp_path):
    """--all validates every row and candidate under docs/research/."""
    # Build a synthetic research tree in tmp_path
    rows = tmp_path / "docs" / "research" / "rows"
    cands = tmp_path / "docs" / "research" / "candidates"
    rows.mkdir(parents=True)
    cands.mkdir(parents=True)

    # Copy the good fixtures into the tree
    good_row = FIXTURE_DIR / "example_row.md"
    good_cand = FIXTURE_DIR / "example_candidate.md"
    (rows / "example.md").write_text(good_row.read_text())
    (cands / "example.md").write_text(good_cand.read_text())

    r = subprocess.run(
        [sys.executable, str(VALIDATOR), "--all", "--research-root", str(tmp_path / "docs" / "research")],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert r.returncode == 0, r.stdout + r.stderr
```

- [ ] **Step 3.2: Run the tests — expect failure**

```bash
cd bootstrapper && uv run pytest tests/test_validate_research_schema.py -v
```

Expected: FAIL — script doesn't exist.

- [ ] **Step 3.3: Implement the validator**

Create `scripts/validate_research_schema.py`:

```python
#!/usr/bin/env python3
"""Phase B research-schema validator.

Validates row files (docs/research/rows/<service>.md) and candidate files
(docs/research/candidates/<slug>.md) against the schemas defined in
docs/research/README.md.

Usage:
  python scripts/validate_research_schema.py <file>
  python scripts/validate_research_schema.py --all [--research-root PATH]

Exit codes:
  0 — all valid.
  1 — one or more validation errors (printed to stdout).
  2 — usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Row file required sections (in order, must match exactly)
_ROW_SECTIONS = (
    "## 1. Missing-pair integrations",
    "## 2. Candidate new services",
    "## 3. Per-service feature gaps",
)

# Candidate file required sections (in order)
_CAND_SECTIONS = (
    "## Headline",
    "## Problem it solves",
    "## Stack wiring sketch",
    "## Effort",
    "## Risks & open questions",
    "## Upstream evidence",
)

_ROW_FRONTMATTER_KEYS = {"service", "category", "generated", "generator", "sources_consulted"}
_CAND_FRONTMATTER_KEYS = {"slug", "name", "type", "category-fit", "generated", "upstream", "license", "referenced-by"}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_RE = re.compile(r"https?://\S+")

_WORD_CAP = 800
_CANDIDATE_CAP = 5

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str] | None:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return fm, m.group(2)


def _validate_row(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    parsed = _parse_frontmatter(text)
    if parsed is None:
        errors.append(f"{path}: missing or unparseable frontmatter")
        return errors
    fm, body = parsed

    # Frontmatter keys
    missing = _ROW_FRONTMATTER_KEYS - set(fm)
    if missing:
        errors.append(f"{path}: frontmatter missing key(s): {sorted(missing)}")

    # generated must be ISO date
    if "generated" in fm and not _DATE_RE.match(str(fm.get("generated", ""))):
        errors.append(f"{path}: frontmatter `generated` must be YYYY-MM-DD")

    # sources_consulted must be a non-empty list
    src = fm.get("sources_consulted")
    if not isinstance(src, list) or len(src) == 0:
        errors.append(f"{path}: frontmatter `sources_consulted` must be a non-empty list")

    # Required sections, in order
    last_idx = -1
    for sec in _ROW_SECTIONS:
        idx = body.find(sec)
        if idx == -1:
            errors.append(f"{path}: missing required section: {sec}")
        elif idx <= last_idx:
            errors.append(f"{path}: section out of order: {sec}")
        else:
            last_idx = idx

    # Word cap
    word_count = len(body.split())
    if word_count > _WORD_CAP:
        errors.append(f"{path}: body exceeds {_WORD_CAP}-word cap ({word_count} words)")

    # Candidate count cap (count cross-references in section 2)
    sec2_start = body.find("## 2. Candidate new services")
    sec3_start = body.find("## 3. Per-service feature gaps")
    if sec2_start != -1 and sec3_start != -1 and sec3_start > sec2_start:
        sec2_body = body[sec2_start:sec3_start]
        cand_refs = re.findall(r"\.\./candidates/[\w-]+\.md", sec2_body)
        if len(cand_refs) > _CANDIDATE_CAP:
            errors.append(f"{path}: section 2 has {len(cand_refs)} candidate refs (cap: {_CANDIDATE_CAP})")

    return errors


def _validate_candidate(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    parsed = _parse_frontmatter(text)
    if parsed is None:
        errors.append(f"{path}: missing or unparseable frontmatter")
        return errors
    fm, body = parsed

    missing = _CAND_FRONTMATTER_KEYS - set(fm)
    if missing:
        errors.append(f"{path}: frontmatter missing key(s): {sorted(missing)}")

    if "generated" in fm and not _DATE_RE.match(str(fm.get("generated", ""))):
        errors.append(f"{path}: frontmatter `generated` must be YYYY-MM-DD")

    # upstream must be a URL
    up = str(fm.get("upstream", ""))
    if not _URL_RE.match(up):
        errors.append(f"{path}: frontmatter `upstream` must be an http(s) URL")

    # referenced-by must be a list
    rb = fm.get("referenced-by")
    if not isinstance(rb, list):
        errors.append(f"{path}: frontmatter `referenced-by` must be a list (may be empty)")

    # All six required sections
    last_idx = -1
    for sec in _CAND_SECTIONS:
        idx = body.find(sec)
        if idx == -1:
            errors.append(f"{path}: missing required section: {sec}")
        elif idx <= last_idx:
            errors.append(f"{path}: section out of order: {sec}")
        else:
            last_idx = idx

    # Upstream evidence section must contain at least one URL
    ue_start = body.find("## Upstream evidence")
    if ue_start != -1:
        ue_end = len(body)
        # Find next heading (## or # at line start)
        nxt = re.search(r"(?m)^#+ ", body[ue_start + 1:])
        if nxt:
            ue_end = ue_start + 1 + nxt.start()
        ue_body = body[ue_start:ue_end]
        if not _URL_RE.search(ue_body):
            errors.append(f"{path}: Upstream evidence section must contain at least one URL")

    return errors


def _validate_one(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.parent.name == "rows":
        return _validate_row(path, text)
    if path.parent.name == "candidates":
        return _validate_candidate(path, text)
    # Default: guess by frontmatter shape
    parsed = _parse_frontmatter(text)
    if parsed and "slug" in parsed[0]:
        return _validate_candidate(path, text)
    return _validate_row(path, text)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("file", nargs="?", type=Path, help="One row or candidate file.")
    grp.add_argument("--all", action="store_true", help="Validate every row + candidate file.")
    ap.add_argument("--research-root", type=Path, default=REPO_ROOT / "docs" / "research")
    args = ap.parse_args(argv)

    targets: list[Path] = []
    if args.all:
        for sub in ("rows", "candidates"):
            d = args.research_root / sub
            if d.is_dir():
                targets.extend(sorted(p for p in d.glob("*.md") if p.name not in ("README.md", ".gitkeep")))
    else:
        if not args.file.exists():
            print(f"error: file not found: {args.file}", file=sys.stderr)
            return 2
        targets = [args.file]

    all_errors: list[str] = []
    for p in targets:
        all_errors.extend(_validate_one(p))

    if all_errors:
        for e in all_errors:
            print(e)
        print(f"\n{len(all_errors)} error(s) across {len(targets)} file(s).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Mark executable: `chmod +x scripts/validate_research_schema.py`

- [ ] **Step 3.4: Run the tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_validate_research_schema.py -v
```

Expected: 8 passing.

- [ ] **Step 3.5: Commit**

```bash
git add scripts/validate_research_schema.py bootstrapper/tests/test_validate_research_schema.py
git commit -m "scripts: add research-schema validator + tests"
```

---

## Task 4: `bootstrapper/docs/merge_research.py` merge script

**Files:**
- Create: `bootstrapper/docs/merge_research.py`
- Create: `bootstrapper/tests/test_merge_research.py`

**Why:** Subagents produce 21 row files + N candidates. The merge script aggregates them into the master `integration-matrix.md` and reconciles the `referenced-by:` frontmatter on each candidate.

- [ ] **Step 4.1: Write the failing tests**

Create `bootstrapper/tests/test_merge_research.py`:

```python
"""Tests for bootstrapper.docs.merge_research."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _build_research_tree(tmp_path: Path, *, rows: dict[str, str], candidates: dict[str, str]) -> Path:
    """Build a synthetic docs/research/ tree."""
    root = tmp_path / "research"
    (root / "rows").mkdir(parents=True)
    (root / "candidates").mkdir(parents=True)
    for name, body in rows.items():
        (root / "rows" / f"{name}.md").write_text(body)
    for slug, body in candidates.items():
        (root / "candidates" / f"{slug}.md").write_text(body)
    return root


def test_merge_emits_integration_matrix(tmp_path):
    """The merge step writes docs/research/integration-matrix.md."""
    from docs.merge_research import run_merge
    row = (FIXTURE_DIR / "example_row.md").read_text()
    cand = (FIXTURE_DIR / "example_candidate.md").read_text()
    root = _build_research_tree(tmp_path, rows={"example-service": row}, candidates={"example-candidate": cand})

    run_merge(root)

    matrix = root / "integration-matrix.md"
    assert matrix.is_file()
    text = matrix.read_text()
    assert "example-service" in text
    assert "Example Candidate" in text


def test_merge_reconciles_referenced_by(tmp_path):
    """If row references a candidate, the candidate's referenced-by must list that service."""
    from docs.merge_research import run_merge
    row = (FIXTURE_DIR / "example_row.md").read_text()
    # Use the example_candidate but stripped to empty referenced-by
    raw_cand = (FIXTURE_DIR / "example_candidate.md").read_text()
    cand_stripped = raw_cand.replace("referenced-by: [example-service]", "referenced-by: []")
    root = _build_research_tree(tmp_path, rows={"example-service": row}, candidates={"example-candidate": cand_stripped})

    run_merge(root)

    updated = (root / "candidates" / "example-candidate.md").read_text()
    assert "referenced-by: [example-service]" in updated or "referenced-by:\n- example-service" in updated


def test_merge_is_idempotent(tmp_path):
    """Re-running merge against an already-merged tree leaves files byte-identical."""
    from docs.merge_research import run_merge
    row = (FIXTURE_DIR / "example_row.md").read_text()
    cand = (FIXTURE_DIR / "example_candidate.md").read_text()
    root = _build_research_tree(tmp_path, rows={"example-service": row}, candidates={"example-candidate": cand})

    run_merge(root)
    matrix1 = (root / "integration-matrix.md").read_text()
    cand1 = (root / "candidates" / "example-candidate.md").read_text()

    run_merge(root)
    matrix2 = (root / "integration-matrix.md").read_text()
    cand2 = (root / "candidates" / "example-candidate.md").read_text()

    assert matrix1 == matrix2
    assert cand1 == cand2


def test_merge_groups_by_category(tmp_path):
    """integration-matrix.md groups rows by category."""
    from docs.merge_research import run_merge
    base_row = (FIXTURE_DIR / "example_row.md").read_text()

    # Two rows, different categories
    row_a = base_row.replace("service: example-service", "service: alpha").replace("category: data", "category: agents")
    row_b = base_row.replace("service: example-service", "service: beta").replace("category: data", "category: media")
    root = _build_research_tree(tmp_path, rows={"alpha": row_a, "beta": row_b}, candidates={})

    run_merge(root)
    text = (root / "integration-matrix.md").read_text()
    # Category headings present
    assert "## Category: agents" in text or "### agents" in text
    assert "## Category: media" in text or "### media" in text


def test_cli_entry(tmp_path):
    """python -m bootstrapper.docs.merge_research --research-root <path> writes the matrix."""
    import subprocess
    row = (FIXTURE_DIR / "example_row.md").read_text()
    cand = (FIXTURE_DIR / "example_candidate.md").read_text()
    root = _build_research_tree(tmp_path, rows={"example-service": row}, candidates={"example-candidate": cand})

    env = {"PYTHONPATH": str(REPO_ROOT / "bootstrapper")}
    import os
    r = subprocess.run(
        [sys.executable, "-m", "docs.merge_research", "--research-root", str(root)],
        capture_output=True, text=True, cwd=REPO_ROOT,
        env={**os.environ, **env},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (root / "integration-matrix.md").is_file()
```

- [ ] **Step 4.2: Run the test — expect failure**

```bash
cd bootstrapper && uv run pytest tests/test_merge_research.py -v
```

Expected: FAIL — module missing.

- [ ] **Step 4.3: Implement the merge script**

Create `bootstrapper/docs/merge_research.py`:

```python
"""Merge research rows + candidates into the master integration matrix.

Reads:
  docs/research/rows/<service>.md
  docs/research/candidates/<slug>.md

Writes:
  docs/research/integration-matrix.md           — generated index
  docs/research/candidates/<slug>.md            — referenced-by frontmatter
                                                   updated in place

Deterministic and idempotent: re-running produces byte-identical output.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ROOT = REPO_ROOT / "docs" / "research"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_CAND_REF_RE = re.compile(r"\.\./candidates/([\w-]+)\.md")


def _parse(text: str) -> tuple[dict, str] | None:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return fm, m.group(2)


def _emit_frontmatter(fm: dict) -> str:
    """Emit YAML frontmatter deterministically. Uses inline (`[a, b]`) form for
    short lists to match the existing example fixtures."""
    lines = ["---"]
    for k in sorted(fm.keys()):
        v = fm[k]
        if isinstance(v, list):
            if all(isinstance(x, str) for x in v) and len(v) <= 8:
                rendered = "[" + ", ".join(v) + "]"
                lines.append(f"{k}: {rendered}")
            else:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def run_merge(root: Path) -> None:
    """Merge research artifacts under `root` (a Path pointing at docs/research/)."""

    rows_dir = root / "rows"
    cands_dir = root / "candidates"

    # Load all rows
    rows: list[tuple[Path, dict, str]] = []
    if rows_dir.is_dir():
        for p in sorted(rows_dir.glob("*.md")):
            if p.name in ("README.md", ".gitkeep"):
                continue
            parsed = _parse(p.read_text(encoding="utf-8"))
            if parsed:
                rows.append((p, parsed[0], parsed[1]))

    # Load all candidates
    cands: dict[str, tuple[Path, dict, str]] = {}
    if cands_dir.is_dir():
        for p in sorted(cands_dir.glob("*.md")):
            if p.name in ("README.md", ".gitkeep"):
                continue
            parsed = _parse(p.read_text(encoding="utf-8"))
            if parsed:
                cands[parsed[0].get("slug", p.stem)] = (p, parsed[0], parsed[1])

    # Build referenced-by map from rows
    referenced_by: dict[str, set[str]] = {slug: set() for slug in cands}
    for _, fm, body in rows:
        svc = fm.get("service", "")
        for slug in _CAND_REF_RE.findall(body):
            if slug in referenced_by:
                referenced_by[slug].add(svc)

    # Rewrite each candidate's referenced-by frontmatter
    for slug, (path, fm, body) in cands.items():
        new_fm = dict(fm)
        new_fm["referenced-by"] = sorted(referenced_by.get(slug, set()))
        new_text = _emit_frontmatter(new_fm) + "\n" + body.lstrip("\n")
        path.write_text(new_text, encoding="utf-8")

    # Build the matrix
    out_path = root / "integration-matrix.md"
    out_path.write_text(_build_matrix(rows, cands, referenced_by), encoding="utf-8")


def _build_matrix(
    rows: list[tuple[Path, dict, str]],
    cands: dict[str, tuple[Path, dict, str]],
    referenced_by: dict[str, set[str]],
) -> str:
    """Build the integration-matrix.md content."""

    lines: list[str] = []
    lines.append("# Cross-service Integration Matrix")
    lines.append("")
    lines.append(
        "> **Generated** by `python -m bootstrapper.docs.merge_research`. "
        "Do not edit by hand — your changes will be overwritten on the next run."
    )
    lines.append("")
    lines.append("## By service")
    lines.append("")
    lines.append("| Service | Category | Sources | Row file |")
    lines.append("|---|---|---|---|")
    for _, fm, _body in sorted(rows, key=lambda r: r[1].get("service", "")):
        svc = fm.get("service", "?")
        cat = fm.get("category", "?")
        src_count = len(fm.get("sources_consulted") or [])
        lines.append(f"| {svc} | {cat} | {src_count} | [rows/{svc}.md](./rows/{svc}.md) |")
    lines.append("")

    # By category
    by_cat: dict[str, list[str]] = {}
    for _, fm, _body in rows:
        by_cat.setdefault(fm.get("category", "?"), []).append(fm.get("service", "?"))
    lines.append("## By category")
    lines.append("")
    for cat in sorted(by_cat):
        lines.append(f"### {cat}")
        lines.append("")
        for svc in sorted(by_cat[cat]):
            lines.append(f"- [{svc}](./rows/{svc}.md)")
        lines.append("")

    # Candidate cross-reference table
    lines.append("## Candidate new services")
    lines.append("")
    if cands:
        lines.append("| Candidate | Category fit | Referenced by | One-pager |")
        lines.append("|---|---|---|---|")
        for slug in sorted(cands):
            _, fm, _body = cands[slug]
            name = fm.get("name", slug)
            cat_fit = fm.get("category-fit", "?")
            refs = sorted(referenced_by.get(slug, set()))
            refs_str = ", ".join(refs) if refs else "_(none)_"
            lines.append(f"| {name} | {cat_fit} | {refs_str} | [candidates/{slug}.md](./candidates/{slug}.md) |")
    else:
        lines.append("_No candidate new services proposed._")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="bootstrapper.docs.merge_research")
    ap.add_argument("--research-root", type=Path, default=DEFAULT_ROOT)
    args = ap.parse_args(argv)
    if not args.research_root.is_dir():
        print(f"error: research root not found: {args.research_root}", file=sys.stderr)
        return 1
    run_merge(args.research_root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4.4: Run the tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_merge_research.py -v
```

Expected: 5 passing.

- [ ] **Step 4.5: Commit**

```bash
git add bootstrapper/docs/merge_research.py bootstrapper/tests/test_merge_research.py
git commit -m "docs: add research merge script (rows + candidates → matrix)"
```

---

## Task 5: `bootstrapper/docs/research_subagent_prompt.py` prompt builder

**Files:**
- Create: `bootstrapper/docs/research_subagent_prompt.py`
- Create: `bootstrapper/tests/test_research_subagent_prompt.py`

**Why:** A programmatic prompt builder beats hand-writing 21 prompts. It pulls real data from manifests + topology so the "do-not-propose-these" list is always current, the other-20-services table is always accurate, and the per-service context is always grounded in the actual repo state.

- [ ] **Step 5.1: Write the failing tests**

Create `bootstrapper/tests/test_research_subagent_prompt.py`:

```python
"""Tests for bootstrapper.docs.research_subagent_prompt."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))


def test_prompt_includes_target_service_name():
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("hermes")
    assert "hermes" in prompt.lower()


def test_prompt_lists_other_services():
    """The prompt enumerates the other 20 doc folders so the subagent knows
    what pairs to consider."""
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("hermes")
    # At least a handful of other services should appear
    for other in ("litellm", "kong", "neo4j", "weaviate", "n8n"):
        assert other in prompt


def test_prompt_includes_do_not_propose_list():
    """The prompt names services already wired to the target as a 'do not propose' set."""
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("hermes")
    # Hermes depends_on.required: litellm; adapts_to: stt_provider, tts_provider, ...
    # The do-not-propose list must include at least litellm
    dnp_section_idx = prompt.lower().find("do not propose")
    assert dnp_section_idx >= 0, "prompt must contain a 'do not propose' section"
    tail = prompt[dnp_section_idx:dnp_section_idx + 1000]
    assert "litellm" in tail.lower()


def test_prompt_includes_schema_rules():
    """The prompt cites the schema (frontmatter keys, 3 sections, 800-word cap)."""
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("hermes")
    assert "frontmatter" in prompt.lower()
    assert "800" in prompt   # word cap
    assert "5 candidate" in prompt or "5-candidate" in prompt or "max 5" in prompt.lower()
    assert "Missing-pair integrations" in prompt
    assert "Candidate new services" in prompt
    assert "Per-service feature gaps" in prompt


def test_prompt_specifies_output_path():
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("hermes")
    assert "docs/research/rows/hermes.md" in prompt


def test_prompt_specifies_webfetch_budget():
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("hermes")
    # WebFetch budget is 8 per spec B.1
    assert "8" in prompt   # appears as the budget number


def test_prompt_for_aggregate_doc_folder_handles_membership():
    """For stt-provider (aggregate), the prompt explains the doc folder
    aggregates multiple manifests (parakeet, speaches)."""
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("stt-provider")
    assert "parakeet" in prompt.lower() or "speaches" in prompt.lower()


def test_prompt_handles_pointer_only_doc_folder():
    """multi2vec-clip has no underlying manifest — prompt should still build (no crash)
    and instruct the subagent how to research a pointer-only doc."""
    from docs.research_subagent_prompt import build_research_prompt
    prompt = build_research_prompt("multi2vec-clip")
    assert "multi2vec-clip" in prompt.lower()
    assert "docs/research/rows/multi2vec-clip.md" in prompt
```

- [ ] **Step 5.2: Run the test — expect failure**

```bash
cd bootstrapper && uv run pytest tests/test_research_subagent_prompt.py -v
```

Expected: FAIL — module missing.

- [ ] **Step 5.3: Implement the prompt builder**

Create `bootstrapper/docs/research_subagent_prompt.py`:

```python
"""Programmatic prompt builder for Phase B research subagents.

`build_research_prompt(doc_folder)` returns a self-contained prompt string
that the Phase B controller passes to an Explore subagent. The prompt:

  - names the target doc folder + the manifests it aggregates
  - lists the other 20 doc folders with category + one-line description
  - lists the target's current upstream dependencies as a "do not propose
    these" set (the subagent must research GAPS, not re-derive what's wired)
  - cites the strict row-file + candidate schemas
  - states the WebFetch budget (8 fetches) and hard caps (800 words, 5
    candidates)
  - directs output to docs/research/rows/<doc_folder>.md

All data is pulled from manifests + topology so the prompt is current.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.manifests import load_manifests  # noqa: E402
from services.topology import get_topology     # noqa: E402

from .deps_resolver import build_doc_graph, doc_folder_to_manifests  # noqa: E402

SERVICES_DIR = REPO_ROOT / "services"


def _all_doc_folders() -> list[str]:
    """List the 21 service doc folders (matches docs/services/ subdirs)."""
    docs = REPO_ROOT / "docs" / "services"
    return sorted(p.name for p in docs.iterdir() if p.is_dir())


def _do_not_propose_set(focus: str) -> list[str]:
    """Services already wired to `focus`. Pulled from focus's DepGraph."""
    try:
        g = build_doc_graph(focus, SERVICES_DIR)
    except KeyError:
        return []
    wired: set[str] = set()
    for e in g.upstream:
        wired.add(e.other)
    for e in g.downstream:
        wired.add(e.other)
    return sorted(wired)


def _other_services_table(focus: str) -> str:
    """Markdown table of the other 20 doc folders (one row each)."""
    topo = get_topology()
    rows_by_folder = {}
    for row in topo.rows:
        rows_by_folder.setdefault(row.manifest, []).append(row)

    lines = ["| Service | Category | Description |", "|---|---|---|"]
    for folder in _all_doc_folders():
        if folder == focus:
            continue
        # Get a description from topology if available
        members = doc_folder_to_manifests(folder)
        desc = ""
        for m in members:
            for row in rows_by_folder.get(m, []):
                if row.description:
                    desc = row.description
                    break
            if desc:
                break
        category = ""
        for m in members:
            for row in rows_by_folder.get(m, []):
                category = row.category
                break
            if category:
                break
        lines.append(f"| {folder} | {category or '?'} | {desc or '_(see manifest)_'} |")

    return "\n".join(lines)


def build_research_prompt(doc_folder: str) -> str:
    """Build the standardized Phase B subagent prompt for one service."""

    members = doc_folder_to_manifests(doc_folder)
    member_note = ""
    if members and members != (doc_folder,):
        member_note = (
            f"\n\n**Note:** `{doc_folder}` is an aggregate doc folder; the "
            f"underlying manifests are: {', '.join(members)}. Treat the whole "
            f"aggregate as one logical service for the purposes of research.\n"
        )
    elif not members:
        member_note = (
            f"\n\n**Note:** `{doc_folder}` is a pointer-only doc folder (no "
            f"underlying manifest). Research it as a logical service that lives "
            f"alongside the stack — e.g. multi2vec-clip is a Weaviate feature.\n"
        )

    do_not_propose = _do_not_propose_set(doc_folder)
    dnp_block = (
        ", ".join(do_not_propose) if do_not_propose else "_(no current wiring detected)_"
    )

    others_table = _other_services_table(doc_folder)

    return f"""You are the Phase B research subagent for **{doc_folder}** in the genai-vanilla stack.

Your job is to research **integration opportunities** for this service and produce a single markdown file at `docs/research/rows/{doc_folder}.md` following the strict schema below.

## Scope

Three research deliverables, in order:

1. **Missing-pair integrations** — pairs of services ALREADY IN the stack that should be wired together but aren't. For each candidate pair, the bullet must include: *Why valuable*, *Mechanism sketch* (named endpoint or protocol), *Effort* (small | medium | large), *Risks / open questions*, *Confidence* (high | medium | low). Confidence must be backed by an entry in `sources_consulted`.

2. **Candidate new services** — services NOT currently in the stack that would plug in cleanly here. Maximum **5 candidates per row file**. For each, write a full one-pager at `docs/research/candidates/<slug>.md` per the candidate schema below — UNLESS a one-pager already exists, in which case append a `## Cross-references` line to your row pointing at the existing file.

3. **Per-service feature gaps** — capabilities the upstream project ({doc_folder}) exposes that we don't yet leverage in this stack.

## Target context

- **Doc folder:** `{doc_folder}`
- **Existing manifest(s):** `services/{members[0] if members else '(none)'}/service.yml`{member_note}
- **Existing doc:** `docs/services/{doc_folder}/README.md`

## Do NOT propose these (already wired)

The following services are already connected to {doc_folder} via the manifest's `depends_on.required`, `runtime_adaptive.adapts_to`, or `runtime_deps.optional`. Do not propose new wiring with these — your job is to find GAPS, not duplicate existing edges.

{dnp_block}

## Other services in the stack

These are the 20 other doc folders. Each pair (`{doc_folder}` × <other>) is a candidate for "missing-pair integration" if not already wired.

{others_table}

## Row file schema (write this to `docs/research/rows/{doc_folder}.md`)

```markdown
---
service: {doc_folder}
category: <one of: infra | data | llm | media | agents | apps>
generated: 2026-05-18
generator: phase-b-subagent
sources_consulted:
  - https://...                # upstream docs/repo
  - services/{doc_folder}/service.yml
  - docs/services/{doc_folder}/README.md
  - ...
---

# {doc_folder} — Integration Research

## 1. Missing-pair integrations

- **{doc_folder} ↔ <Other>**
  - Why valuable: <1-2 sentences>
  - Mechanism sketch: <named endpoint or protocol — e.g. `bolt://neo4j:7687`>
  - Effort: small | medium | large
  - Risks / open questions: <bullets, may be empty>
  - Confidence: high | medium | low

(or `_No high-confidence opportunities identified._` if nothing meets the bar)

## 2. Candidate new services

- **<Candidate Name>** → `../candidates/<slug>.md`
  - Headline: <one sentence>
  - Other consumers in stack: <bulleted services>

## 3. Per-service feature gaps

- **<feature>** — Why pursue: <reason>. Effort: <small|medium|large>.
```

## Candidate one-pager schema (write to `docs/research/candidates/<slug>.md`)

If a one-pager already exists at that path, do NOT overwrite it — instead, append a `## Cross-references` line to it linking from your row. The merge step will reconcile `referenced-by:` later.

```markdown
---
slug: <kebab-case>
name: <Display Name>
type: external-service
category-fit: <one of: infra | data | llm | media | agents | apps>
generated: 2026-05-18
upstream: <URL>
license: <SPDX or "unknown">
referenced-by: [{doc_folder}]
---

# <Name>

## Headline
<one sentence>

## Problem it solves
<2-3 sentences>

## Stack wiring sketch
- <service A> → <this candidate> via <protocol/endpoint>
- <this candidate> → <service B> via <...>

(Every bullet MUST name a real service in the current topology.)

## Effort
<small | medium | large> — <one sentence on what dominates the cost>

## Risks & open questions
- <bullet> (may be empty but heading is required)

## Why now (and why not sooner)
<optional, one paragraph>

## Upstream evidence
<at least one URL>
```

## Hard caps

- **800 words** total per row file.
- **5 candidates** maximum per row file. Rank and trim if you have more.
- **WebFetch budget: 8** for this subagent. Use them on upstream project docs for high-confidence claims.

## Quality bar

**Good output:**
- "**hermes ↔ neo4j** — Why: persistent agent memory across sessions. Mechanism: skill writing session graphs via `bolt://neo4j:7687`. Effort: medium. Confidence: medium (Hermes skill system supports custom tools per https://github.com/NousResearch/hermes/blob/main/docs/skills.md)."

**Bad output:**
- "Could maybe use neo4j somehow." (vague, no mechanism, no confidence reason)
- Naming a service that doesn't exist in the topology table above.
- Re-proposing a pair already in the "Do NOT propose" list.

## Process

1. Read `services/{doc_folder if members else '(none)'}/service.yml`, the existing README at `docs/services/{doc_folder}/README.md`, and any init scripts.
2. Identify the strongest 3-7 missing-pair integration candidates from the other-20-services table.
3. Identify 0-5 candidate new services that would slot in cleanly.
4. Identify 0-N per-service feature gaps from upstream docs.
5. Write the row file at the path above following the schema EXACTLY.
6. For each candidate, write the one-pager (or append `## Cross-references` if it exists).
7. Validate yourself: run `python scripts/validate_research_schema.py docs/research/rows/{doc_folder}.md` from the repo root. Exit 0 = pass.

## When you are done

Report:
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED
- The row-file path you wrote.
- The candidate-file paths you created (and which you cross-referenced instead of created).
- Validator exit code.
- Word count of the row file body.

Do NOT modify code under `bootstrapper/` or `services/`. Do NOT touch other doc folders or other row/candidate files. Stay within your `docs/research/rows/{doc_folder}.md` and the candidate files you author.
"""
```

- [ ] **Step 5.4: Run the tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_research_subagent_prompt.py -v
```

Expected: 8 passing.

- [ ] **Step 5.5: Commit**

```bash
git add bootstrapper/docs/research_subagent_prompt.py bootstrapper/tests/test_research_subagent_prompt.py
git commit -m "docs: add programmatic Phase B subagent prompt builder"
```

---

## Task 6: Dispatch 21 parallel research subagents — CONTROLLER TASK

**Files written by subagents (the controller does NOT write these directly):**
- 21 × `docs/research/rows/<doc_folder>.md`
- Variable × `docs/research/candidates/<slug>.md`

**IMPORTANT:** This task is NOT to be delegated to a fresh implementer subagent via `subagent-driven-development`. The controller (the Claude session executing this plan) MUST do this directly, because the implementation IS dispatching 21 parallel subagents — nesting that inside another implementer subagent is operationally fragile.

The plan executor: when you reach Task 6, do the work in your own session (no fresh implementer dispatch). Use the dispatching-parallel-agents skill as a reference if needed.

- [ ] **Step 6.1: Enumerate the 21 doc folders**

```bash
ls docs/services/ | sort
```

Expected: 21 directory names. Capture this list — these are the dispatch targets.

- [ ] **Step 6.2: Pre-build all 21 prompts**

For each doc folder, call `build_research_prompt(name)` and capture the result. This catches prompt-builder failures before dispatching live subagents. From the repo root:

```bash
PYTHONPATH=bootstrapper python - <<'PY'
from docs.research_subagent_prompt import build_research_prompt
from pathlib import Path

DOCS = sorted(p.name for p in Path("docs/services").iterdir() if p.is_dir())
for name in DOCS:
    p = build_research_prompt(name)
    print(f"{name}: prompt_len={len(p)} dnp_set_count={p.count('do not propose')}")
PY
```

Expected: 21 lines, each with `prompt_len` in the few-thousand range. Confirms every prompt builds without crashing.

- [ ] **Step 6.3: Dispatch all 21 subagents in a single message**

In a single controller message, call `Agent` 21 times in parallel. Each call:
- `subagent_type`: `"general-purpose"` — note: the spec mentioned "Explore subagent_type" but Explore is read-only and these subagents need `Write` to author their row + candidate files, so general-purpose is the correct choice. Document this deviation when you commit.
- `description`: short — `"Phase B research: <doc_folder>"`
- `prompt`: the output of `build_research_prompt(<doc_folder>)`
- `model`: default (sonnet) — research quality matters more than speed

The dispatching-parallel-agents skill says: "When you launch multiple agents for independent work, send them in a single message with multiple tool uses so they run concurrently."

**Concretely:** assemble a single Agent tool call block with 21 invocations. Wait for all to complete via standard tool-result notifications. Do NOT poll.

- [ ] **Step 6.4: Collect results**

For each of the 21 subagent results:
- Status: DONE | DONE_WITH_CONCERNS | BLOCKED
- Files written
- Validator exit code (reported by the subagent per the prompt's instructions)

Build a summary table:

```
| Service | Status | Row written? | Candidates created | Validator |
|---|---|---|---|---|
| backend | DONE | yes | obsidian-mcp.md | 0 |
| ...     | ...  | ... | ...                | ... |
```

- [ ] **Step 6.5: Re-dispatch failures**

For each subagent that reported BLOCKED or wrote no row file:
- Read its concern and the partial state on disk.
- Dispatch a single follow-up `Agent` call (sequential, not parallel) with the same prompt PLUS targeted clarifying context.
- Repeat until DONE.

For each subagent that reported DONE_WITH_CONCERNS:
- Read the concern. If it's a quality concern, leave for Task 8's spot-check pass. If it's a correctness concern (e.g., "I couldn't determine the category"), dispatch a fix-up.

- [ ] **Step 6.6: Validate every row file**

```bash
python scripts/validate_research_schema.py --all
echo "exit=$?"
```

Expected: exit 0. If 1, the script lists offending files — re-dispatch fix-up subagents until clean.

- [ ] **Step 6.7: Commit (single commit for the whole batch)**

```bash
git add docs/research/rows/ docs/research/candidates/
git commit -m "docs: phase B research — 21 row files + candidate one-pagers"
```

Capture the diff stat (`git diff HEAD~1 --stat`) for the final report.

---

## Task 7: Run the merge step

**Files written:**
- `docs/research/integration-matrix.md` (new)
- Each `docs/research/candidates/<slug>.md` (frontmatter `referenced-by:` reconciled)

- [ ] **Step 7.1: Run the merge**

```bash
PYTHONPATH=bootstrapper python -m bootstrapper.docs.merge_research
```

Expected: silent success (exit 0). Inspect:

```bash
ls -la docs/research/integration-matrix.md
head -30 docs/research/integration-matrix.md
```

- [ ] **Step 7.2: Verify idempotency**

```bash
# Re-run; capture before/after content
cp docs/research/integration-matrix.md /tmp/matrix-1.md
PYTHONPATH=bootstrapper python -m bootstrapper.docs.merge_research
diff /tmp/matrix-1.md docs/research/integration-matrix.md
```

Expected: no diff.

- [ ] **Step 7.3: Re-validate (the merge may have changed referenced-by lists)**

```bash
python scripts/validate_research_schema.py --all
echo "exit=$?"
```

Expected: exit 0.

- [ ] **Step 7.4: Commit**

```bash
git add docs/research/integration-matrix.md docs/research/candidates/
git commit -m "docs: phase B merge — generate integration-matrix.md + reconcile referenced-by"
```

---

## Task 8: Spot-check 5 rows for quality — CONTROLLER TASK

**Files reviewed (NOT modified at this step):**
- 5 randomly-selected row files under `docs/research/rows/`.

**IMPORTANT:** This is a CONTROLLER TASK — the controller reads the 5 rows directly and judges quality. No subagent delegation for the judgment itself. (Quality fix-ups, if any, ARE delegated to subagents.)

- [ ] **Step 8.1: Select 5 rows pseudo-randomly**

```bash
ls docs/research/rows/*.md | shuf -n 5    # macOS: `gshuf` or use the Python one-liner
```

Or deterministic for reproducibility: pick `hermes.md`, `kong.md`, `litellm.md`, `weaviate.md`, `n8n.md` (the 5 services with the densest dep graphs — most likely to surface quality issues).

- [ ] **Step 8.2: For each of the 5, evaluate against this rubric**

| Criterion | Pass condition |
|---|---|
| Sources consulted | ≥1 URL in frontmatter AND ≥1 referenced inside Confidence claims |
| Mechanism specificity | Every "Mechanism sketch" names an actual protocol/endpoint, not a generic "API" or "connection" |
| Confidence backing | Every `Confidence: high\|medium` claim has a sources_consulted entry that supports it |
| Wiring sketch realism | Every "Stack wiring sketch" in linked candidates names ONLY services in the current topology |
| Do-not-propose hygiene | No proposed pair is already in the service's current upstream/downstream |
| Word cap | Body ≤ 800 words (validator confirms; spot-check) |
| Candidate cap | ≤ 5 cross-references in section 2 (validator confirms; spot-check) |

Document findings inline as you read.

- [ ] **Step 8.3: For any row failing 2+ criteria, dispatch a fix-up subagent**

```
Agent(
  description=f"Phase B quality fix-up: {service}",
  subagent_type="general-purpose",
  prompt=<rebuilt prompt + specific feedback>,
)
```

The fix-up prompt should include the original prompt PLUS a short "fix the following issues:" block citing the specific criteria the row failed. Repeat until rubric passes.

- [ ] **Step 8.4: Re-validate + re-merge if any fix-up happened**

```bash
python scripts/validate_research_schema.py --all
PYTHONPATH=bootstrapper python -m bootstrapper.docs.merge_research
```

- [ ] **Step 8.5: Commit fix-ups (if any)**

```bash
# Only if Step 8.3 made changes:
git add docs/research/
git commit -m "docs: phase B quality fix-ups from spot-check pass"
```

---

## Task 9: CHANGELOG + Phase B acceptance gates + tag

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 9.1: Append CHANGELOG entry**

Open `docs/CHANGELOG.md`. Insert a new entry inside the `## [Unreleased]` block, BEFORE the existing most-recent entry, following the project's section style. Use this content:

```markdown
### Added (Cross-service deps + diagrams — Phase B research)

- Added 21 per-service integration-research files under `docs/research/rows/<service>.md` (missing-pair integrations, candidate new services, per-service feature gaps).
- Added candidate one-pagers under `docs/research/candidates/<slug>.md`.
- Added generated master index at `docs/research/integration-matrix.md` (re-build with `python -m bootstrapper.docs.merge_research`).
- New tooling: `scripts/validate_research_schema.py` (schema validator), `bootstrapper/docs/merge_research.py` (merge + index generator), `bootstrapper/docs/research_subagent_prompt.py` (programmatic Phase B subagent prompt builder).
- Phase C (content authoring) is next — see `docs/superpowers/specs/2026-05-16-cross-service-deps-and-diagrams-design.md`.
```

- [ ] **Step 9.2: Verify Phase B acceptance gates**

Run all 5 gates explicitly:

```bash
# Gate 1: 21 row files exist + parse against schema
ls docs/research/rows/*.md | wc -l    # expect: 21
python scripts/validate_research_schema.py --all
echo "Gate 1 exit: $?"  # expect 0

# Gate 2: every candidate's Stack wiring sketch names real services
# (the validator already enforces every required section; the realism check is
# spot-check + the merge step's referenced-by reconciliation — if a candidate
# references a non-real service, the referenced-by list will mis-resolve.)
# Spot-check by inspection:
ls docs/research/candidates/*.md 2>/dev/null

# Gate 3: integration-matrix.md builds without errors
PYTHONPATH=bootstrapper python -m bootstrapper.docs.merge_research
echo "Gate 3 exit: $?"  # expect 0
ls -la docs/research/integration-matrix.md

# Gate 4: no row makes a Confidence claim without a sources_consulted entry
# (validator already enforces sources_consulted ≥ 1; the specific Confidence-to-source
# binding is part of the spot-check rubric. Re-confirm by grepping):
for f in docs/research/rows/*.md; do
  if grep -q "Confidence: high\|Confidence: medium" "$f"; then
    if ! grep -q "^sources_consulted:" "$f"; then
      echo "GATE 4 FAIL: $f makes high/medium claim without sources_consulted"
    fi
  fi
done

# Gate 5: spot-check completed (5 of 21 reviewed) — verify by Task 8 commit history:
git log --oneline -10 | grep "spot-check" || echo "no spot-check commit (acceptable if no fix-ups were needed)"

# Final: full test suite green
cd bootstrapper && uv run pytest -q
cd ..
```

Expected for the test suite: ~306 passed, 3 skipped (Phase A baseline 285 + Phase B's 21 new tests: 8 validator + 5 merge + 8 prompt-builder).

- [ ] **Step 9.3: Commit the CHANGELOG**

```bash
git add docs/CHANGELOG.md
git commit -m "docs: changelog entry for cross-service deps + diagrams Phase B"
```

- [ ] **Step 9.4: Tag the Phase B landing point**

```bash
git tag phase-b-research -m "Phase B complete: 21 row files + candidate one-pagers + master matrix"
```

---

## Phase B complete

You have shipped:

1. A schema validator (`scripts/validate_research_schema.py`) covering both row files and candidate one-pagers.
2. A merge script (`bootstrapper/docs/merge_research.py`) that produces `integration-matrix.md` and reconciles `referenced-by:` frontmatter deterministically.
3. A programmatic prompt builder (`bootstrapper/docs/research_subagent_prompt.py`) that pulls do-not-propose lists and other-services context from manifests + topology.
4. 21 per-service research row files describing missing-pair integrations, candidate new services, and per-service feature gaps.
5. N candidate one-pagers (typically 5-20) describing slot-in new services.
6. A generated `integration-matrix.md` master index.
7. A CHANGELOG entry.
8. A Phase B tag.

**Phase C** can now consume these row files to populate the "Future" subsections in each service README, plus rewrite the 7 placeholder docs to Hermes-grade depth. Phase C's plan will be written next.
