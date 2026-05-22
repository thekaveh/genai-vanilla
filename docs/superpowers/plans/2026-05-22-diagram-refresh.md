# Architecture diagram refresh — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Phase A's manifest-derived per-service architecture diagrams with a data-flow model (new `data_flow.calls:` manifest field) and a clustered-by-category visual layout.

**Architecture:** Three coordinated changes — (1) new optional manifest field `data_flow.calls` with schema + dataclass support, (2) populate the field across 22 manifests, (3) rewrite `deps_resolver.py` to read only this field and rewrite `diagram_renderer.py` for the clustered visual layout. The `deps_section_writer.py` table columns simplify to `Service | Category`. The `regen` CLI + drift gate from Phase A keep working unchanged at their interfaces; their content changes. Hermes golden snapshots regenerate.

**Tech Stack:** Python 3.9+, `pyyaml`, `jsonschema`, pytest. No new runtime dependencies. Reuses Phase A's templates pattern (`bootstrapper/docs/templates/*.tmpl` with `string.Template`).

**Spec reference:** `docs/superpowers/specs/2026-05-22-diagram-refresh-design.md`.

**Phase A + B status:** both merged to main (tags `phase-a-deps-foundations` + `phase-b-research`). Main HEAD includes the per-service folder migration, the regen CLI, the drift gate, and the research artifacts. Build on top.

---

## File structure

**New files (created during this phase):**

```
bootstrapper/docs/templates/
├── cluster.tmpl                     # category-cluster box template (new)
└── (architecture.html.tmpl, svg_box.tmpl, svg_defs.tmpl unchanged; svg_edge.tmpl deleted long ago)
```

**Modified files:**

- `bootstrapper/schemas/service.schema.json` — add top-level optional `data_flow` block.
- `bootstrapper/services/manifests.py` — add `data_flow: dict` field to `Manifest` dataclass.
- `bootstrapper/docs/deps_resolver.py` — rewrite: drop reads of `depends_on.required` / `runtime_adaptive.adapts_to` / `runtime_deps.optional` / `doc_extras.diagram.extra_consumers`; read only `data_flow.calls`; simplify `DepEdge`.
- `bootstrapper/docs/diagram_renderer.py` — rewrite for clustered layout.
- `bootstrapper/docs/deps_section_writer.py` — simplify tables to `Service | Category` columns.
- `bootstrapper/docs/regen.py` — no behavioral change expected; verify still works.
- `bootstrapper/tests/test_manifests.py` — extend with `data_flow.calls` round-trip + invalid-service-name rejection tests.
- `bootstrapper/tests/test_deps_resolver.py` — rewrite all tests for the new model.
- `bootstrapper/tests/test_diagram_renderer.py` — rewrite all tests for clustered layout.
- `bootstrapper/tests/test_deps_section_writer.py` — update for new table shape.
- `bootstrapper/tests/fixtures/hermes.architecture.svg` — regenerate.
- `bootstrapper/tests/fixtures/hermes.deps_section.md` — regenerate.
- `services/<name>/service.yml` for **22 manifests** — add `data_flow.calls` block.
- `docs/services/<name>/README.md` × 21 — regenerated.
- `docs/services/<name>/architecture.svg` × 21 — regenerated.
- `docs/services/<name>/architecture.html` × 21 — regenerated.
- `docs/CHANGELOG.md` — entry.

**Files explicitly NOT touched:**

- `services/globals/service.yml`, `services/cloud-providers/service.yml`'s **other** fields (cloud-providers gets a `data_flow.calls: []` block; globals is virtual and gets nothing).
- The bootstrapper's compose orchestration. The bootstrap dep fields (`depends_on.required`, `runtime_adaptive.adapts_to`, `runtime_deps.optional`) STAY in manifests — they're still used by the compose layer. The diagram resolver just stops reading them.
- `scripts/check_doc_links.py`, `scripts/migrate_docs_to_folders.py`, `scripts/validate_research_schema.py` — unrelated.
- `docs/research/` — Phase B output is untouched.

---

## Pre-flight

- [ ] **Step 0a: Worktree setup**

```bash
git worktree add .claude/worktrees/diagram-refresh -b diagram-refresh
cd .claude/worktrees/diagram-refresh
pwd; git branch --show-current
```

Expected: pwd ends with `/diagram-refresh`, branch is `diagram-refresh`.

- [ ] **Step 0b: Verify Phase A + B are in place**

```bash
git tag -l 'phase-*-*'                  # expect: phase-a-deps-foundations, phase-b-research
ls docs/services/hermes/architecture.svg # expect: file exists
ls docs/research/integration-matrix.md   # expect: file exists
```

If any check fails, stop and resolve.

- [ ] **Step 0c: Baseline test run**

```bash
cd bootstrapper && uv run pytest -q
```

Expected: ~309 passed (Phase A + B baseline). Capture for end-of-plan sanity check.

---

## Task 1: Schema + dataclass — `data_flow.calls`

**Files:**
- Modify: `bootstrapper/schemas/service.schema.json`
- Modify: `bootstrapper/services/manifests.py`
- Test: `bootstrapper/tests/test_manifests.py` (extend)

**Why first:** every other module depends on this field being parseable.

- [ ] **Step 1.1: Write failing tests**

Append to `bootstrapper/tests/test_manifests.py`:

```python
def test_data_flow_calls_round_trips(tmp_path):
    """A manifest declaring data_flow.calls must parse and the values must be retrievable."""
    from services.manifests import load_manifests

    services_dir = tmp_path / "services"
    svc = services_dir / "foo"
    svc.mkdir(parents=True)
    (svc / "service.yml").write_text(
        "name: foo\n"
        "label: Foo\n"
        "category: data\n"
        "env: []\n"
        "data_flow:\n"
        "  calls:\n"
        "    - bar\n"
        "    - baz\n"
    )

    manifests = load_manifests(services_dir)
    assert len(manifests) == 1
    assert manifests[0].data_flow == {"calls": ["bar", "baz"]}


def test_data_flow_calls_optional(tmp_path):
    """A manifest without data_flow loads cleanly with empty dict."""
    from services.manifests import load_manifests

    services_dir = tmp_path / "services"
    svc = services_dir / "noflow"
    svc.mkdir(parents=True)
    (svc / "service.yml").write_text(
        "name: noflow\n"
        "label: NoFlow\n"
        "category: data\n"
        "env: []\n"
    )

    manifests = load_manifests(services_dir)
    assert manifests[0].data_flow == {}


def test_data_flow_calls_rejects_unknown_subkey(tmp_path):
    """Unknown subkeys under data_flow (e.g. data_flow.bogus) are rejected by schema."""
    from services.manifests import load_manifests, ManifestLoadError

    services_dir = tmp_path / "services"
    svc = services_dir / "bad"
    svc.mkdir(parents=True)
    (svc / "service.yml").write_text(
        "name: bad\n"
        "label: Bad\n"
        "category: data\n"
        "env: []\n"
        "data_flow:\n"
        "  bogus: [a, b]\n"
    )

    import pytest
    with pytest.raises(ManifestLoadError):
        load_manifests(services_dir)
```

- [ ] **Step 1.2: Run tests — expect failure**

```bash
cd bootstrapper && uv run pytest tests/test_manifests.py::test_data_flow_calls_round_trips tests/test_manifests.py::test_data_flow_calls_optional tests/test_manifests.py::test_data_flow_calls_rejects_unknown_subkey -v
```

Expected: FAIL — schema rejects `data_flow` OR `Manifest` dataclass has no `data_flow` field.

- [ ] **Step 1.3: Extend the schema**

In `bootstrapper/schemas/service.schema.json`, add a new top-level optional property `data_flow` (alphabetically near `depends_on:`). Find the `"properties": {` block and add this entry:

```json
"data_flow": {
  "type": "object",
  "additionalProperties": false,
  "description": "Runtime data-flow declarations consumed by the diagram resolver. Independent of depends_on (which expresses bootstrap order).",
  "properties": {
    "calls": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
      "uniqueItems": true,
      "description": "Names of services this one calls at runtime in the request path. Init-time bootstrap calls do NOT count. Names must match either a doc-folder name under docs/services/ or a manifest name under services/."
    }
  }
},
```

- [ ] **Step 1.4: Extend the `Manifest` dataclass**

Open `bootstrapper/services/manifests.py`. Locate the `Manifest` dataclass. Append a new field after `doc_extras`:

```python
    data_flow: dict = field(default_factory=dict)
```

Then locate `_to_dataclass` (or `_load_one`) and populate the field:

```python
        data_flow=dict(raw.get("data_flow") or {}),
```

- [ ] **Step 1.5: Run tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_manifests.py -v
```

Expected: 3 new tests pass, all pre-existing tests still pass.

- [ ] **Step 1.6: Full suite still green**

```bash
cd bootstrapper && uv run pytest -q
```

Expected: 312 passed (baseline 309 + 3 new).

- [ ] **Step 1.7: Commit**

```bash
git add bootstrapper/schemas/service.schema.json \
        bootstrapper/services/manifests.py \
        bootstrapper/tests/test_manifests.py
git commit -m "manifests: add optional data_flow.calls field for diagram resolver"
```

---

## Task 2: Populate `data_flow.calls` in all manifests

**Files:**
- Modify: 22 × `services/<name>/service.yml`

**Why:** the resolver in Task 3 will read this field. Without populated data, all diagrams render empty.

The values below come from the spec's authoring table, augmented with bidirectional cases (Hermes↔LiteLLM) and the Kong "proxies" convention.

For each manifest, append a `data_flow:` block (typically near the end, before `runtime_sc:` or `exports:`). If the block already exists from Task 1's testing, just edit it. Use the exact YAML below.

- [ ] **Step 2.1: Edit `services/backend/service.yml`**

Add:

```yaml
data_flow:
  calls:
    - supabase
    - redis
    - weaviate
    - neo4j
    - litellm
    - hermes
    - comfyui
    - stt-provider
    - tts-provider
    - doc-processor
    - n8n
```

- [ ] **Step 2.2: Edit `services/comfyui/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - minio
```

- [ ] **Step 2.3: Edit `services/docling/service.yml`** (underlying manifest for doc-processor aggregate)

```yaml
data_flow:
  calls: []
```

(doc-processor is called by others but doesn't call out at runtime.)

- [ ] **Step 2.4: Edit `services/hermes/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - stt-provider
    - tts-provider
    - comfyui
    - searxng
```

- [ ] **Step 2.5: Edit `services/jupyterhub/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - hermes
    - weaviate
    - neo4j
    - minio
    - supabase
```

- [ ] **Step 2.6: Edit `services/kong/service.yml`**

Add a header comment explaining the proxy-direction convention, then the calls list (all consumer-facing services Kong fronts at the gateway):

```yaml
# data_flow.calls for Kong uses the PROXY direction by convention:
# Kong doesn't initiate outbound calls itself — it forwards inbound traffic
# to these backends. Listing them here produces a diagram where Kong is
# correctly shown as the front door for everything it routes to.
data_flow:
  calls:
    - backend
    - open-webui
    - jupyterhub
    - n8n
    - hermes
    - openclaw
    - local-deep-researcher
    - minio
    - supabase
    - weaviate
    - neo4j
    - comfyui
    - searxng
    - stt-provider
    - tts-provider
    - doc-processor
    - litellm
    - ollama
```

- [ ] **Step 2.7: Edit `services/litellm/service.yml`**

```yaml
data_flow:
  calls:
    - supabase
    - redis
    - ollama
    - cloud-providers
    - hermes
```

(`cloud-providers` is a virtual manifest with `category: llm` — the resolver renders it as a category-colored box even though it has no doc folder. `hermes` listed for bidirectional collapse against hermes's own `data_flow.calls: [litellm, ...]`.)

- [ ] **Step 2.8: Edit `services/local-deep-researcher/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - searxng
```

- [ ] **Step 2.9: Edit `services/minio/service.yml`**

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.10: Edit `services/n8n/service.yml`**

```yaml
data_flow:
  calls:
    - supabase
    - weaviate
    - comfyui
    - doc-processor
    - hermes
    - litellm
    - stt-provider
    - tts-provider
    - searxng
    - minio
```

- [ ] **Step 2.11: Edit `services/neo4j/service.yml`**

```yaml
data_flow:
  calls:
    - supabase
```

- [ ] **Step 2.12: Edit `services/ollama/service.yml`**

```yaml
data_flow:
  calls:
    - supabase
    - litellm
```

(ollama-pull also reads from supabase's `public.llms`; init-only call to litellm for model registration is bootstrap — but Phase B research showed there's also a runtime tagging callback. List `litellm` for honest data flow.)

- [ ] **Step 2.13: Edit `services/open-webui/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - hermes
    - doc-processor
    - searxng
```

- [ ] **Step 2.14: Edit `services/openclaw/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - hermes
    - n8n
```

- [ ] **Step 2.15: Edit `services/redis/service.yml`**

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.16: Edit `services/searxng/service.yml`**

```yaml
data_flow:
  calls: []
```

(searxng makes outbound calls to external search engines — none of which are in-stack.)

- [ ] **Step 2.17: Edit `services/supabase/service.yml`**

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.18: Edit `services/weaviate/service.yml`**

```yaml
data_flow:
  calls:
    - litellm
    - multi2vec-clip
```

- [ ] **Step 2.19: Edit `services/parakeet/service.yml`** (underlying manifest for stt-provider aggregate)

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.20: Edit `services/speaches/service.yml`** (underlying manifest for stt-provider + tts-provider aggregates)

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.21: Edit `services/chatterbox/service.yml`** (underlying manifest for tts-provider aggregate)

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.22: Edit `services/tts-provider/service.yml`** (underlying manifest for tts-provider aggregate)

```yaml
data_flow:
  calls: []
```

- [ ] **Step 2.23: Edit `services/cloud-providers/service.yml`**

```yaml
data_flow:
  calls: []
```

(virtual manifest, no runtime calls — but explicit empty list makes the field's presence consistent.)

- [ ] **Step 2.24: Verify schema validation across all manifests**

```bash
cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -q
```

Expected: all pass. If any manifest fails schema validation, fix the offending file.

- [ ] **Step 2.25: Spot-check a few values via the loader**

```bash
PYTHONPATH=bootstrapper python -c "
from services.manifests import load_manifests
from pathlib import Path
m = {x.name: x for x in load_manifests(Path('services'))}
for name in ['litellm', 'hermes', 'kong', 'minio']:
    print(f'{name}: data_flow.calls = {m[name].data_flow.get(\"calls\", [])}')"
```

Expected: prints the lists from steps 2.7, 2.4, 2.6, 2.9.

- [ ] **Step 2.26: Commit**

```bash
git add services/*/service.yml
git commit -m "manifests: populate data_flow.calls across 22 services"
```

---

## Task 3: Rewrite `deps_resolver.py` for data-flow model

**Files:**
- Modify: `bootstrapper/docs/deps_resolver.py`
- Rewrite: `bootstrapper/tests/test_deps_resolver.py`

**Why:** the resolver must read `data_flow.calls` and produce the new (simpler) `DepGraph`. Old logic that reads `depends_on.required` / `runtime_adaptive.adapts_to` / `runtime_deps.optional` / `doc_extras.diagram.extra_consumers` is dropped from the resolver entirely (those fields stay in manifests for compose orchestration).

- [ ] **Step 3.1: Replace the test file**

Overwrite `bootstrapper/tests/test_deps_resolver.py` with:

```python
"""Tests for bootstrapper.docs.deps_resolver — data-flow model."""

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


def test_upstream_comes_from_data_flow_calls():
    """build_graph reads focus.data_flow.calls and renders it as the upstream lane."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    upstream_others = {e.other for e in g.upstream}
    # Hermes calls litellm, stt-provider, tts-provider, comfyui, searxng (per data_flow.calls)
    assert upstream_others >= {"litellm", "comfyui", "searxng"}


def test_downstream_comes_from_inverse_data_flow_calls():
    """A service appears downstream of focus if any other manifest's
    data_flow.calls includes focus."""
    from docs.deps_resolver import build_graph
    g = build_graph("litellm", SERVICES_DIR)
    downstream_others = {e.other for e in g.downstream}
    # backend, n8n, hermes, weaviate, jupyterhub, etc. all call litellm
    assert downstream_others >= {"backend", "n8n", "weaviate", "jupyterhub", "open-webui"}


def test_bidirectional_collapse_hermes_litellm():
    """litellm.data_flow.calls includes hermes; hermes.data_flow.calls includes litellm.
    Both edges must be marked bidirectional."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    litellm_edges = [e for e in g.upstream if e.other == "litellm"]
    assert litellm_edges, "expected litellm in hermes upstream"
    assert litellm_edges[0].bidirectional


def test_dep_edge_has_no_kind_field():
    """The simpler DepEdge no longer carries kind/mechanism/failure_mode."""
    from docs.deps_resolver import DepEdge
    fields = set(DepEdge.__dataclass_fields__.keys())
    assert "kind" not in fields
    assert "mechanism" not in fields
    assert "failure_mode" not in fields


def test_dep_graph_byte_deterministic():
    from docs.deps_resolver import build_graph
    g1 = build_graph("hermes", SERVICES_DIR)
    g2 = build_graph("hermes", SERVICES_DIR)
    assert g1 == g2


def test_empty_data_flow_calls_means_empty_upstream():
    """minio has data_flow.calls: [] — so minio's upstream is empty."""
    from docs.deps_resolver import build_graph
    g = build_graph("minio", SERVICES_DIR)
    assert g.upstream == ()


def test_kong_fronted_services_in_upstream():
    """Kong's data_flow.calls lists services it fronts. Applying the
    universal convention 'focus.data_flow.calls = upstream lane' consistently,
    these services appear in Kong's UPSTREAM lane (Kong calls/routes to them).
    Kong's downstream lane will be empty (no in-network service calls Kong)."""
    from docs.deps_resolver import build_graph
    g = build_graph("kong", SERVICES_DIR)
    assert len(g.upstream) > 10
    # Downstream is empty in the strict data-flow sense
    assert g.downstream == ()


def test_aggregate_doc_folder_unions_underlying_manifests():
    """build_doc_graph('stt-provider') unions parakeet + speaches data_flow.calls."""
    from docs.deps_resolver import build_doc_graph
    g = build_doc_graph("stt-provider", SERVICES_DIR)
    # parakeet + speaches data_flow.calls: [] each; so stt-provider upstream is empty
    assert g.upstream == ()
    # but stt-provider IS called by hermes, n8n, backend, etc. — those should be downstream
    downstream_others = {e.other for e in g.downstream}
    assert "hermes" in downstream_others


def test_doc_folder_to_manifests_mapping_unchanged():
    """A.7 mapping table is unchanged."""
    from docs.deps_resolver import doc_folder_to_manifests
    assert doc_folder_to_manifests("hermes") == ("hermes",)
    assert set(doc_folder_to_manifests("stt-provider")) >= {"parakeet", "speaches"}
    assert doc_folder_to_manifests("multi2vec-clip") == ()


def test_cloud_providers_renders_as_edge_target():
    """litellm.data_flow.calls includes cloud-providers (a virtual manifest, not a doc folder).
    The resolver must still produce a DepEdge for it."""
    from docs.deps_resolver import build_graph
    g = build_graph("litellm", SERVICES_DIR)
    upstream_others = {e.other for e in g.upstream}
    assert "cloud-providers" in upstream_others
    # And it should be category-tagged (llm)
    cp_edge = next(e for e in g.upstream if e.other == "cloud-providers")
    assert cp_edge.other_category == "llm"
```

- [ ] **Step 3.2: Run tests — expect failure**

```bash
cd bootstrapper && uv run pytest tests/test_deps_resolver.py -v
```

Expected: FAIL (DepEdge still has `kind`/`mechanism`/`failure_mode`; resolver reads old fields).

- [ ] **Step 3.3: Rewrite `bootstrapper/docs/deps_resolver.py`**

Replace the entire file with:

```python
"""Manifest-graph resolver — data-flow model.

For a given focus doc-folder, walks every manifest under services/ and builds
a DepGraph whose edges come exclusively from `data_flow.calls`. The legacy
fields (depends_on.required, runtime_adaptive.adapts_to, runtime_deps.optional,
doc_extras.diagram.extra_consumers) are NOT read here — they remain in
manifests for compose orchestration but are invisible to the diagram.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.manifests import Manifest, load_manifests  # noqa: E402


EdgeDirection = Literal["upstream", "downstream"]


@dataclass(frozen=True, order=True)
class DepEdge:
    """One edge in the data-flow graph.

    Simpler than Phase A's DepEdge — no kind/mechanism/failure_mode, because
    we now have a single edge type ("calls"). `other_category` carries the
    target's category so the renderer can colour-code without re-loading.
    """

    other: str
    direction: EdgeDirection
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


# Category ordering matches services.topology.CATEGORY_ORDER.
_CATEGORY_RANK = {
    "infra": 0, "data": 1, "llm": 2, "media": 3, "agents": 4, "apps": 5,
    "external": 6,
}


def _edge_sort_key(e: DepEdge) -> tuple[int, str]:
    """Stable sort: by category-rank, then alphabetically."""
    return (_CATEGORY_RANK.get(e.other_category, 99), e.other)


def _category_of(name: str, all_m: dict[str, Manifest]) -> str:
    if name in all_m:
        return all_m[name].category
    return "external"


def _calls_of(m: Manifest) -> list[str]:
    """Read m's data_flow.calls. Returns empty list if absent."""
    df = m.data_flow or {}
    return list(df.get("calls") or [])


# ─────────────────────────────────────────────────────────────────────────
# Doc-folder ↔ manifest mapping (spec A.7, unchanged)
# ─────────────────────────────────────────────────────────────────────────

_AGGREGATE_DOC_FOLDERS: dict[str, tuple[str, ...]] = {
    "stt-provider":   ("parakeet", "speaches"),
    "tts-provider":   ("chatterbox", "speaches", "tts-provider"),
    "doc-processor":  ("docling",),
    "multi2vec-clip": (),
}


def doc_folder_to_manifests(doc_folder: str) -> tuple[str, ...]:
    if doc_folder in _AGGREGATE_DOC_FOLDERS:
        return _AGGREGATE_DOC_FOLDERS[doc_folder]
    return (doc_folder,)


# A reverse map: which doc-folder a manifest belongs to (for inverse-pass
# edge naming). E.g. parakeet → stt-provider.
def _manifest_to_doc_folder(name: str) -> str:
    for folder, members in _AGGREGATE_DOC_FOLDERS.items():
        if name in members:
            return folder
    return name


# ─────────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────────


def build_graph(focus: str, services_root: Path) -> DepGraph:
    """Build the DepGraph for a single manifest-name focus."""
    manifests_by_name = {m.name: m for m in load_manifests(services_root)}
    if focus not in manifests_by_name:
        raise KeyError(f"no manifest for service '{focus}' under {services_root}")
    return _build_for_manifests(focus, [manifests_by_name[focus]], manifests_by_name)


def build_doc_graph(doc_folder: str, services_root: Path) -> DepGraph:
    """Build the DepGraph for a doc folder. Folds aggregate manifests."""
    manifest_names = doc_folder_to_manifests(doc_folder)
    manifests_by_name = {m.name: m for m in load_manifests(services_root)}

    if not manifest_names:
        # Pointer-only doc (e.g., multi2vec-clip)
        return DepGraph(
            focus=doc_folder,
            category="data",
            port_var=None,
            source="(pointer doc — see weaviate)",
        )

    members = [manifests_by_name[n] for n in manifest_names if n in manifests_by_name]
    if len(members) == 1 and members[0].name == doc_folder:
        return _build_for_manifests(doc_folder, members, manifests_by_name)
    # Aggregate
    return _build_for_manifests(doc_folder, members, manifests_by_name, aggregate=True)


def _build_for_manifests(
    focus: str,
    members: list[Manifest],
    all_m: dict[str, Manifest],
    *,
    aggregate: bool = False,
) -> DepGraph:
    """Common builder. `members` is one manifest for singletons, multiple for
    aggregates. Edges are derived from members' data_flow.calls (upstream)
    and from any other manifest whose data_flow.calls names the focus or any
    member (downstream)."""

    member_names = {m.name for m in members}

    # Upstream — union of each member's data_flow.calls, with intra-aggregate
    # edges suppressed. Targets are resolved to their doc-folder name where
    # possible (so a member calling 'speaches' renders as 'stt-provider' or
    # 'tts-provider' depending on context — but since 'speaches' the manifest
    # is itself the underlying for both aggregates, we keep the raw name).
    upstream: dict[str, DepEdge] = {}
    for m in members:
        for target in _calls_of(m):
            if target in member_names:
                continue  # intra-aggregate edge
            # Resolve target name: prefer the doc-folder name if it's an
            # aggregate (e.g. someone calling 'stt-provider' is calling the
            # logical service, not an underlying manifest).
            resolved = target
            if resolved not in upstream:
                upstream[resolved] = DepEdge(
                    other=resolved,
                    direction="upstream",
                    other_category=_resolve_category(resolved, all_m),
                )

    # Downstream — every other manifest whose data_flow.calls names focus,
    # any member, or the doc folder containing the focus.
    downstream_keys: set[str] = {focus, *member_names}
    downstream: dict[str, DepEdge] = {}
    for other_name, other_m in all_m.items():
        if other_name in member_names:
            continue
        for target in _calls_of(other_m):
            if target in downstream_keys:
                # Render the consumer under its doc-folder name where applicable
                rendered = _manifest_to_doc_folder(other_name)
                if rendered == focus or rendered in member_names:
                    continue  # don't draw a self-loop via doc-folder collapse
                if rendered not in downstream:
                    downstream[rendered] = DepEdge(
                        other=rendered,
                        direction="downstream",
                        other_category=_resolve_category(rendered, all_m),
                    )
                break  # one inbound edge per consumer

    # Bidirectional collapse: same name in both directions.
    both = set(upstream) & set(downstream)
    for name in both:
        u = upstream[name]
        d = downstream[name]
        upstream[name] = DepEdge(**{**u.__dict__, "bidirectional": True})
        downstream[name] = DepEdge(**{**d.__dict__, "bidirectional": True})

    # Focus metadata (use first member as canonical, or aggregate's defaults)
    if aggregate:
        category = members[0].category
        source = "(aggregate)"
        port_var = None
    else:
        me = members[0]
        category = me.category
        source = me.sources.default if me.sources else "single"
        port_var = next(
            (env.name for env in me.env
             if env.name.endswith("_PORT") or env.name.endswith("_API_PORT")),
            None,
        )

    init_containers = tuple(sorted({c for m in members for c in m.containers if c.endswith("-init")}))

    return DepGraph(
        focus=focus,
        category=category,
        port_var=port_var,
        source=source,
        upstream=tuple(sorted(upstream.values(), key=_edge_sort_key)),
        downstream=tuple(sorted(downstream.values(), key=_edge_sort_key)),
        init_containers=init_containers,
    )


def _resolve_category(name: str, all_m: dict[str, Manifest]) -> str:
    """Lookup category for a target name. Handles three cases:
       - Doc-folder name that's also a manifest name (1:1): use that manifest.
       - Aggregate doc-folder name: use the first underlying manifest's category.
       - Pure manifest name (e.g. underlying manifest for an aggregate, or
         a virtual manifest like cloud-providers): look up directly.
    """
    if name in _AGGREGATE_DOC_FOLDERS:
        members = _AGGREGATE_DOC_FOLDERS[name]
        if members and members[0] in all_m:
            return all_m[members[0]].category
        return "data"  # fallback for pointer-only docs
    if name in all_m:
        return all_m[name].category
    return "external"
```

- [ ] **Step 3.4: Run tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_deps_resolver.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 3.5: Full suite — note expected failures elsewhere**

```bash
cd bootstrapper && uv run pytest -q
```

Expected: `test_deps_resolver.py` passes (11). BUT:
- `test_diagram_renderer.py` — many failures (renderer reads `kind` from DepEdge which no longer exists).
- `test_deps_section_writer.py` — failures (writer references `kind`/`mechanism`/`failure_mode`).
- `test_docs_drift.py` — failure (regen --check sees drift everywhere).

These are intentional and will be fixed in Tasks 4-6. Capture the test count so you can confirm the right tests are failing.

- [ ] **Step 3.6: Commit (with failing tests — they'll pass after later tasks)**

```bash
git add bootstrapper/docs/deps_resolver.py bootstrapper/tests/test_deps_resolver.py
git commit -m "docs: rewrite deps_resolver for data-flow model (drops bootstrap-dep edges)"
```

---

## Task 4: Rewrite `diagram_renderer.py` for clustered layout

**Files:**
- Modify: `bootstrapper/docs/diagram_renderer.py`
- Create: `bootstrapper/docs/templates/cluster.tmpl`
- Rewrite: `bootstrapper/tests/test_diagram_renderer.py`
- Regenerate: `bootstrapper/tests/fixtures/hermes.architecture.svg`

**Why:** the renderer must produce the clustered-by-category layout from the spec's polished mockup.

- [ ] **Step 4.1: Create the cluster template**

Create `bootstrapper/docs/templates/cluster.tmpl`:

```svg
<g class="cluster">
  <rect x="$x" y="$y" width="$w" height="$h" rx="8"
        fill="rgba(30,41,59,0.35)"
        stroke="$stroke" stroke-width="1" stroke-dasharray="4,4" stroke-opacity="0.4"/>
  <text x="$header_x" y="$header_y" fill="$stroke" font-size="9" font-weight="700"
        text-anchor="start" style="letter-spacing:0.06em;text-transform:uppercase;">$category</text>
  <text x="$count_x" y="$header_y" fill="$stroke" font-size="9" font-weight="600"
        text-anchor="end">$count</text>
</g>
```

- [ ] **Step 4.2: Rewrite the test file**

Overwrite `bootstrapper/tests/test_diagram_renderer.py`:

```python
"""Tests for bootstrapper.docs.diagram_renderer — clustered layout."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
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
    assert "HERMES" in svg


def test_renders_html_includes_jetbrains_mono():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_html
    g = build_doc_graph("hermes", SERVICES_DIR)
    html = render_html(g)
    assert "JetBrains+Mono" in html
    assert "<svg" in html


def test_svg_byte_deterministic():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    a = render_svg(g)
    b = render_svg(g)
    assert a == b


def test_svg_is_well_formed_xml_across_services():
    """Every doc folder's SVG parses as well-formed XML."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    for svc in ("hermes", "kong", "litellm", "redis", "stt-provider",
                "tts-provider", "ollama", "weaviate", "minio", "supabase"):
        svg = render_svg(build_doc_graph(svc, SERVICES_DIR))
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise AssertionError(f"{svc}: malformed SVG — {exc}") from None


def test_focus_box_has_glow_filter():
    """The focus box uses a glow effect (filter or shadow)."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    # Glow implemented as either an SVG filter or a stroke-on-stroke effect
    assert "feGaussianBlur" in svg or "stdDeviation" in svg or "drop-shadow" in svg.lower()


def test_clusters_grouped_by_category():
    """Hermes upstream has services in 'llm' + 'media' categories — both
    categories should appear as cluster headers in the SVG."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    # Cluster headers carry the category name in the SVG text
    assert "LLM" in svg or "llm" in svg
    assert "MEDIA" in svg or "media" in svg


def test_no_required_sublabel():
    """Pills no longer carry the old 'required' sublabel."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    # Only the lane headers carry uppercase words; check 'required' (lowercase
    # near a pill) is absent
    assert "required" not in svg.lower() or svg.lower().count("required") == 0


def test_empty_lane_placeholder():
    """A focus with no upstream renders the lane with an empty placeholder."""
    from docs.deps_resolver import DepGraph
    from docs.diagram_renderer import render_svg
    g = DepGraph(focus="lonely", category="infra", port_var=None, source="single")
    svg = render_svg(g)
    assert "none" in svg.lower()


def test_one_edge_per_cluster_not_per_pill():
    """For kong (15+ downstream), edge count is bounded by cluster count (≤6),
    not by individual pill count."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("kong", SERVICES_DIR)
    svg = render_svg(g)
    line_count = svg.count("<line")
    # kong has 18 downstream services but ≤6 categories
    assert line_count <= 12  # 6 upstream lanes max + 6 downstream lanes max


def test_bidirectional_annotation():
    """Bidirectional edges (Hermes↔LiteLLM) get a bidirectional marker, not a
    duplicated arrow."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    # The text "↔" or "bidirectional" appears in the SVG when a litellm edge
    # is bidirectional
    assert "↔" in svg or "bidirectional" in svg.lower()


def test_summary_cards_in_html():
    """The HTML wrapper includes three summary cards."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_html
    g = build_doc_graph("hermes", SERVICES_DIR)
    html = render_html(g)
    # Three cards: Calls, Consumers, Categories
    assert "Calls" in html
    assert "Consumers" in html
    assert "Categories" in html


def test_svg_matches_golden_snapshot():
    """Hermes is the snapshot — must match committed fixture."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("hermes", SERVICES_DIR)
    rendered = render_svg(g)
    golden = (FIXTURE_DIR / "hermes.architecture.svg").read_text()
    assert rendered == golden, (
        "Hermes SVG drift. To accept new output:\n"
        "  PYTHONPATH=bootstrapper python -c \"from docs.deps_resolver import build_doc_graph; "
        "from docs.diagram_renderer import render_svg; from pathlib import Path; "
        "Path('bootstrapper/tests/fixtures/hermes.architecture.svg').write_text("
        "render_svg(build_doc_graph('hermes', Path('services'))))\"\n"
    )
```

- [ ] **Step 4.3: Run tests — expect failure**

```bash
cd bootstrapper && uv run pytest tests/test_diagram_renderer.py -v
```

Expected: FAIL — renderer is still the old version.

- [ ] **Step 4.4: Rewrite `bootstrapper/docs/diagram_renderer.py`**

Replace the entire file with:

```python
"""DepGraph → HTML+SVG renderer — clustered-by-category layout.

Visual design (see spec docs/superpowers/specs/2026-05-22-diagram-refresh-design.md):
- 3-lane layout: upstream | focus | downstream.
- Each non-focus lane groups services into category clusters.
- One edge per cluster (not per pill).
- Focus box has a glow (filter blur + stroke).
- Empty lanes show an italic "— none —" placeholder.
- Legend bar + 3 summary cards below the diagram.

Output is byte-deterministic for the same DepGraph.
"""

from __future__ import annotations

import html as html_mod
import sys
from collections import OrderedDict
from pathlib import Path
from string import Template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.topology import CATEGORY_COLORS  # noqa: E402

from .deps_resolver import DepEdge, DepGraph  # noqa: E402

TEMPLATE_DIR = Path(__file__).parent / "templates"

# ───── Geometry ──────────────────────────────────────────────────────────
LANE_W = 240
LANE_GAP = 60
FOCUS_W = 200
FOCUS_H = 70
PILL_H = 22
PILL_GAP = 4
CLUSTER_PADDING_Y = 8
CLUSTER_HEADER_H = 16
CLUSTER_GAP = 10
LANE_HEADER_Y = 36
LANE_TOP_Y = 64
LEGEND_H = 28
CARDS_H = 56
WIDTH = LANE_W + LANE_GAP + FOCUS_W + LANE_GAP + LANE_W + 120  # 880

CATEGORY_ORDER = ("infra", "data", "llm", "media", "agents", "apps", "external")


def render_svg(graph: DepGraph) -> str:
    """Render the architecture SVG. Pure function of graph state."""
    up_clusters = _cluster_by_category(graph.upstream)
    down_clusters = _cluster_by_category(graph.downstream)

    up_height = _clusters_height(up_clusters)
    down_height = _clusters_height(down_clusters)
    body_height = max(up_height, down_height, FOCUS_H + 40)
    total_height = LANE_TOP_Y + body_height + LEGEND_H + 20

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {total_height}">')
    parts.append(_defs(graph))
    parts.append(f'<rect width="{WIDTH}" height="{total_height}" fill="url(#grid)"/>')

    # Lane headers
    parts.append(_text(60 + LANE_W // 2, LANE_HEADER_Y, "Upstream (calls)",
                       size=10, color="#94a3b8", anchor="middle", weight=600, letter_spacing=0.08))
    focus_x = 60 + LANE_W + LANE_GAP
    parts.append(_text(focus_x + FOCUS_W // 2, LANE_HEADER_Y, "Focus",
                       size=10, color="#94a3b8", anchor="middle", weight=600, letter_spacing=0.08))
    down_x = focus_x + FOCUS_W + LANE_GAP
    parts.append(_text(down_x + LANE_W // 2, LANE_HEADER_Y, "Downstream (consumers)",
                       size=10, color="#94a3b8", anchor="middle", weight=600, letter_spacing=0.08))

    # Edges drawn first (behind clusters)
    parts.extend(_edges(graph, up_clusters, down_clusters, body_height))

    # Clusters
    parts.append(_render_lane(60, LANE_TOP_Y, LANE_W, up_clusters, "upstream"))
    parts.append(_render_lane(down_x, LANE_TOP_Y, LANE_W, down_clusters, "downstream"))

    # Focus box (centered vertically in body)
    focus_y = LANE_TOP_Y + (body_height - FOCUS_H) // 2
    parts.append(_focus_box(focus_x, focus_y, FOCUS_W, FOCUS_H, graph))

    # Legend
    legend_y = LANE_TOP_Y + body_height + 10
    parts.append(_legend(WIDTH // 2, legend_y))

    parts.append("</svg>")
    return "\n".join(parts)


def render_html(graph: DepGraph) -> str:
    tmpl = Template((TEMPLATE_DIR / "architecture.html.tmpl").read_text())
    svg = render_svg(graph)
    cat_color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    n_calls = len(graph.upstream)
    n_consumers = len(graph.downstream)
    n_categories = len({e.other_category for e in graph.downstream})
    return tmpl.substitute(
        focus=graph.focus,
        subtitle=f"category: {graph.category} · source: {graph.source}",
        cat_color=cat_color,
        svg=svg,
        n_required=n_calls,         # "Calls" — template still uses these var names
        n_optional=n_consumers,     # "Consumers"
        n_consumers=n_categories,   # "Categories served"
        footer=f"Regenerate: python -m bootstrapper.docs.regen {graph.focus}",
    )


# ───── Internal helpers ──────────────────────────────────────────────────


def _cluster_by_category(edges: tuple[DepEdge, ...]) -> "OrderedDict[str, list[DepEdge]]":
    """Group edges by other_category. Preserves CATEGORY_ORDER ordering.
    Returns empty OrderedDict if edges is empty."""
    grouped: dict[str, list[DepEdge]] = {}
    for e in edges:
        grouped.setdefault(e.other_category, []).append(e)
    return OrderedDict(
        (cat, sorted(grouped[cat], key=lambda x: x.other))
        for cat in CATEGORY_ORDER
        if cat in grouped
    )


def _cluster_height(pills: list[DepEdge]) -> int:
    """Height of a cluster containing N pills (in 2-column packed grid)."""
    rows = (len(pills) + 1) // 2 if len(pills) > 1 else 1
    return CLUSTER_PADDING_Y + CLUSTER_HEADER_H + rows * (PILL_H + PILL_GAP) + CLUSTER_PADDING_Y


def _clusters_height(clusters: "OrderedDict[str, list[DepEdge]]") -> int:
    if not clusters:
        return 80  # empty-placeholder height
    return sum(_cluster_height(pills) for pills in clusters.values()) + (len(clusters) - 1) * CLUSTER_GAP


def _defs(graph: DepGraph) -> str:
    focus_color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    return f"""<defs>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.5"/>
  </pattern>
  <marker id="arrowhead" markerWidth="9" markerHeight="6" refX="8" refY="3" orient="auto">
    <polygon points="0 0, 9 3, 0 6" fill="#64748b"/>
  </marker>
  <filter id="focus-glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="6"/>
    <feFlood flood-color="{focus_color}" flood-opacity="0.6"/>
    <feComposite in2="SourceAlpha" operator="in"/>
    <feMerge>
      <feMergeNode/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>"""


def _focus_box(x: int, y: int, w: int, h: int, graph: DepGraph) -> str:
    color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    cx = x + w // 2
    return (
        f'<g class="focus" filter="url(#focus-glow)">'
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
        f'        fill="#0f172a" stroke="{color}" stroke-width="1.5"/>'
        f'  <text x="{cx}" y="{y + 28}" fill="white" font-size="15" font-weight="700" '
        f'        text-anchor="middle">{html_mod.escape(graph.focus.upper())}</text>'
        f'  <text x="{cx}" y="{y + 48}" fill="#94a3b8" font-size="10" '
        f'        text-anchor="middle">{html_mod.escape(graph.category)} · {html_mod.escape(graph.source)}</text>'
        f'</g>'
    )


def _render_lane(x: int, y: int, w: int, clusters: "OrderedDict[str, list[DepEdge]]", direction: str) -> str:
    if not clusters:
        # Empty placeholder
        return (
            f'<g><rect x="{x}" y="{y + 20}" width="{w}" height="60" rx="6" '
            f'fill="none" stroke="#1e293b" stroke-width="1" stroke-dasharray="3,3"/>'
            f'<text x="{x + w // 2}" y="{y + 56}" fill="#475569" font-size="10" '
            f'font-style="italic" text-anchor="middle">— none —</text></g>'
        )

    parts: list[str] = ['<g>']
    cy = y
    cluster_tmpl = Template((TEMPLATE_DIR / "cluster.tmpl").read_text())
    for cat, pills in clusters.items():
        ch = _cluster_height(pills)
        color = CATEGORY_COLORS.get(cat, "#94a3b8")
        parts.append(cluster_tmpl.substitute(
            x=x, y=cy, w=w, h=ch,
            stroke=color,
            header_x=x + 10, header_y=cy + 14,
            count_x=x + w - 10,
            category=html_mod.escape(cat),
            count=str(len(pills)),
        ))
        # Pills inside the cluster
        pill_top = cy + CLUSTER_PADDING_Y + CLUSTER_HEADER_H
        pill_w = (w - 24) // 2
        for i, p in enumerate(pills):
            row = i // 2
            col = i % 2
            px = x + 8 + col * (pill_w + 4)
            py = pill_top + row * (PILL_H + PILL_GAP)
            parts.append(_pill(px, py, pill_w, PILL_H, p.other, color))
        cy += ch + CLUSTER_GAP

    parts.append('</g>')
    return "\n".join(parts)


def _pill(x: int, y: int, w: int, h: int, label: str, stroke: str) -> str:
    return (
        f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
        f'fill="rgba(15,23,42,0.7)" stroke="{stroke}" stroke-width="1"/>'
        f'<text x="{x + w // 2}" y="{y + h // 2 + 4}" fill="white" font-size="10" '
        f'text-anchor="middle">{html_mod.escape(label)}</text></g>'
    )


def _edges(graph: DepGraph, up_clusters: "OrderedDict[str, list[DepEdge]]",
          down_clusters: "OrderedDict[str, list[DepEdge]]", body_height: int) -> list[str]:
    """One edge per cluster. Edge connects focus side to cluster header."""
    parts: list[str] = []
    focus_x = 60 + LANE_W + LANE_GAP
    focus_y_center = LANE_TOP_Y + body_height // 2

    # Upstream: cluster → focus (arrow points right)
    cy = LANE_TOP_Y
    for cat, pills in up_clusters.items():
        ch = _cluster_height(pills)
        bidirectional = any(p.bidirectional for p in pills)
        x1 = 60 + LANE_W
        y1 = cy + CLUSTER_PADDING_Y + CLUSTER_HEADER_H // 2
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{focus_x}" y2="{focus_y_center}" '
            f'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        )
        if bidirectional:
            parts.append(
                f'<line x1="{focus_x}" y1="{focus_y_center + 6}" x2="{x1}" y2="{y1 + 6}" '
                f'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
            )
            parts.append(
                f'<text x="{(x1 + focus_x) // 2}" y="{(y1 + focus_y_center) // 2 - 4}" '
                f'fill="#94a3b8" font-size="9" text-anchor="middle">↔ bidirectional</text>'
            )
        cy += ch + CLUSTER_GAP

    # Downstream: focus → cluster (arrow points right)
    down_x = focus_x + FOCUS_W + LANE_GAP
    cy = LANE_TOP_Y
    for cat, pills in down_clusters.items():
        ch = _cluster_height(pills)
        x2 = down_x
        y2 = cy + CLUSTER_PADDING_Y + CLUSTER_HEADER_H // 2
        parts.append(
            f'<line x1="{focus_x + FOCUS_W}" y1="{focus_y_center}" x2="{x2}" y2="{y2}" '
            f'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        )
        cy += ch + CLUSTER_GAP

    return parts


def _legend(cx: int, y: int) -> str:
    items = [
        ("#f7768e", "infra"),
        ("#7dcfff", "data"),
        ("#e0af68", "llm"),
        ("#7aa2f7", "media"),
        ("#9ece6a", "agents"),
        ("#bb9af7", "apps"),
    ]
    item_w = 80
    total_w = item_w * len(items)
    start_x = cx - total_w // 2
    parts = [f'<g class="legend"><line x1="{start_x - 60}" y1="{y - 4}" x2="{cx + total_w // 2 + 60}" y2="{y - 4}" stroke="#1e293b" stroke-width="1"/>']
    for i, (color, name) in enumerate(items):
        ix = start_x + i * item_w
        parts.append(f'<circle cx="{ix + 6}" cy="{y + 8}" r="4" fill="{color}"/>')
        parts.append(_text(ix + 16, y + 11, name, size=9, color="#94a3b8", anchor="start"))
    parts.append('</g>')
    return "\n".join(parts)


def _text(x: int, y: int, text: str, *,
          size: int = 11, weight: int = 400, color: str = "#fff",
          anchor: str = "start", letter_spacing: float = 0.0) -> str:
    ls = f' letter-spacing="{letter_spacing}em"' if letter_spacing else ""
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{ls}>'
        f'{html_mod.escape(text)}</text>'
    )
```

- [ ] **Step 4.4b: Update `architecture.html.tmpl` summary-card labels**

Open `bootstrapper/docs/templates/architecture.html.tmpl`. The summary cards section currently reads:

```html
<div class="card"><h3>Required deps</h3><div class="num">$n_required</div></div>
<div class="card"><h3>Optional/adaptive deps</h3><div class="num">$n_optional</div></div>
<div class="card"><h3>Consumers</h3><div class="num">$n_consumers</div></div>
```

Replace those three lines with new labels aligned to the data-flow model (we keep the variable names for backwards-compat with the renderer's substitute call):

```html
<div class="card"><h3>Calls</h3><div class="num">$n_required</div></div>
<div class="card"><h3>Consumers</h3><div class="num">$n_optional</div></div>
<div class="card"><h3>Categories</h3><div class="num">$n_consumers</div></div>
```

(Variable names `$n_required` / `$n_optional` / `$n_consumers` are now reused with the new meanings per the renderer's `render_html` substitute call. A comment in `diagram_renderer.py` documents this mapping.)

- [ ] **Step 4.5: Generate the golden SVG fixture**

```bash
PYTHONPATH=bootstrapper python -c "
from docs.deps_resolver import build_doc_graph
from docs.diagram_renderer import render_svg
from pathlib import Path
Path('bootstrapper/tests/fixtures/hermes.architecture.svg').write_text(
    render_svg(build_doc_graph('hermes', Path('services'))))
print('regenerated:', Path('bootstrapper/tests/fixtures/hermes.architecture.svg').stat().st_size, 'bytes')
"
```

Expected: prints `regenerated: <size>` (typically 4-8 KB).

- [ ] **Step 4.6: Open the golden in a browser**

```bash
PYTHONPATH=bootstrapper python -c "
from docs.deps_resolver import build_doc_graph
from docs.diagram_renderer import render_html
from pathlib import Path
Path('/tmp/hermes-preview.html').write_text(render_html(build_doc_graph('hermes', Path('services'))))"
open /tmp/hermes-preview.html
```

Visually verify:
- Focus box "HERMES" centered with glow.
- Upstream lane: 2 clusters (llm: litellm + bidirectional marker; media: comfyui, searxng, stt-provider, tts-provider).
- Downstream lane: clusters for any service calling Hermes.
- Edges connect cluster headers, not pills.
- Legend bar below.

- [ ] **Step 4.7: Run tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_diagram_renderer.py -v
```

Expected: 12 passing.

- [ ] **Step 4.8: Commit**

```bash
git add bootstrapper/docs/diagram_renderer.py \
        bootstrapper/docs/templates/cluster.tmpl \
        bootstrapper/docs/templates/architecture.html.tmpl \
        bootstrapper/tests/test_diagram_renderer.py \
        bootstrapper/tests/fixtures/hermes.architecture.svg
git commit -m "docs: rewrite diagram renderer for clustered-by-category layout"
```

---

## Task 5: Update `deps_section_writer.py` for simplified tables

**Files:**
- Modify: `bootstrapper/docs/deps_section_writer.py`
- Update: `bootstrapper/tests/test_deps_section_writer.py`
- Regenerate: `bootstrapper/tests/fixtures/hermes.deps_section.md`

**Why:** the section's Upstream/Downstream tables previously had `Type | Mechanism | Failure mode` columns. With the data-flow model these columns no longer have data. New shape: `Service | Category`.

- [ ] **Step 5.1: Rewrite `bootstrapper/docs/deps_section_writer.py`**

Replace the entire file with:

```python
"""DepGraph → markdown deps section (simplified for data-flow model)."""

from __future__ import annotations

from .deps_resolver import DepEdge, DepGraph


def render_section(graph: DepGraph) -> str:
    """Render the canonical 'Dependencies & Integrations' section.

    Output is byte-deterministic for the same DepGraph. The Future-*
    subsections emit placeholders until Phase C populates them.
    """

    lines: list[str] = []
    lines.append("## Dependencies & Integrations")
    lines.append("")
    lines.append(
        "> Auto-generated section — the **Current** subsections are derived from "
        f"`services/{graph.focus}/service.yml`'s `data_flow.calls` field "
        f"(and inverse passes). Re-run "
        f"`python -m bootstrapper.docs.regen {graph.focus}` after manifest changes."
    )
    lines.append("")

    # Current — Upstream
    lines.append("### Current — Upstream (this service calls)")
    lines.append("")
    if graph.upstream:
        lines.append("| Service | Category |")
        lines.append("|---|---|")
        for e in graph.upstream:
            bidi = " ↔" if e.bidirectional else ""
            lines.append(f"| {e.other}{bidi} | {e.other_category} |")
    else:
        lines.append("_No upstream calls._")
    lines.append("")

    # Current — Downstream
    lines.append("### Current — Downstream (services that call this)")
    lines.append("")
    if graph.downstream:
        lines.append("| Service | Category |")
        lines.append("|---|---|")
        for e in graph.downstream:
            bidi = " ↔" if e.bidirectional else ""
            lines.append(f"| {e.other}{bidi} | {e.other_category} |")
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
```

- [ ] **Step 5.2: Update tests**

Overwrite `bootstrapper/tests/test_deps_section_writer.py`:

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
    """Hermes deps section is byte-stable against committed fixture."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import build_doc_graph
    g = build_doc_graph("hermes", SERVICES_DIR)
    rendered = render_section(g)
    golden = (FIXTURE_DIR / "hermes.deps_section.md").read_text()
    assert rendered == golden, "Hermes deps section drift — update the fixture."


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
        assert heading in text


def test_section_uses_two_column_table():
    """New table shape is Service | Category (only 2 columns)."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import build_doc_graph
    g = build_doc_graph("hermes", SERVICES_DIR)
    text = render_section(g)
    # The header row "| Service | Category |" must be present
    assert "| Service | Category |" in text
    # The old "| Service | Type | Mechanism" header must NOT be present
    assert "| Service | Type | Mechanism" not in text


def test_section_emits_empty_table_placeholder():
    """A graph with no upstream emits the explicit `_No upstream calls._` line."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import DepGraph
    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    text = render_section(g)
    assert "_No upstream calls._" in text
    assert "_No downstream consumers._" in text
```

- [ ] **Step 5.3: Regenerate Hermes deps_section fixture**

```bash
PYTHONPATH=bootstrapper python -c "
from docs.deps_resolver import build_doc_graph
from docs.deps_section_writer import render_section
from pathlib import Path
Path('bootstrapper/tests/fixtures/hermes.deps_section.md').write_text(
    render_section(build_doc_graph('hermes', Path('services'))))
print('regenerated')
"
cat bootstrapper/tests/fixtures/hermes.deps_section.md | head -30
```

Visually verify: Service|Category table; bidirectional `litellm ↔` row in both Upstream and Downstream (Hermes↔LiteLLM).

- [ ] **Step 5.4: Run tests — expect pass**

```bash
cd bootstrapper && uv run pytest tests/test_deps_section_writer.py -v
```

Expected: 4 passing.

- [ ] **Step 5.5: Commit**

```bash
git add bootstrapper/docs/deps_section_writer.py \
        bootstrapper/tests/test_deps_section_writer.py \
        bootstrapper/tests/fixtures/hermes.deps_section.md
git commit -m "docs: simplify deps-section tables to Service | Category"
```

---

## Task 6: Regenerate all 21 service artifacts

**Files:**
- Modify: 21 × `docs/services/<name>/README.md` (deps section)
- Modify: 21 × `docs/services/<name>/architecture.svg`
- Modify: 21 × `docs/services/<name>/architecture.html`

- [ ] **Step 6.1: Dry-run preview**

```bash
PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all --dry-run | head -30
```

Expected: ~63 "would write" lines.

- [ ] **Step 6.2: Run for real**

```bash
PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all
```

Expected: silent success.

- [ ] **Step 6.3: Drift gate passes**

```bash
cd bootstrapper && uv run pytest tests/test_docs_drift.py -v
```

Expected: 1 passed.

- [ ] **Step 6.4: Link validator still clean**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/diagram-refresh
python scripts/check_doc_links.py; echo "exit=$?"
```

Expected: exit 0.

- [ ] **Step 6.5: Full test suite green**

```bash
cd bootstrapper && uv run pytest -q
```

Expected: ~312 passed (pre-existing tests + this plan's new ones; resolver tests rewritten so count may match or differ slightly).

- [ ] **Step 6.6: Visual spot-check — 5 diagrams**

```bash
PYTHONPATH=bootstrapper python -c "
from docs.deps_resolver import build_doc_graph
from docs.diagram_renderer import render_html
from pathlib import Path
for svc in ('hermes', 'kong', 'litellm', 'minio', 'neo4j'):
    Path(f'/tmp/{svc}-preview.html').write_text(render_html(build_doc_graph(svc, Path('services'))))
    print(f'/tmp/{svc}-preview.html')
"
open /tmp/hermes-preview.html /tmp/kong-preview.html /tmp/litellm-preview.html /tmp/minio-preview.html /tmp/neo4j-preview.html
```

User visually approves before continuing. Expected divergence from the brainstorming mockup: **Kong's fronted services appear in Kong's UPSTREAM lane (not downstream)**. This is consistent with the user's stated rule "Ollama is upstream of LiteLLM because LiteLLM routes to Ollama" — the same rule applied to Kong puts Kong-fronted backends in Kong's upstream. The mockup's "Downstream (call Kong)" label was inconsistent with the universal convention; the implementation prefers the consistent rule. If the user wants the mockup's specific layout for Kong, we'd need a special-cased lane swap per service category — flag and ask. Otherwise approve and proceed.

If any other diagram looks wrong, fix renderer/resolver/manifest before proceeding to Task 7.

- [ ] **Step 6.7: Commit the regenerated artifacts**

```bash
git add docs/services/
git commit -m "docs: regenerate all 21 service diagrams + deps sections for data-flow model"
```

---

## Task 7: CHANGELOG + acceptance gates + tag

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 7.1: Append CHANGELOG entry**

Open `docs/CHANGELOG.md`. Inside the `## [Unreleased]` block, add a new `### Changed` (or `### Added` if no Changed exists yet) sub-block at the top of the `[Unreleased]` section:

```markdown
### Changed (Architecture diagrams — data-flow model + clustered layout)

- Architecture diagrams under `docs/services/<name>/` now render the **data-flow** model (runtime "X calls Y" edges) instead of the bootstrap-dep model. Source of truth is a new optional `data_flow.calls` field per `services/<name>/service.yml`.
- Diagram layout redesigned: services in the upstream and downstream lanes group by category (infra / data / llm / media / agents / apps) into mini-clusters; one edge per cluster (not per pill); focus box gains a category-colored glow; legend bar + 3 summary cards below.
- Deps-section tables in each README simplified to `Service | Category` (the old Type / Mechanism / Failure mode columns no longer have data in the data-flow model).
- `depends_on.required`, `runtime_adaptive.adapts_to`, `runtime_deps.optional`, and `doc_extras.diagram.extra_consumers` remain in manifests (still used by the compose layer) but the diagram resolver no longer reads them.
- Spec: `docs/superpowers/specs/2026-05-22-diagram-refresh-design.md`.
```

- [ ] **Step 7.2: Run all acceptance gates**

```bash
# Gate 1: regen --all runs clean
PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all
echo "Gate 1 exit: $?"  # expect 0

# Gate 2: drift test passes
cd bootstrapper && uv run pytest tests/test_docs_drift.py -v && cd ..

# Gate 3: Hermes golden snapshot matches
cd bootstrapper && uv run pytest tests/test_diagram_renderer.py::test_svg_matches_golden_snapshot tests/test_deps_section_writer.py::test_section_for_hermes_matches_golden -v && cd ..

# Gate 4: Every SVG parses as well-formed XML
cd bootstrapper && uv run pytest tests/test_diagram_renderer.py::test_svg_is_well_formed_xml_across_services -v && cd ..

# Gate 5: Schema additions validate
cd bootstrapper && uv run pytest tests/test_manifests.py -v && cd ..

# Gate 6: Spot-check (visual) done in Task 6.6 — user approved.

# Gate 7: data_flow.calls entries point only at valid doc folders or manifests
PYTHONPATH=bootstrapper python -c "
from services.manifests import load_manifests
from pathlib import Path
ms = {m.name: m for m in load_manifests(Path('services'))}
all_names = set(ms) | {'stt-provider', 'tts-provider', 'doc-processor', 'multi2vec-clip'}
broken = []
for m in ms.values():
    for tgt in (m.data_flow or {}).get('calls', []) or []:
        if tgt not in all_names:
            broken.append(f'{m.name}.data_flow.calls references unknown: {tgt}')
if broken:
    print('\n'.join(broken))
    raise SystemExit(1)
print('Gate 7: all data_flow.calls targets resolve.')
"

# Final: full test suite green
cd bootstrapper && uv run pytest -q
```

Expected: all green.

- [ ] **Step 7.3: Commit the CHANGELOG**

```bash
git add docs/CHANGELOG.md
git commit -m "docs: changelog entry for diagram refresh (data-flow model)"
```

- [ ] **Step 7.4: Tag the landing point**

```bash
git tag diagram-refresh -m "Diagram refresh complete: data-flow model + clustered layout"
git tag -l 'diagram-refresh'
```

Expected: prints `diagram-refresh`.

---

## Implementation complete

You have shipped:

1. A new optional manifest field `data_flow.calls` with schema + dataclass support.
2. Populated `data_flow.calls` across 22 manifests, encoding runtime data-flow truth.
3. Rewritten `deps_resolver.py` for the data-flow model — simpler `DepEdge`, single edge kind.
4. Rewritten `diagram_renderer.py` for the clustered-by-category layout.
5. Simplified `deps_section_writer.py` to `Service | Category` columns.
6. Regenerated all 21 architecture SVGs + HTML wrappers + deps sections.
7. New Hermes golden snapshots (`hermes.architecture.svg`, `hermes.deps_section.md`).
8. CHANGELOG entry + `diagram-refresh` tag.

The bootstrapper's compose orchestration is unchanged — `depends_on.required` / `runtime_adaptive.adapts_to` / `runtime_deps.optional` still drive startup. The diagram resolver simply no longer reads them.

Run `superpowers:finishing-a-development-branch` to merge this work back to main.
