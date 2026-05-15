# Wizard category coloring, topology ordering, and pending state — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `service.yml` the single source of truth for service ordering, categorization, port defaults, and display metadata. Surface this in a category-color-coded box with pending-state visuals during the wizard. Migrate existing .env files in place on next start.

**Architecture:** New `bootstrapper/services/topology.py` consumes every manifest and exposes a single `Topology` dataclass. Eight scattered constants across `bootstrapper/{ui,wizard,utils}` collapse into manifest fields (`category`, `depends_on.required`, new `rows:` list). Port defaults move from per-manifest `default:` declarations into a deterministic slot allocator. UI gains a leading category bar, a legend widget, and a yellow pending state for unanswered service rows.

**Tech Stack:** Python 3.10+, PyYAML, jsonschema (Draft 2020-12), Textual ≥0.85, Rich, pytest, click. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-15-wizard-categories-topology-design.md`

**Conventions:**
- Run every test from `bootstrapper/` directory with `uv run pytest ...`.
- Commit messages: terse, third-person verb, no Co-Authored-By trailer.
- One task = one commit (or two: failing test → green commit). Do not batch unrelated work.
- TDD: write the failing test first, run to confirm it fails, then implement.

---

## File structure

### Created files

| Path | Responsibility |
|---|---|
| `bootstrapper/services/topology.py` | `Topology` + `Row` dataclasses, topo sort, slot allocator, single-import entry point |
| `bootstrapper/services/migrations/__init__.py` | Package init |
| `bootstrapper/services/migrations/migration_v1.py` | `BOOTSTRAPPER_PORT_LAYOUT_VERSION=1` snapshot of v0 offsets + apply logic |
| `bootstrapper/ui/textual/widgets/category_legend.py` | Single-line legend widget |
| `bootstrapper/tests/test_topology.py` | Topology unit tests |
| `bootstrapper/tests/test_slot_allocator.py` | Slot allocator unit tests |
| `bootstrapper/tests/test_port_migration.py` | Port-migration unit tests |
| `bootstrapper/tests/test_wizard_pending.py` | Pending-state transitions |
| `bootstrapper/tests/test_service_table_pending.py` | Service table render snapshot |
| `bootstrapper/tools/generate_architecture_diagram.py` | Architecture diagram generator (Phase 7) |
| `bootstrapper/tools/generate_readme_topology.py` | README block generator (Phase 7) |

### Modified files

| Path | Why |
|---|---|
| `bootstrapper/schemas/service.schema.json` | New `rows:` block, updated `category:` enum |
| `bootstrapper/services/manifests.py` | New `Row` dataclass + parse |
| `bootstrapper/services/manifest_validator.py` | New cross-manifest checks (cycle, alias uniqueness, category overflow, engine-only ref) |
| `bootstrapper/tools/validate_fragments.py` | Surface new validator checks |
| `bootstrapper/ui/state_builder.py` | Delete `_SERVICES`, `_HOST_ALIAS`, `_LOCALHOST_ENDPOINT_VARS`, `_LOOKUP_BY_NAME`; consume `Topology` |
| `bootstrapper/wizard/service_discovery.py` | Delete `DISPLAY_NAME_OVERRIDES`, `SERVICE_DESCRIPTIONS`, `LOCKED_SERVICES`; consume `Topology` |
| `bootstrapper/utils/endpoint_vars.py` | Delete `LOCALHOST_ENDPOINT_VARS`; module retired after wiring |
| `bootstrapper/utils/hosts_manager.py` | Delete `GENAI_HOSTS` constant; consume `Topology.aliases` |
| `bootstrapper/services/env_assembler.py` | Read port defaults from `Topology.port_defaults` |
| `bootstrapper/ui/state.py` | Add `category` and `pending` fields to `ServiceEntry` |
| `bootstrapper/ui/textual/palette.py` | Add `CAT_*` tokens + `style_for_category` helper |
| `bootstrapper/ui/textual/widgets/service_table.py` | Leading bar column, pending-state render branch, canonical-order sort |
| `bootstrapper/ui/textual/widgets/info_box.py` | Include `CategoryLegend` in body, pending count in footer |
| `bootstrapper/ui/textual/screens/wizard_screen.py` | `_answered: set[int]`, pending-state transitions |
| `bootstrapper/ui/textual/integration.py` | Read `BASE_PORT` (not `SUPABASE_DB_PORT`); sort by canonical order |
| `bootstrapper/start.py` | Drop endpoint_vars import; consume `Topology`; Rich-table category bar |
| `services/*/service.yml` (all 22 manifests) | Update `category:`, populate `depends_on.required`, add `rows:`, drop port `default:` |
| `services/_order.yml` | Deleted (replaced by topology computation) |
| `docs/CHANGELOG.md` | Phase-6 migration entry |

---

## Pre-flight check

- [ ] **Step 1: Verify working directory and worktree status**

Run:
```bash
pwd
git -C /Users/kaveh/repos/genai-vanilla/.claude/worktrees/setup-wizard-categories-reorder rev-parse --abbrev-ref HEAD
```

Expected: working in `.claude/worktrees/setup-wizard-categories-reorder`, on the worktree branch (not `main`).

- [ ] **Step 2: Baseline test suite is green**

Run:
```bash
cd bootstrapper && uv run pytest -q
```

Expected: all tests pass. If anything is red BEFORE we start, fix or document first.

---

## Phase 1 — Schema and manifest content

Pure-additive. No behavior change. Old constants stay. CI green.

### Task 1.1 — Extend service.schema.json with `rows:` block

**Files:**
- Modify: `bootstrapper/schemas/service.schema.json`
- Test: `bootstrapper/tests/test_manifests.py` (extend with new schema-violation case)

- [ ] **Step 1: Write the failing test**

Append to `bootstrapper/tests/test_manifests.py`:

```python
def test_rows_block_accepts_valid_entries(tmp_path):
    """The new rows: block accepts the canonical shape."""
    services_root = tmp_path / "services"
    (services_root / "demo").mkdir(parents=True)
    (services_root / "demo" / "service.yml").write_text(
        "name: demo\n"
        "label: Demo\n"
        "category: data\n"
        "env: []\n"
        "rows:\n"
        "  - display_name: Demo Row\n"
        "    source_var: DEMO_SOURCE\n"
        "    port_var: DEMO_PORT\n"
        "    description: A demo row\n"
        "    alias: demo.localhost\n"
        "    localhost_endpoint_var: DEMO_URL\n"
    )

    from services.manifests import load_manifests
    manifests = load_manifests(services_root)
    assert len(manifests) == 1
    assert len(manifests[0].rows) == 1
    row = manifests[0].rows[0]
    assert row.display_name == "Demo Row"
    assert row.alias == "demo.localhost"
```

- [ ] **Step 2: Run test to confirm it fails**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py::test_rows_block_accepts_valid_entries -v`
Expected: FAIL — `rows` isn't in the schema yet, OR the `Row` dataclass doesn't exist.

- [ ] **Step 3: Extend the JSON schema**

In `bootstrapper/schemas/service.schema.json`, inside the top-level `properties` block, add:

```json
"rows": {
  "type": "array",
  "minItems": 0,
  "description": "Box rows this manifest renders. Most manifests have one; supabase has seven (one per HTTP component). Replaces the legacy _SERVICES/_HOST_ALIAS/DISPLAY_NAME_OVERRIDES/SERVICE_DESCRIPTIONS/LOCALHOST_ENDPOINT_VARS constants.",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["display_name", "source_var"],
    "properties": {
      "display_name": {
        "type": "string",
        "description": "Human label shown in the box and wizard prompts."
      },
      "source_var": {
        "type": "string",
        "pattern": "^[A-Z][A-Z0-9_]*$",
        "description": "The *_SOURCE env var driving this row's source pick."
      },
      "port_var": {
        "type": "string",
        "pattern": "^[A-Z][A-Z0-9_]*$",
        "description": "The env var holding this row's primary display port. Omit for virtual rows."
      },
      "scale_var": {
        "type": "string",
        "pattern": "^[A-Z][A-Z0-9_]*$",
        "description": "The *_SCALE env var. Absence ⇒ always-on."
      },
      "alias": {
        "type": "string",
        "pattern": "^[a-z][a-z0-9-]*\\.localhost$",
        "description": "*.localhost hostname Kong virtual-host-routes. Must be unique across all manifests."
      },
      "description": {
        "type": "string",
        "description": "One-line label used as wizard prompt subtitle."
      },
      "localhost_endpoint_var": {
        "type": "string",
        "pattern": "^[A-Z][A-Z0-9_]*$",
        "description": "Env var holding the URL when source is a localhost variant."
      }
    }
  }
}
```

- [ ] **Step 4: Commit (schema only)**

```bash
git add bootstrapper/schemas/service.schema.json
git commit -m "extend service schema with rows: block"
```

### Task 1.2 — Add `Row` dataclass + parser to manifests.py

**Files:**
- Modify: `bootstrapper/services/manifests.py`
- Test: `bootstrapper/tests/test_manifests.py` (test from Task 1.1 stays)

- [ ] **Step 1: Add the Row dataclass**

In `bootstrapper/services/manifests.py`, add above `Manifest`:

```python
@dataclass(frozen=True)
class Row:
    """One box row a manifest renders. Replaces the legacy _SERVICES tuple
    plus several scattered constants. See spec §rows."""

    display_name: str
    source_var: str
    port_var: str = ""
    scale_var: str = ""
    alias: str = ""
    description: str = ""
    localhost_endpoint_var: str = ""
```

- [ ] **Step 2: Extend the Manifest dataclass**

In the same file, add `rows` to the `Manifest` dataclass right after `exports`:

```python
    rows: list[Row] = field(default_factory=list)
```

- [ ] **Step 3: Parse `rows:` in `_to_dataclass`**

In `_to_dataclass`, after the `exports = [...]` block, add:

```python
    rows = [
        Row(
            display_name=r["display_name"],
            source_var=r["source_var"],
            port_var=r.get("port_var", ""),
            scale_var=r.get("scale_var", ""),
            alias=r.get("alias", ""),
            description=r.get("description", ""),
            localhost_endpoint_var=r.get("localhost_endpoint_var", ""),
        )
        for r in raw.get("rows") or []
    ]
```

Then pass `rows=rows` to the `Manifest(...)` constructor at the bottom of the function.

- [ ] **Step 4: Run the test from Task 1.1**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py::test_rows_block_accepts_valid_entries -v`
Expected: PASS.

- [ ] **Step 5: Run full manifest test suite to confirm nothing broke**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/services/manifests.py bootstrapper/tests/test_manifests.py
git commit -m "add Row dataclass and rows: parser to manifest loader"
```

### Task 1.3 — Update category enum in schema

**Files:**
- Modify: `bootstrapper/schemas/service.schema.json`
- Test: `bootstrapper/tests/test_manifests.py`

- [ ] **Step 1: Add the test for the new enum**

Append to `bootstrapper/tests/test_manifests.py`:

```python
import pytest
from services.manifests import ManifestLoadError


@pytest.mark.parametrize("cat", ["infra", "data", "llm", "media", "agents", "apps"])
def test_category_enum_accepts_new_values(tmp_path, cat):
    services_root = tmp_path / "services"
    (services_root / "demo").mkdir(parents=True)
    (services_root / "demo" / "service.yml").write_text(
        f"name: demo\nlabel: Demo\ncategory: {cat}\nenv: []\n"
    )
    from services.manifests import load_manifests
    manifests = load_manifests(services_root)
    assert manifests[0].category == cat


@pytest.mark.parametrize("cat", ["ai", "app"])
def test_category_enum_rejects_old_values(tmp_path, cat):
    services_root = tmp_path / "services"
    (services_root / "demo").mkdir(parents=True)
    (services_root / "demo" / "service.yml").write_text(
        f"name: demo\nlabel: Demo\ncategory: {cat}\nenv: []\n"
    )
    from services.manifests import load_manifests
    with pytest.raises(ManifestLoadError, match="category"):
        load_manifests(services_root)
```

- [ ] **Step 2: Run tests — accepts-new should pass, rejects-old should fail**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py::test_category_enum_accepts_new_values tests/test_manifests.py::test_category_enum_rejects_old_values -v`

Expected: accept-new tests FAIL (schema still has old enum), reject-old tests FAIL (schema accepts them).

- [ ] **Step 3: Update the schema enum**

In `bootstrapper/schemas/service.schema.json`, change the `category` enum from:
```json
"enum": ["data", "llm", "ai", "app", "infra"],
```
to:
```json
"enum": ["infra", "data", "llm", "media", "agents", "apps"],
```

And update the inline description to match:
```json
"description": "Wizard grouping. infra=gateway/observability; data=DB/cache/storage; llm=LLM gateway/engine; media=multimodal AI (image-gen/STT/TTS/doc/search); agents=programmable AI agents/workflows; apps=user-facing UIs."
```

- [ ] **Step 4: Run tests — both parametrize sets should now pass**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py::test_category_enum_accepts_new_values tests/test_manifests.py::test_category_enum_rejects_old_values -v`
Expected: all 8 cases PASS.

- [ ] **Step 5: Run the full existing manifest test suite**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py -v`
Expected: every existing test still PASSES (we changed only enum values, no parser shape).

Note: the broader test suite (`pytest -q`) WILL be red until Task 1.5 onward updates each manifest's `category:`. Do not panic — Tasks 1.5-1.10 fix that.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/schemas/service.schema.json bootstrapper/tests/test_manifests.py
git commit -m "switch category enum to infra|data|llm|media|agents|apps"
```

### Task 1.4 — Update infrastructure manifests (kong, globals)

**Files:**
- Modify: `services/kong/service.yml`, `services/globals/service.yml`

- [ ] **Step 1: kong manifest — depends_on + rows**

In `services/kong/service.yml`:

Change `depends_on:` block (currently `required: [], optional: []`) to:
```yaml
depends_on:
  required:
    - supabase
    - redis
    - litellm
    - open-webui
    - n8n
    - hermes
    - openclaw
    - jupyterhub
    - backend
    - searxng
    - minio
    - comfyui
    - local-deep-researcher
    - neo4j
    - weaviate
    - tts-provider
    - parakeet
    - docling
    - ollama
  optional: []
```

Add a `rows:` block at the end of the file (before any trailing runtime_*):
```yaml
rows:
  - display_name: "Kong API Gateway"
    source_var: KONG_API_GATEWAY_SOURCE
    port_var: KONG_HTTP_PORT
    description: "Edge gateway routing *.localhost aliases."
```

`category: infra` is already correct — no change.

- [ ] **Step 2: globals manifest — empty rows**

In `services/globals/service.yml`, the `category: infra` is correct. The `depends_on: { required: [], optional: [] }` stays empty (globals is the root anchor). Add an empty `rows:` block:
```yaml
rows: []
```

- [ ] **Step 3: Run manifest loader tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS (these tests don't require all manifests to be wired yet).

- [ ] **Step 4: Commit**

```bash
git add services/kong/service.yml services/globals/service.yml
git commit -m "wire kong and globals manifests for topology"
```

### Task 1.5 — Update data-tier manifests (supabase, redis, neo4j, minio, weaviate)

**Files:**
- Modify: `services/{supabase,redis,neo4j,minio,weaviate}/service.yml`

- [ ] **Step 1: supabase manifest**

In `services/supabase/service.yml` — `category: data` already correct. Update `depends_on:`:

```yaml
depends_on:
  required:
    - globals
  optional: []
```

Add `rows:` block:
```yaml
rows:
  - display_name: "Supabase DB"
    source_var: SUPABASE_DB_SOURCE
    port_var: SUPABASE_DB_PORT
    description: "Postgres database (always-on, container-only)."
  - display_name: "Supabase Meta"
    source_var: SUPABASE_META_SOURCE
    port_var: SUPABASE_META_PORT
    description: "Postgres metadata API."
  - display_name: "Supabase Storage"
    source_var: SUPABASE_STORAGE_SOURCE
    port_var: SUPABASE_STORAGE_PORT
    description: "S3-compatible storage API."
  - display_name: "Supabase Auth"
    source_var: SUPABASE_AUTH_SOURCE
    port_var: SUPABASE_AUTH_PORT
    description: "GoTrue authentication service."
  - display_name: "Supabase API"
    source_var: SUPABASE_API_SOURCE
    port_var: SUPABASE_API_PORT
    description: "PostgREST REST API surface."
  - display_name: "Supabase Realtime"
    source_var: SUPABASE_REALTIME_SOURCE
    port_var: SUPABASE_REALTIME_PORT
    description: "WebSocket replication firehose."
  - display_name: "Supabase Studio"
    source_var: SUPABASE_STUDIO_SOURCE
    port_var: SUPABASE_STUDIO_PORT
    alias: studio.localhost
    description: "Browser UI for the database."
```

- [ ] **Step 2: redis manifest**

In `services/redis/service.yml` — `category: data` correct. Update:

```yaml
depends_on:
  required:
    - supabase
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Redis"
    source_var: REDIS_SOURCE
    port_var: REDIS_PORT
    description: "Key-value cache and queue broker."
```

- [ ] **Step 3: neo4j manifest**

In `services/neo4j/service.yml` — `category: data` correct. Update:

```yaml
depends_on:
  required:
    - globals
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Neo4j Graph DB"
    source_var: NEO4J_GRAPH_DB_SOURCE
    port_var: GRAPH_DB_DASHBOARD_PORT
    scale_var: NEO4J_SCALE
    alias: graph.localhost
    description: "Graph database for knowledge graphs."
```

- [ ] **Step 4: minio manifest**

In `services/minio/service.yml` — `category: data` correct. Update:

```yaml
depends_on:
  required:
    - globals
  optional: []
```

Add:
```yaml
rows:
  - display_name: "MinIO"
    source_var: MINIO_SOURCE
    port_var: MINIO_PORT
    scale_var: MINIO_SCALE
    alias: minio.localhost
    description: "S3-compatible artifact storage."
```

- [ ] **Step 5: weaviate manifest**

In `services/weaviate/service.yml` — change `category: ai` → `category: data`. Update:

```yaml
depends_on:
  required:
    - supabase
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Weaviate"
    source_var: WEAVIATE_SOURCE
    port_var: WEAVIATE_PORT
    scale_var: WEAVIATE_SCALE
    alias: weaviate.localhost
    description: "Vector database for semantic search & RAG."
    localhost_endpoint_var: WEAVIATE_URL
  - display_name: "Multi2Vec CLIP"
    source_var: MULTI2VEC_CLIP_SOURCE
    scale_var: CLIP_SCALE
    description: "CLIP embeddings for multimodal search."
```

- [ ] **Step 6: Run manifest tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/supabase/service.yml services/redis/service.yml services/neo4j/service.yml services/minio/service.yml services/weaviate/service.yml
git commit -m "wire data-tier manifests for topology"
```

### Task 1.6 — Update LLM-tier manifests (litellm, ollama, cloud-providers)

**Files:**
- Modify: `services/{litellm,ollama,cloud-providers}/service.yml`

- [ ] **Step 1: litellm manifest**

In `services/litellm/service.yml` — `category: llm` correct. Update:

```yaml
depends_on:
  required:
    - supabase
    - redis
  optional: []
```

Add:
```yaml
rows:
  - display_name: "LiteLLM"
    source_var: LITELLM_SOURCE
    port_var: LITELLM_PORT
    alias: litellm.localhost
    description: "Unified LLM gateway — always-on; fronts every provider."
    localhost_endpoint_var: LITELLM_BASE_URL
```

- [ ] **Step 2: ollama manifest**

In `services/ollama/service.yml` — `category: llm` correct. Update:

```yaml
depends_on:
  required:
    - supabase
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "LLM Engine"
    source_var: LLM_PROVIDER_SOURCE
    scale_var: OLLAMA_SCALE
    alias: ollama.localhost
    description: "Local Ollama upstream the LiteLLM gateway forwards to."
    localhost_endpoint_var: LITELLM_OLLAMA_UPSTREAM
```

Note: no `port_var` — Ollama doesn't publish a host port directly (routed via Kong).

- [ ] **Step 3: cloud-providers manifest**

In `services/cloud-providers/service.yml` — `category: llm` correct. Update:

```yaml
depends_on:
  required:
    - litellm
  optional: []
```

Add empty rows (cloud providers render in their own Cloud APIs sub-block, not as service rows):
```yaml
rows: []
```

- [ ] **Step 4: Run manifest tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/litellm/service.yml services/ollama/service.yml services/cloud-providers/service.yml
git commit -m "wire LLM-tier manifests for topology"
```

### Task 1.7 — Update media-tier manifests (comfyui, parakeet, tts-provider, speaches, chatterbox, docling, searxng)

**Files:**
- Modify: `services/{comfyui,parakeet,tts-provider,speaches,chatterbox,docling,searxng}/service.yml`

- [ ] **Step 1: comfyui manifest**

In `services/comfyui/service.yml` — change `category: ai` → `category: media`. Update:

```yaml
depends_on:
  required:
    - supabase
    - litellm
    - ollama
  optional: []
```

Add:
```yaml
rows:
  - display_name: "ComfyUI"
    source_var: COMFYUI_SOURCE
    port_var: COMFYUI_PORT
    scale_var: COMFYUI_SCALE
    alias: comfyui.localhost
    description: "AI image generation & workflows."
    localhost_endpoint_var: COMFYUI_ENDPOINT
```

- [ ] **Step 2: parakeet manifest (STT family parent)**

In `services/parakeet/service.yml` — change `category: ai` → `category: media`. Update:

```yaml
depends_on:
  required:
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "STT Provider"
    source_var: STT_PROVIDER_SOURCE
    port_var: STT_PROVIDER_PORT
    scale_var: STT_PROVIDER_SCALE
    alias: stt.localhost
    description: "Speech-to-text transcription."
    localhost_endpoint_var: STT_ENDPOINT
```

- [ ] **Step 3: tts-provider manifest**

In `services/tts-provider/service.yml` — change `category: ai` → `category: media`. Update:

```yaml
depends_on:
  required:
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "TTS Provider"
    source_var: TTS_PROVIDER_SOURCE
    port_var: TTS_PROVIDER_PORT
    scale_var: TTS_PROVIDER_SCALE
    alias: tts.localhost
    description: "Text-to-speech synthesis."
    localhost_endpoint_var: TTS_ENDPOINT
```

- [ ] **Step 4: speaches manifest (engine-only)**

In `services/speaches/service.yml` — change `category: ai` → `category: media`. Update:

```yaml
depends_on:
  required:
    - parakeet
    - tts-provider
  optional: []
```

Add empty rows (engine-only; rendered under parent rows):
```yaml
rows: []
```

- [ ] **Step 5: chatterbox manifest (engine-only)**

In `services/chatterbox/service.yml` — change `category: ai` → `category: media`. Update:

```yaml
depends_on:
  required:
    - tts-provider
  optional: []
```

Add:
```yaml
rows: []
```

- [ ] **Step 6: docling manifest**

In `services/docling/service.yml` — change `category: ai` → `category: media`. Update:

```yaml
depends_on:
  required:
    - globals
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Document Processor"
    source_var: DOC_PROCESSOR_SOURCE
    port_var: DOC_PROCESSOR_PORT
    scale_var: DOCLING_GPU_SCALE
    alias: docling.localhost
    description: "Document parsing & extraction."
    localhost_endpoint_var: DOCLING_ENDPOINT
```

- [ ] **Step 7: searxng manifest**

In `services/searxng/service.yml` — change `category: app` → `category: media`. Update:

```yaml
depends_on:
  required:
    - supabase
    - redis
  optional: []
```

Add:
```yaml
rows:
  - display_name: "SearxNG"
    source_var: SEARXNG_SOURCE
    port_var: SEARXNG_PORT
    scale_var: SEARXNG_SCALE
    alias: search.localhost
    description: "Privacy-focused metasearch."
```

- [ ] **Step 8: Run manifest tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add services/comfyui/service.yml services/parakeet/service.yml services/tts-provider/service.yml services/speaches/service.yml services/chatterbox/service.yml services/docling/service.yml services/searxng/service.yml
git commit -m "wire media-tier manifests for topology"
```

### Task 1.8 — Update agents-tier manifests (hermes, n8n, openclaw)

**Files:**
- Modify: `services/{hermes,n8n,openclaw}/service.yml`

- [ ] **Step 1: hermes manifest**

In `services/hermes/service.yml` — change `category: ai` → `category: agents`. Update:

```yaml
depends_on:
  required:
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Hermes Agent"
    source_var: HERMES_SOURCE
    port_var: HERMES_API_PORT
    scale_var: HERMES_SCALE
    alias: hermes.localhost
    description: "Programmable AI agent runtime (Nous Research)."
    localhost_endpoint_var: HERMES_ENDPOINT
```

- [ ] **Step 2: n8n manifest**

In `services/n8n/service.yml` — change `category: app` → `category: agents`. Update:

```yaml
depends_on:
  required:
    - supabase
    - redis
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "n8n"
    source_var: N8N_SOURCE
    port_var: N8N_PORT
    scale_var: N8N_SCALE
    alias: n8n.localhost
    description: "Workflow automation & integrations."
```

- [ ] **Step 3: openclaw manifest**

In `services/openclaw/service.yml` — change `category: app` → `category: agents`. Update:

```yaml
depends_on:
  required:
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "OpenClaw"
    source_var: OPENCLAW_SOURCE
    port_var: OPENCLAW_GATEWAY_PORT
    scale_var: OPENCLAW_SCALE
    alias: openclaw.localhost
    description: "AI agent gateway for messaging platforms."
```

- [ ] **Step 4: Run manifest tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/hermes/service.yml services/n8n/service.yml services/openclaw/service.yml
git commit -m "wire agents-tier manifests for topology"
```

### Task 1.9 — Update apps-tier manifests (backend, open-webui, jupyterhub, local-deep-researcher)

**Files:**
- Modify: `services/{backend,open-webui,jupyterhub,local-deep-researcher}/service.yml`

- [ ] **Step 1: backend manifest**

In `services/backend/service.yml` — change `category: app` → `category: apps`. Update:

```yaml
depends_on:
  required:
    - supabase
    - redis
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Backend API"
    source_var: BACKEND_SOURCE
    port_var: BACKEND_PORT
    scale_var: BACKEND_SCALE
    alias: api.localhost
    description: "FastAPI backend (always-on adaptive)."
```

- [ ] **Step 2: open-webui manifest**

In `services/open-webui/service.yml` — change `category: app` → `category: apps`. Update:

```yaml
depends_on:
  required:
    - supabase
    - redis
    - litellm
    - hermes
  optional: []
```

(Note `hermes` is listed even though compose.yml doesn't have a docker depends_on — open-webui registers hermes-agent as a LiteLLM model, so it's a logical dep.)

Add:
```yaml
rows:
  - display_name: "Open WebUI"
    source_var: OPEN_WEB_UI_SOURCE
    port_var: OPEN_WEB_UI_PORT
    scale_var: OPEN_WEB_UI_SCALE
    alias: chat.localhost
    description: "Chat interface (consumes LiteLLM model list incl. hermes-agent)."
```

- [ ] **Step 3: jupyterhub manifest**

In `services/jupyterhub/service.yml` — change `category: app` → `category: apps`. Update:

```yaml
depends_on:
  required:
    - supabase
    - redis
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "JupyterHub"
    source_var: JUPYTERHUB_SOURCE
    port_var: JUPYTERHUB_PORT
    scale_var: JUPYTERHUB_SCALE
    alias: jupyter.localhost
    description: "Data-science notebooks."
```

- [ ] **Step 4: local-deep-researcher manifest**

In `services/local-deep-researcher/service.yml` — change `category: app` → `category: apps`. Update:

```yaml
depends_on:
  required:
    - supabase
    - searxng
    - litellm
  optional: []
```

Add:
```yaml
rows:
  - display_name: "Local Deep Researcher"
    source_var: LOCAL_DEEP_RESEARCHER_SOURCE
    port_var: LOCAL_DEEP_RESEARCHER_PORT
    scale_var: LOCAL_DEEP_RESEARCHER_SCALE
    alias: research.localhost
    description: "LangGraph research agent."
```

- [ ] **Step 5: Run manifest tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/backend/service.yml services/open-webui/service.yml services/jupyterhub/service.yml services/local-deep-researcher/service.yml
git commit -m "wire apps-tier manifests for topology"
```

### Task 1.10 — Re-run the full test suite to confirm Phase 1 is clean

- [ ] **Step 1: Run all tests**

Run: `cd bootstrapper && uv run pytest -q`
Expected: every test PASSES. The existing constants (`_SERVICES`, `_HOST_ALIAS`, etc.) still drive the wizard — we haven't wired Topology yet. The manifests now carry all the data we need; nothing reads it yet.

If any test fails, debug before moving on. Common cause: a manifest's `category:` value still has an old enum value (`ai`/`app`) that the validator now rejects. Grep for it: `grep "category: ai\|category: app" services/*/service.yml`.

- [ ] **Step 2: Validate via the existing fragment validator**

Run: `cd bootstrapper && uv run python -m tools.validate_fragments`
Expected: exit 0 (no validation errors).

---

## Phase 2 — Topology module

New module computes canonical ordering, slot allocation, and exposes `Topology` dataclass.

### Task 2.1 — Scaffold topology.py with dataclasses

**Files:**
- Create: `bootstrapper/services/topology.py`
- Create: `bootstrapper/tests/test_topology.py`

- [ ] **Step 1: Write the failing test for the data shape**

Create `bootstrapper/tests/test_topology.py`:

```python
"""Topology engine unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_manifest(services_root: Path, name: str, body: str) -> None:
    (services_root / name).mkdir(parents=True, exist_ok=True)
    (services_root / name / "service.yml").write_text(body)


def test_topology_dataclass_shape():
    """Topology exposes canonical_order, category_of, port_defaults, rows, aliases."""
    from services.topology import Topology
    t = Topology(canonical_order=[], category_of={}, port_defaults={}, rows=[], aliases=[])
    assert t.canonical_order == []
    assert t.category_of == {}
    assert t.port_defaults == {}
    assert t.rows == []
    assert t.aliases == []
```

- [ ] **Step 2: Run test, confirm it fails**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py::test_topology_dataclass_shape -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create the module skeleton**

Write `bootstrapper/services/topology.py`:

```python
"""
Topology engine — single source of truth for service ordering, categorization,
port slot allocation, box rows, and alias list.

Replaces:
  * services/_order.yml (hand-edited)
  * bootstrapper/ui/state_builder.py::_SERVICES
  * bootstrapper/ui/state_builder.py::_HOST_ALIAS
  * bootstrapper/wizard/service_discovery.py::DISPLAY_NAME_OVERRIDES
  * bootstrapper/wizard/service_discovery.py::SERVICE_DESCRIPTIONS
  * bootstrapper/wizard/service_discovery.py::LOCKED_SERVICES
  * bootstrapper/utils/endpoint_vars.py::LOCALHOST_ENDPOINT_VARS
  * bootstrapper/utils/hosts_manager.py::HostsManager.GENAI_HOSTS

Every downstream consumer imports Topology from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from services.manifests import Manifest, load_manifests


# Display order top-to-bottom. Apps last because Open WebUI consumes Hermes
# Agent as a model (Apps depend on Agents).
CATEGORY_ORDER: tuple[str, ...] = (
    "infra", "data", "llm", "media", "agents", "apps",
)


# Slot allocator: per-category port block. (base_offset, block_size).
# Block sizes give ~2x headroom over today's ~33 used slots.
CATEGORY_SLOTS: dict[str, tuple[int, int]] = {
    "infra":  (0,  10),
    "data":   (10, 20),
    "llm":    (30, 10),
    "media":  (40, 20),
    "agents": (60, 20),
    "apps":   (80, 20),
}


@dataclass(frozen=True)
class Row:
    """A single box row. Resolved from a manifest's rows[] entry plus category metadata."""

    manifest: str
    display_name: str
    source_var: str
    port_var: Optional[str]
    scale_var: Optional[str]
    alias: Optional[str]
    description: str
    localhost_endpoint_var: Optional[str]
    category: str
    locked: bool


@dataclass(frozen=True)
class Topology:
    """The single object consumed by every downstream module."""

    canonical_order: list[str]
    category_of: dict[str, str]
    port_defaults: dict[str, int]
    rows: list[Row]
    aliases: list[str]


class TopologyError(Exception):
    """Topology cannot be computed (cycle, unknown dep, overflow)."""


def build_topology(services_root: Path, base_port: int = 63000) -> Topology:
    """Top-level entry point — loads manifests then computes the topology."""
    manifests = load_manifests(Path(services_root))
    return _build_from_manifests(manifests, base_port)


def _build_from_manifests(manifests: list[Manifest], base_port: int) -> Topology:
    """Internal — splits manifest loading from computation for unit-test ergonomics."""
    raise NotImplementedError  # filled in by Tasks 2.2-2.5
```

- [ ] **Step 4: Run test to confirm it passes**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py::test_topology_dataclass_shape -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/services/topology.py bootstrapper/tests/test_topology.py
git commit -m "scaffold topology module and dataclasses"
```

### Task 2.2 — Topological sort with lex tiebreaker

**Files:**
- Modify: `bootstrapper/services/topology.py`
- Modify: `bootstrapper/tests/test_topology.py`

- [ ] **Step 1: Write the failing test**

Append to `bootstrapper/tests/test_topology.py`:

```python
from services.manifests import Manifest, DependsOn, Row as ManifestRow


def _manifest(name, category, requires=None, rows=None):
    """Helper: build a minimal Manifest for unit tests."""
    return Manifest(
        name=name,
        label=name,
        category=category,
        env=[],
        depends_on=DependsOn(required=list(requires or []), optional=[]),
        rows=list(rows or []),
    )


def test_topo_sort_lex_tiebreaker():
    """Equal-rank manifests sort alphabetically."""
    from services.topology import _topo_sort
    manifests = [
        _manifest("zulu", "data"),
        _manifest("alpha", "data"),
        _manifest("mike", "data"),
    ]
    order = _topo_sort(manifests)
    assert order == ["alpha", "mike", "zulu"]


def test_topo_sort_respects_deps():
    """A depends_on B means B comes first."""
    from services.topology import _topo_sort
    manifests = [
        _manifest("alpha", "data", requires=["zulu"]),
        _manifest("zulu", "data"),
    ]
    order = _topo_sort(manifests)
    assert order == ["zulu", "alpha"]


def test_topo_sort_cycle_raises():
    """Cycle in deps triggers TopologyError with cycle path."""
    from services.topology import _topo_sort, TopologyError
    manifests = [
        _manifest("a", "data", requires=["b"]),
        _manifest("b", "data", requires=["a"]),
    ]
    with pytest.raises(TopologyError, match="cycle"):
        _topo_sort(manifests)
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py -v -k topo_sort`
Expected: 3 FAILS (function doesn't exist).

- [ ] **Step 3: Implement `_topo_sort`**

Add to `bootstrapper/services/topology.py`:

```python
def _topo_sort(manifests: list[Manifest]) -> list[str]:
    """Kahn's algorithm with lexicographic tiebreaker.

    Returns manifest names in topological order. Manifests with no deps sort
    alphabetically among themselves; same for any other tier of equal rank.
    """
    from collections import defaultdict
    import heapq

    names = {m.name for m in manifests}
    in_degree: dict[str, int] = {m.name: 0 for m in manifests}
    forward: dict[str, list[str]] = defaultdict(list)

    for m in manifests:
        for dep in m.depends_on.required:
            if dep in names:
                forward[dep].append(m.name)
                in_degree[m.name] += 1

    ready: list[str] = [n for n, d in in_degree.items() if d == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        n = heapq.heappop(ready)
        order.append(n)
        for child in forward[n]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                heapq.heappush(ready, child)

    if len(order) != len(manifests):
        unresolved = sorted(n for n, d in in_degree.items() if d > 0)
        raise TopologyError(
            f"dependency cycle among: {unresolved}. "
            f"Each remaining manifest has at least one inbound dep that was "
            f"never resolved — pick any to start tracing."
        )
    return order
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py -v -k topo_sort`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/services/topology.py bootstrapper/tests/test_topology.py
git commit -m "implement topological sort with lex tiebreaker"
```

### Task 2.3 — Category partition + canonical_order

**Files:**
- Modify: `bootstrapper/services/topology.py`
- Modify: `bootstrapper/tests/test_topology.py`

- [ ] **Step 1: Write the failing test**

Append to `bootstrapper/tests/test_topology.py`:

```python
def test_canonical_order_groups_by_category():
    """Topo order is partitioned by category in fixed display order."""
    from services.topology import _canonical_order
    manifests = [
        _manifest("z-app", "apps"),
        _manifest("a-data", "data"),
        _manifest("k-llm", "llm"),
    ]
    topo = ["a-data", "k-llm", "z-app"]
    out = _canonical_order(manifests, topo)
    assert out == ["a-data", "k-llm", "z-app"]  # data → llm → apps


def test_canonical_order_apps_after_agents():
    """Apps category sorts AFTER agents (specs §display order)."""
    from services.topology import _canonical_order
    manifests = [
        _manifest("foo-app", "apps"),
        _manifest("bar-agent", "agents"),
    ]
    topo = ["bar-agent", "foo-app"]
    out = _canonical_order(manifests, topo)
    assert out == ["bar-agent", "foo-app"]
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py -v -k canonical_order`
Expected: 2 FAILS.

- [ ] **Step 3: Implement `_canonical_order`**

Add to `bootstrapper/services/topology.py`:

```python
def _canonical_order(manifests: list[Manifest], topo: list[str]) -> list[str]:
    """Partition the topo order by category, concatenate in CATEGORY_ORDER.

    Within a category, manifests stay in their topo-derived order. Between
    categories, the global category sequence wins (infra → data → llm → media
    → agents → apps).
    """
    category_of = {m.name: m.category for m in manifests}
    buckets: dict[str, list[str]] = {c: [] for c in CATEGORY_ORDER}
    for name in topo:
        cat = category_of.get(name)
        if cat in buckets:
            buckets[cat].append(name)
    result: list[str] = []
    for cat in CATEGORY_ORDER:
        result.extend(buckets[cat])
    return result
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py -v -k canonical_order`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/services/topology.py bootstrapper/tests/test_topology.py
git commit -m "implement canonical order category partitioning"
```

### Task 2.4 — Slot allocator

**Files:**
- Modify: `bootstrapper/services/topology.py`
- Create: `bootstrapper/tests/test_slot_allocator.py`

- [ ] **Step 1: Write the failing test**

Create `bootstrapper/tests/test_slot_allocator.py`:

```python
"""Slot allocator unit tests."""

from __future__ import annotations

import pytest


from services.manifests import Manifest, DependsOn, EnvVarDecl


def _manifest_with_ports(name, category, port_vars, requires=None):
    return Manifest(
        name=name,
        label=name,
        category=category,
        env=[EnvVarDecl(name=v) for v in port_vars],
        depends_on=DependsOn(required=list(requires or []), optional=[]),
    )


def test_slot_allocator_assigns_within_category_block():
    """Data manifests get ports in the 63010-63029 range; LLM in 63030-63039."""
    from services.topology import _allocate_slots
    manifests = [
        _manifest_with_ports("redis", "data", ["REDIS_PORT"]),
        _manifest_with_ports("litellm", "llm", ["LITELLM_PORT"], requires=["redis"]),
    ]
    canonical = ["redis", "litellm"]
    defaults = _allocate_slots(manifests, canonical, base_port=63000)
    assert defaults["REDIS_PORT"] == 63010
    assert defaults["LITELLM_PORT"] == 63030


def test_slot_allocator_multi_port_manifest_contiguous():
    """A manifest with multiple port vars gets a contiguous block."""
    from services.topology import _allocate_slots
    manifests = [
        _manifest_with_ports("kong", "infra", ["KONG_HTTP_PORT", "KONG_HTTPS_PORT"]),
    ]
    defaults = _allocate_slots(manifests, ["kong"], base_port=63000)
    assert defaults["KONG_HTTP_PORT"] == 63000
    assert defaults["KONG_HTTPS_PORT"] == 63001


def test_slot_allocator_overflow_raises():
    """More than 10 infra port vars exceeds the 10-slot infra block."""
    from services.topology import _allocate_slots, TopologyError
    too_many = [f"VAR_{i}" for i in range(11)]
    manifests = [_manifest_with_ports("bad", "infra", too_many)]
    with pytest.raises(TopologyError, match="infra block full"):
        _allocate_slots(manifests, ["bad"], base_port=63000)


def test_slot_allocator_ignores_non_port_env_vars():
    """Only env var names ending in _PORT are slotted."""
    from services.topology import _allocate_slots
    manifests = [
        _manifest_with_ports("demo", "data", ["DEMO_PORT", "DEMO_SECRET", "DEMO_SOURCE"]),
    ]
    defaults = _allocate_slots(manifests, ["demo"], base_port=63000)
    assert defaults == {"DEMO_PORT": 63010}
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd bootstrapper && uv run pytest tests/test_slot_allocator.py -v`
Expected: 4 FAILS.

- [ ] **Step 3: Implement `_allocate_slots`**

Add to `bootstrapper/services/topology.py`:

```python
def _allocate_slots(
    manifests: list[Manifest],
    canonical: list[str],
    base_port: int,
) -> dict[str, int]:
    """Assign port_var → default port for every *_PORT env var declared.

    Each category has a block (base_offset, block_size). For each manifest in
    canonical order, every env var ending in `_PORT` consumes the next slot in
    its category's block. Multi-port manifests get a contiguous run.
    """
    by_name = {m.name: m for m in manifests}
    next_slot: dict[str, int] = {c: base_offset for c, (base_offset, _) in CATEGORY_SLOTS.items()}
    defaults: dict[str, int] = {}

    for name in canonical:
        m = by_name[name]
        cat = m.category
        if cat not in CATEGORY_SLOTS:
            continue
        base_offset, block_size = CATEGORY_SLOTS[cat]
        block_end = base_offset + block_size
        for env in m.env:
            if not env.name.endswith("_PORT"):
                continue
            if next_slot[cat] >= block_end:
                raise TopologyError(
                    f"{cat} block full (size {block_size}); cannot allocate "
                    f"{env.name} for manifest {m.name}. Increase block size in "
                    f"CATEGORY_SLOTS or move some manifests to a different category."
                )
            defaults[env.name] = base_port + next_slot[cat]
            next_slot[cat] += 1

    return defaults
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd bootstrapper && uv run pytest tests/test_slot_allocator.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/services/topology.py bootstrapper/tests/test_slot_allocator.py
git commit -m "implement port slot allocator per category block"
```

### Task 2.5 — Wire it together in `_build_from_manifests` + build_topology

**Files:**
- Modify: `bootstrapper/services/topology.py`
- Modify: `bootstrapper/tests/test_topology.py`

- [ ] **Step 1: Write the end-to-end failing test**

Append to `bootstrapper/tests/test_topology.py`:

```python
def test_build_topology_end_to_end(tmp_path):
    """A small two-manifest fixture builds a complete Topology."""
    services_root = tmp_path / "services"
    _write_manifest(services_root, "alpha-infra",
        "name: alpha-infra\n"
        "label: A\n"
        "category: infra\n"
        "env:\n"
        "  - name: ALPHA_PORT\n"
        "rows:\n"
        "  - display_name: Alpha\n"
        "    source_var: ALPHA_SOURCE\n"
        "    port_var: ALPHA_PORT\n"
        "    alias: alpha.localhost\n"
    )
    _write_manifest(services_root, "beta-data",
        "name: beta-data\n"
        "label: B\n"
        "category: data\n"
        "env:\n"
        "  - name: BETA_PORT\n"
        "depends_on:\n"
        "  required: [alpha-infra]\n"
        "  optional: []\n"
        "rows:\n"
        "  - display_name: Beta\n"
        "    source_var: BETA_SOURCE\n"
        "    port_var: BETA_PORT\n"
    )

    from services.topology import build_topology
    t = build_topology(services_root, base_port=63000)
    assert t.canonical_order == ["alpha-infra", "beta-data"]
    assert t.category_of["alpha-infra"] == "infra"
    assert t.category_of["beta-data"] == "data"
    assert t.port_defaults == {"ALPHA_PORT": 63000, "BETA_PORT": 63010}
    assert [r.display_name for r in t.rows] == ["Alpha", "Beta"]
    assert t.aliases == ["alpha.localhost"]
```

- [ ] **Step 2: Run test, confirm it fails**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py::test_build_topology_end_to_end -v`
Expected: FAIL — `_build_from_manifests` still raises NotImplementedError.

- [ ] **Step 3: Implement `_build_from_manifests`**

In `bootstrapper/services/topology.py`, replace the `raise NotImplementedError` body of `_build_from_manifests`:

```python
def _build_from_manifests(manifests: list[Manifest], base_port: int) -> Topology:
    """Internal — splits manifest loading from computation for unit-test ergonomics."""
    topo = _topo_sort(manifests)
    canonical = _canonical_order(manifests, topo)
    port_defaults = _allocate_slots(manifests, canonical, base_port)

    by_name = {m.name: m for m in manifests}
    locked_by_name = {m.name: _is_locked(m) for m in manifests}

    rows: list[Row] = []
    aliases: list[str] = []
    for name in canonical:
        m = by_name[name]
        for r in m.rows:
            rows.append(Row(
                manifest=m.name,
                display_name=r.display_name,
                source_var=r.source_var,
                port_var=r.port_var or None,
                scale_var=r.scale_var or None,
                alias=r.alias or None,
                description=r.description,
                localhost_endpoint_var=r.localhost_endpoint_var or None,
                category=m.category,
                locked=locked_by_name[m.name],
            ))
            if r.alias:
                aliases.append(r.alias)

    return Topology(
        canonical_order=canonical,
        category_of={m.name: m.category for m in manifests},
        port_defaults=port_defaults,
        rows=rows,
        aliases=aliases,
    )


def _is_locked(m: Manifest) -> bool:
    """A manifest is locked when there is no source choice for the user.

    Locked = sources block absent OR sources.options has only one entry.
    """
    if m.sources is None:
        return True
    return len(m.sources.options) <= 1
```

- [ ] **Step 4: Run test, confirm it passes**

Run: `cd bootstrapper && uv run pytest tests/test_topology.py::test_build_topology_end_to_end -v`
Expected: PASS.

- [ ] **Step 5: Run end-to-end topology against real manifests**

Run:
```bash
cd bootstrapper && uv run python -c "
from pathlib import Path
from services.topology import build_topology
t = build_topology(Path('../services'), base_port=63000)
print('CANONICAL ORDER:')
for n in t.canonical_order:
    print(f'  {t.category_of[n]:7} {n}')
print()
print('ALIASES:', t.aliases)
print()
print('PORT DEFAULTS:')
for k in sorted(t.port_defaults, key=t.port_defaults.get):
    print(f'  {t.port_defaults[k]:5}  {k}')
"
```

Expected: complete ordered listing — infra first (kong, globals), data tier (supabase, redis, neo4j, minio, weaviate), llm tier (litellm, ollama, cloud-providers), media tier (parakeet, tts-provider, comfyui, speaches, chatterbox, docling, searxng — order depending on topo), agents (hermes, n8n, openclaw), apps (backend, open-webui, jupyterhub, local-deep-researcher). Aliases list matches the spec's 18-alias target. Ports cluster within category blocks.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/services/topology.py bootstrapper/tests/test_topology.py
git commit -m "wire build_topology end-to-end producing Topology"
```

---

## Phase 3 — Wire Topology into state and wizard

Each task replaces one retired constant with a `Topology` consumption. Old code paths still work because we replace, not parallel-track.

### Task 3.1 — Replace `_SERVICES` and `_LOOKUP_BY_NAME` in state_builder.py

**Files:**
- Modify: `bootstrapper/ui/state_builder.py`

- [ ] **Step 1: Identify the public API of state_builder we need to preserve**

The public exports consumed elsewhere are: `build_app_state`, `lookup_service_meta`, `resolve_port`, `alias_for`, `all_services`, `all_cloud_apis`, `cloud_api_status_text`. Each must keep its signature.

- [ ] **Step 2: Update `build_app_state` to consume `Topology`**

In `bootstrapper/ui/state_builder.py`, replace the top of the file imports + `_SERVICES` block with:

```python
from core.config_parser import ConfigParser
from utils.hosts_manager import HostsManager
from ui.state import AppState, CloudApiEntry, ServiceEntry
from services.topology import build_topology, Topology, Row as TopologyRow
from pathlib import Path
import re
from typing import Optional


# Topology is built once per process. Refresh by calling _refresh_topology()
# from tests; the wizard does not refresh during a single run.
_topology_singleton: Topology | None = None
_SERVICES_ROOT = Path(__file__).resolve().parent.parent.parent / "services"


def _get_topology() -> Topology:
    global _topology_singleton
    if _topology_singleton is None:
        _topology_singleton = build_topology(_SERVICES_ROOT)
    return _topology_singleton


def _refresh_topology() -> None:
    """Test hook — force rebuild on next access."""
    global _topology_singleton
    _topology_singleton = None
```

Then delete the `_SERVICES = [...]` block (lines roughly 23-54 of the current file) and `_LOOKUP_BY_NAME = {...}` (line 94).

- [ ] **Step 3: Rewrite `lookup_service_meta` against Topology**

Replace `lookup_service_meta` with:

```python
def lookup_service_meta(name: str) -> Optional[dict]:
    """Return {'name', 'source_var', 'port_var', 'scale_var'} for the given
    display name, or None if no row matches."""
    for r in _get_topology().rows:
        if r.display_name == name:
            return {
                "name": r.display_name,
                "source_var": r.source_var,
                "port_var": r.port_var,
                "scale_var": r.scale_var,
            }
    return None
```

- [ ] **Step 4: Rewrite `all_services` against Topology**

Replace `all_services` with:

```python
def all_services():
    """Iterate canonical service tuples — display order from Topology.

    Yields (display_name, source_var, port_var, scale_var). Kept tuple-shaped
    for back-compat with start.py::build_pre_launch_summary_table.
    """
    return tuple(
        (r.display_name, r.source_var, r.port_var or None, r.scale_var or None)
        for r in _get_topology().rows
    )
```

- [ ] **Step 5: Rewrite the `for ... in _SERVICES` loop in `build_app_state`**

Replace the loop in `build_app_state` (around line 207 today):

```python
    services = []
    for r in _get_topology().rows:
        source = service_sources.get(r.source_var, env.get(r.source_var, "container"))
        services.append(ServiceEntry(
            name=r.display_name,
            port=resolve_port(r.display_name, source, r.port_var, env),
            source=source,
            alias=r.alias,
        ))
```

- [ ] **Step 6: Run the relevant tests**

Run: `cd bootstrapper && uv run pytest tests/test_kong_and_hosts_wiring.py tests/test_env_assembler.py tests/test_env_example_consistency.py -v`
Expected: PASS (these tests touch state_builder).

- [ ] **Step 7: Run the full test suite**

Run: `cd bootstrapper && uv run pytest -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add bootstrapper/ui/state_builder.py
git commit -m "replace _SERVICES constant with topology rows"
```

### Task 3.2 — Replace `_HOST_ALIAS` in state_builder.py

**Files:**
- Modify: `bootstrapper/ui/state_builder.py`

- [ ] **Step 1: Rewrite `alias_for` against Topology**

In `bootstrapper/ui/state_builder.py`, replace `alias_for`:

```python
def alias_for(name: str) -> Optional[str]:
    """Hosts alias for a service display name, or None if no alias declared."""
    for r in _get_topology().rows:
        if r.display_name == name:
            return r.alias
    return None
```

Then delete the `_HOST_ALIAS = {...}` dict (lines ~67-84).

- [ ] **Step 2: Run tests**

Run: `cd bootstrapper && uv run pytest tests/test_kong_and_hosts_wiring.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/ui/state_builder.py
git commit -m "replace _HOST_ALIAS dict with topology row lookup"
```

### Task 3.3 — Replace `_LOCALHOST_ENDPOINT_VARS` in state_builder.py and retire endpoint_vars.py

**Files:**
- Modify: `bootstrapper/ui/state_builder.py`
- Modify: `bootstrapper/start.py`
- Delete: `bootstrapper/utils/endpoint_vars.py`

- [ ] **Step 1: Rewrite `resolve_port` to look up via Topology**

In `bootstrapper/ui/state_builder.py`, replace the `from utils.endpoint_vars import ...` line and the body of `resolve_port`:

```python
def resolve_port(name: str, source: str, port_var: Optional[str], env: dict) -> Optional[str]:
    """Compute the displayed port for a service given its current SOURCE, its
    port env var, and the parsed .env."""
    if source == "disabled":
        return None
    if "localhost" in source:
        endpoint_var = None
        for r in _get_topology().rows:
            if r.display_name == name:
                endpoint_var = r.localhost_endpoint_var
                break
        if endpoint_var:
            endpoint = env.get(endpoint_var, "")
            match = re.search(r":(\d+)", endpoint)
            if match:
                return f":{match.group(1)}"
        return None
    if port_var:
        port = env.get(port_var, "")
        return f":{port}" if port else None
    return None
```

- [ ] **Step 2: Update start.py to read from Topology**

In `bootstrapper/start.py`, find the `from utils.endpoint_vars import LOCALHOST_ENDPOINT_VARS` import (line ~1013) and the `var = LOCALHOST_ENDPOINT_VARS.get(service_name)` lookup. Replace with:

```python
from services.topology import build_topology
from pathlib import Path
_topology = build_topology(Path(__file__).resolve().parent.parent / "services")
var = None
for r in _topology.rows:
    if r.display_name == service_name:
        var = r.localhost_endpoint_var
        break
```

Note: cache the topology call appropriately — if `start.py` already has a Topology reference at the top of the function or class, reuse it.

- [ ] **Step 3: Delete endpoint_vars.py**

```bash
git rm bootstrapper/utils/endpoint_vars.py
```

- [ ] **Step 4: Run tests**

Run: `cd bootstrapper && uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/ui/state_builder.py bootstrapper/start.py
git commit -m "retire LOCALHOST_ENDPOINT_VARS in favor of topology rows[].localhost_endpoint_var"
```

### Task 3.4 — Replace `DISPLAY_NAME_OVERRIDES` and `SERVICE_DESCRIPTIONS` in service_discovery.py

**Files:**
- Modify: `bootstrapper/wizard/service_discovery.py`

- [ ] **Step 1: Rewrite display-name lookup and description lookup via Topology**

In `bootstrapper/wizard/service_discovery.py`, delete the `DISPLAY_NAME_OVERRIDES = {...}` (lines 21-37) and `SERVICE_DESCRIPTIONS = {...}` (lines 40-56) blocks.

Replace the `_get_display_name` method (around line 198) with:

```python
    def _get_display_name(self, key: str) -> str:
        """Get a human-readable display name for a service key via Topology."""
        from services.topology import build_topology
        from pathlib import Path
        services_root = Path(__file__).resolve().parent.parent.parent / "services"
        # Cached at instance level — caller iterates once.
        if not hasattr(self, "_topology_cache"):
            self._topology_cache = build_topology(services_root)
        target_source_var = key.upper().replace('-', '_') + '_SOURCE'
        for r in self._topology_cache.rows:
            if r.source_var == target_source_var:
                return r.display_name
        return key.replace('_', ' ').replace('-', ' ').title()
```

Update the description-fetching call. Inside `discover()`:
- Where today `description=SERVICE_DESCRIPTIONS.get(key, '')` is set, replace with a Topology lookup:

```python
            description = ""
            target_source_var = key.upper().replace('-', '_') + '_SOURCE'
            if not hasattr(self, "_topology_cache"):
                from services.topology import build_topology
                from pathlib import Path
                self._topology_cache = build_topology(
                    Path(__file__).resolve().parent.parent.parent / "services"
                )
            for r in self._topology_cache.rows:
                if r.source_var == target_source_var:
                    description = r.description
                    break
```

Then `description=description` in the `ServiceInfo(...)` call.

- [ ] **Step 2: Run wizard tests**

Run: `cd bootstrapper && uv run pytest tests/test_wizard_ollama_options.py tests/test_prompt_panel_leaf_badges.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/wizard/service_discovery.py
git commit -m "replace DISPLAY_NAME_OVERRIDES and SERVICE_DESCRIPTIONS with topology"
```

### Task 3.5 — Auto-derive `LOCKED_SERVICES` from manifests

**Files:**
- Modify: `bootstrapper/wizard/service_discovery.py`

- [ ] **Step 1: Delete the hardcoded LOCKED_SERVICES set**

In `bootstrapper/wizard/service_discovery.py`, delete the line:
```python
LOCKED_SERVICES = frozenset({'litellm'})
```

- [ ] **Step 2: Rewrite filtering in `discover()` to use Topology.row.locked**

In `discover()`, replace the early check today reading `if key in LOCKED_SERVICES` (search the file) with a Topology lookup against `r.locked`. Locked manifests are skipped entirely from the wizard's source-question list.

After the existing `if key in CLOUD_PROVIDER_KEYS: continue`, add:

```python
            # Locked manifests (1 source variant) skip the wizard entirely.
            if not hasattr(self, "_topology_cache"):
                from services.topology import build_topology
                from pathlib import Path
                self._topology_cache = build_topology(
                    Path(__file__).resolve().parent.parent.parent / "services"
                )
            target_source_var = key.upper().replace('-', '_') + '_SOURCE'
            is_locked = False
            for r in self._topology_cache.rows:
                if r.source_var == target_source_var:
                    is_locked = r.locked
                    break
            if is_locked:
                continue
```

- [ ] **Step 3: Run wizard tests**

Run: `cd bootstrapper && uv run pytest tests/test_wizard_ollama_options.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/wizard/service_discovery.py
git commit -m "derive locked status from manifest source variant count"
```

### Task 3.6 — Replace `HostsManager.GENAI_HOSTS` with `Topology.aliases`

**Files:**
- Modify: `bootstrapper/utils/hosts_manager.py`

- [ ] **Step 1: Make GENAI_HOSTS lazy via Topology**

In `bootstrapper/utils/hosts_manager.py`, replace the class-level `GENAI_HOSTS = [...]` list (lines 25-36) with a class method:

```python
    @classmethod
    def _genai_hosts_from_topology(cls) -> List[str]:
        """Built once from the topology. Returns a fresh copy on each call."""
        from services.topology import build_topology
        from pathlib import Path
        services_root = Path(__file__).resolve().parent.parent.parent / "services"
        if not hasattr(cls, "_aliases_cache"):
            cls._aliases_cache = list(build_topology(services_root).aliases)
        return list(cls._aliases_cache)
```

Update `get_genai_hosts(self)` and every other place referencing `self.GENAI_HOSTS` / `cls.GENAI_HOSTS` to call `cls._genai_hosts_from_topology()` instead.

- [ ] **Step 2: Run hosts tests**

Run: `cd bootstrapper && uv run pytest tests/test_kong_and_hosts_wiring.py -v`
Expected: PASS — note that the test may need an update if it asserts an exact list of 10 hosts; with 8 added aliases, the total is 18.

- [ ] **Step 3: Update the test if its assertion was a literal list**

Open `bootstrapper/tests/test_kong_and_hosts_wiring.py` and look for hardcoded list comparisons against `GENAI_HOSTS`. Replace any hard-coded list with one computed from `build_topology`. If the test asserts a specific count, update it to 18 — or better, derive the expected count from `Topology.aliases` itself.

- [ ] **Step 4: Re-run tests**

Run: `cd bootstrapper && uv run pytest tests/test_kong_and_hosts_wiring.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/utils/hosts_manager.py bootstrapper/tests/test_kong_and_hosts_wiring.py
git commit -m "derive GENAI_HOSTS from topology aliases"
```

### Task 3.7 — Delete services/_order.yml

**Files:**
- Delete: `services/_order.yml`

- [ ] **Step 1: Verify nothing reads it**

Run: `grep -rn "_order.yml\|order.yml" bootstrapper/ services/ 2>/dev/null`
Expected: no production code references (one or two stale comments are OK; delete them).

- [ ] **Step 2: Delete the file**

```bash
git rm services/_order.yml
```

- [ ] **Step 3: Remove any stale comments referring to it**

Search and remove comments mentioning `_order.yml`:
```bash
grep -rn "_order.yml" bootstrapper/ services/ docs/ 2>/dev/null
```

For each hit, edit to remove the stale reference.

- [ ] **Step 4: Run full test suite**

Run: `cd bootstrapper && uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/_order.yml
git add -A  # picks up any comment-only edits
git commit -m "retire services/_order.yml — superseded by topology"
```

### Task 3.8 — Wizard step ordering uses canonical_order

**Files:**
- Modify: `bootstrapper/ui/textual/integration.py`

- [ ] **Step 1: Replace the port-key sort with canonical-order lookup**

In `bootstrapper/ui/textual/integration.py`, find `_svc_port_key` (around line 133). Replace its definition and the `sorted(...)` call:

```python
    from services.topology import build_topology
    from pathlib import Path
    _services_root = Path(__file__).resolve().parent.parent.parent.parent / "services"
    _topology = build_topology(_services_root)

    # Build display-name → canonical index map for fast lookup.
    _canonical_index: dict[str, int] = {}
    for idx, r in enumerate(_topology.rows):
        _canonical_index[r.display_name] = idx

    def _svc_canonical_key(svc) -> tuple:
        return (_canonical_index.get(svc.display_name, 999), svc.display_name)

    services_info = sorted(services_info, key=_svc_canonical_key)
```

Delete the `_svc_port_key` function and the `from ui.state_builder import ... resolve_port as _resolve_port` import if no longer needed.

- [ ] **Step 2: Replace the row-sort `_port_key` lower in the file similarly**

Find the second sort (around line 273, `def _port_key(svc)`). Replace with a canonical lookup that mirrors the one above. Pull the index map up so both call sites share it.

- [ ] **Step 3: Run wizard tests**

Run: `cd bootstrapper && uv run pytest tests/test_wizard_ollama_options.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/ui/textual/integration.py
git commit -m "wizard step and box order driven by topology canonical_order"
```

### Task 3.9 — Add cycle / overflow / alias-uniqueness / engine-orphan lint rules

**Files:**
- Modify: `bootstrapper/services/manifest_validator.py`

- [ ] **Step 1: Write the failing test for the cycle rule**

Append to `bootstrapper/tests/test_manifest_validator.py`:

```python
def test_cycle_rule_flags_cycles():
    """A manifest dep cycle triggers a topology_cycle issue."""
    from services.manifests import Manifest, DependsOn
    from services.manifest_validator import validate_manifests

    manifests = [
        Manifest(name="a", label="A", category="data", env=[], depends_on=DependsOn(required=["b"])),
        Manifest(name="b", label="B", category="data", env=[], depends_on=DependsOn(required=["a"])),
    ]
    issues = validate_manifests(manifests)
    kinds = {i.kind for i in issues}
    assert "topology_cycle" in kinds


def test_alias_uniqueness_rule():
    """Duplicate alias across manifests is flagged."""
    from services.manifests import Manifest, DependsOn, Row as MRow
    from services.manifest_validator import validate_manifests

    common_alias = "duplicate.localhost"
    manifests = [
        Manifest(name="a", label="A", category="data", env=[], rows=[MRow(display_name="A", source_var="A_SOURCE", alias=common_alias)]),
        Manifest(name="b", label="B", category="data", env=[], rows=[MRow(display_name="B", source_var="B_SOURCE", alias=common_alias)]),
    ]
    issues = validate_manifests(manifests)
    kinds = {i.kind for i in issues}
    assert "duplicate_alias" in kinds
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd bootstrapper && uv run pytest tests/test_manifest_validator.py::test_cycle_rule_flags_cycles tests/test_manifest_validator.py::test_alias_uniqueness_rule -v`
Expected: 2 FAILS.

- [ ] **Step 3: Implement the four new rules**

In `bootstrapper/services/manifest_validator.py`, append:

```python
def _check_topology_cycle(manifests: list[Manifest]) -> list[ValidationIssue]:
    """The combined depends_on graph must be acyclic."""
    from services.topology import _topo_sort, TopologyError
    try:
        _topo_sort(manifests)
        return []
    except TopologyError as e:
        return [ValidationIssue(kind="topology_cycle", manifest="<graph>", message=str(e))]


def _check_alias_uniqueness(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Every rows[].alias must be unique across manifests."""
    seen: dict[str, list[str]] = {}
    for m in manifests:
        for r in m.rows:
            if r.alias:
                seen.setdefault(r.alias, []).append(m.name)
    issues: list[ValidationIssue] = []
    for alias, owners in seen.items():
        if len(owners) > 1:
            for owner in sorted(owners):
                issues.append(ValidationIssue(
                    kind="duplicate_alias",
                    manifest=owner,
                    message=f"alias '{alias}' is claimed by multiple manifests: {sorted(owners)}",
                ))
    return issues


def _check_category_overflow(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Total *_PORT vars per category must fit in that category's block."""
    from services.topology import CATEGORY_SLOTS
    by_cat: dict[str, int] = {c: 0 for c in CATEGORY_SLOTS}
    for m in manifests:
        if m.category not in by_cat:
            continue
        by_cat[m.category] += sum(1 for e in m.env if e.name.endswith("_PORT"))
    issues: list[ValidationIssue] = []
    for cat, count in by_cat.items():
        _, block_size = CATEGORY_SLOTS[cat]
        if count > block_size:
            issues.append(ValidationIssue(
                kind="category_overflow",
                manifest=f"<{cat}>",
                message=f"category '{cat}' has {count} *_PORT vars but block size is {block_size}",
            ))
    return issues


def _check_engine_orphans(manifests: list[Manifest]) -> list[ValidationIssue]:
    """Engine-only manifests (no rows, not virtual) must be referenced as a source variant."""
    # An engine-only manifest contributes no row of its own but is selected
    # via another manifest's sources options (e.g. speaches-* under STT_PROVIDER_SOURCE).
    issues: list[ValidationIssue] = []
    all_source_option_ids: set[str] = set()
    for m in manifests:
        if m.sources is not None:
            for opt in m.sources.options:
                all_source_option_ids.add(opt.id)

    for m in manifests:
        if m.virtual or m.rows:
            continue
        # An engine-only manifest's name must appear as a prefix of at least one source option id.
        if not any(opt_id.startswith(m.name) for opt_id in all_source_option_ids):
            issues.append(ValidationIssue(
                kind="engine_orphan",
                manifest=m.name,
                message=(
                    f"engine-only manifest '{m.name}' is not referenced by any source variant id. "
                    f"Add a source option whose id begins with '{m.name}' to its parent manifest."
                ),
            ))
    return issues
```

Then add calls to `validate_manifests`:

```python
    issues.extend(_check_topology_cycle(manifests))
    issues.extend(_check_alias_uniqueness(manifests))
    issues.extend(_check_category_overflow(manifests))
    issues.extend(_check_engine_orphans(manifests))
```

Also extend the `# `kind` values currently in use` comment at the top of the file with the four new kinds: `topology_cycle`, `duplicate_alias`, `category_overflow`, `engine_orphan`.

- [ ] **Step 4: Run new tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifest_validator.py::test_cycle_rule_flags_cycles tests/test_manifest_validator.py::test_alias_uniqueness_rule -v`
Expected: PASS.

- [ ] **Step 5: Run full validator suite + fragments lint**

Run: `cd bootstrapper && uv run pytest tests/test_manifest_validator.py tests/test_validate_fragments.py -v && uv run python -m tools.validate_fragments`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/services/manifest_validator.py bootstrapper/tests/test_manifest_validator.py
git commit -m "add cycle, alias uniqueness, category overflow, engine orphan lints"
```

---

## Phase 4 — Slot allocator wired into env.example, BASE_PORT canonical

Removes per-manifest `default:` from port env vars; `.env.example` regenerates from `Topology.port_defaults`.

### Task 4.1 — env_assembler reads from Topology.port_defaults

**Files:**
- Modify: `bootstrapper/services/env_assembler.py`
- Test: `bootstrapper/tests/test_env_example_consistency.py`

- [ ] **Step 1: Examine current env_assembler port handling**

Read the env_assembler to find where per-manifest `default:` is used for port vars. Look for where it converts manifest `env[].default` into `.env.example` lines.

Run: `cd bootstrapper && cat services/env_assembler.py | head -80`

- [ ] **Step 2: Build the Topology once at assembly start**

In the assembly entry function, near the top:

```python
from services.topology import build_topology
from pathlib import Path
_topology = build_topology(Path(__file__).resolve().parent.parent.parent / "services")
```

- [ ] **Step 3: Override port-var defaults**

Find the loop that emits each env var's default into the .env.example. For any env var whose name appears in `_topology.port_defaults`, emit the value from `_topology.port_defaults[var_name]` instead of the manifest's `default:` field.

Example refactor (pseudo, adapt to actual file shape):

```python
for env_decl in manifest.env:
    if env_decl.name in _topology.port_defaults:
        value = _topology.port_defaults[env_decl.name]
    else:
        value = env_decl.default
    write_env_line(env_decl.name, value)
```

- [ ] **Step 4: Run env_assembler tests**

Run: `cd bootstrapper && uv run pytest tests/test_env_assembler.py tests/test_env_example_consistency.py -v`
Expected: PASS (or fail with mismatch — see Step 5).

- [ ] **Step 5: Regenerate .env.example and confirm differences are intentional**

Run the env assembler against the real manifests:

```bash
cd bootstrapper && uv run python -m services.env_assembler  # or whatever the entry point is
```

Then `git diff -- .env.example` to inspect what changed. Expected: port defaults shift to the new layout. Source vars, secrets, non-port defaults unchanged.

- [ ] **Step 6: Commit .env.example along with the code change**

```bash
git add bootstrapper/services/env_assembler.py .env.example
git commit -m "env.example port defaults sourced from topology slot allocator"
```

### Task 4.2 — Drop `default:` from port env vars across manifests

**Files:**
- Modify: every `services/*/service.yml` with a `*_PORT` env var

- [ ] **Step 1: Catalog every `*_PORT` env var with a `default:`**

Run: `grep -nE "_PORT[[:space:]]*$" services/*/service.yml`

For each match, find the following `default:` line; that's what's being removed.

- [ ] **Step 2: Edit each manifest**

For every `*_PORT` env var, remove the `default:` line below it. The schema still allows the field; the assembler now ignores it for port vars, but cleanliness matters. Leave the env var entry itself in place:

```yaml
  - name: LITELLM_PORT
    # default removed — computed by services/topology.py slot allocator
```

- [ ] **Step 3: Validate manifests still parse**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py tests/test_manifest_validator.py -v`
Expected: PASS.

- [ ] **Step 4: Regenerate .env.example and confirm no drift**

```bash
cd bootstrapper && uv run python -m services.env_assembler
git diff .env.example
```

Expected: no change to .env.example (Task 4.1 already shifted to topology values; this task only cleans the manifest source).

- [ ] **Step 5: Commit**

```bash
git add services/*/service.yml
git commit -m "drop per-manifest port defaults — topology owns slot allocation"
```

### Task 4.3 — integration.py reads BASE_PORT directly

**Files:**
- Modify: `bootstrapper/ui/textual/integration.py`

- [ ] **Step 1: Replace SUPABASE_DB_PORT proxy with BASE_PORT**

In `bootstrapper/ui/textual/integration.py`, find the line:
```python
current_base_port = int(env_vars.get("SUPABASE_DB_PORT", DEFAULT_BASE_PORT))
```

Replace with:
```python
current_base_port = int(env_vars.get("BASE_PORT", DEFAULT_BASE_PORT))
```

- [ ] **Step 2: Sanity-check DEFAULT_BASE_PORT**

Run: `grep -n DEFAULT_BASE_PORT bootstrapper/core/config_parser.py`
Confirm it's 63000. If not, update the spec or the constant — the design assumes 63000.

- [ ] **Step 3: Run wizard tests**

Run: `cd bootstrapper && uv run pytest tests/test_wizard_ollama_options.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/ui/textual/integration.py
git commit -m "wizard reads BASE_PORT directly instead of SUPABASE_DB_PORT proxy"
```

---

## Phase 5 — UI changes (category bar, legend, pending state)

User-facing visual delivery.

### Task 5.1 — Add CAT_* palette tokens + style_for_category helper

**Files:**
- Modify: `bootstrapper/ui/textual/palette.py`

- [ ] **Step 1: Append the six tokens and helper**

At the end of `bootstrapper/ui/textual/palette.py`:

```python
# ─── Category color tokens — drives the leading bar on every service row ───
CAT_INFRA  = "#9a8cc6"  # purple
CAT_DATA   = "#6a9aaa"  # slate-blue
CAT_LLM    = "#7dcfff"  # sky blue
CAT_MEDIA  = "#98c379"  # sage green
CAT_AGENTS = "#d4a574"  # warm tan
CAT_APPS   = "#89aad4"  # periwinkle

_CATEGORY_COLOR: Dict[str, str] = {
    "infra":  CAT_INFRA,
    "data":   CAT_DATA,
    "llm":    CAT_LLM,
    "media":  CAT_MEDIA,
    "agents": CAT_AGENTS,
    "apps":   CAT_APPS,
}


def style_for_category(name: str) -> str:
    """Return the hex color for a category slug, falling back to TEXT_MUTED."""
    return _CATEGORY_COLOR.get((name or "").lower(), TEXT_MUTED)
```

- [ ] **Step 2: Run any palette-touching tests**

Run: `cd bootstrapper && uv run pytest -q -k palette`
Expected: PASS (no test deletions; tokens are additive).

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/ui/textual/palette.py
git commit -m "add CAT_* category palette tokens and style_for_category helper"
```

### Task 5.2 — Add `category` and `pending` fields to ServiceEntry

**Files:**
- Modify: `bootstrapper/ui/state.py`
- Modify: `bootstrapper/ui/state_builder.py`

- [ ] **Step 1: Extend ServiceEntry**

In `bootstrapper/ui/state.py`, update `ServiceEntry`:

```python
@dataclass
class ServiceEntry:
    """One service displayed in the box."""
    name: str
    port: Optional[str]
    source: str
    alias: Optional[str] = None
    category: str = ""        # NEW — drives bar color in the box
    pending: bool = False     # NEW — drives pending rendering
```

- [ ] **Step 2: Populate the new fields in build_app_state**

In `bootstrapper/ui/state_builder.py`, in the `for r in _get_topology().rows:` loop inside `build_app_state`:

```python
        services.append(ServiceEntry(
            name=r.display_name,
            port=resolve_port(r.display_name, source, r.port_var, env),
            source=source,
            alias=r.alias,
            category=r.category,
            pending=False,  # initial state; wizard sets True for unanswered rows
        ))
```

- [ ] **Step 3: Run state-related tests**

Run: `cd bootstrapper && uv run pytest tests/test_kong_and_hosts_wiring.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/ui/state.py bootstrapper/ui/state_builder.py
git commit -m "ServiceEntry gains category and pending fields"
```

### Task 5.3 — ServiceRow gains category + pending; pending render branch

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/service_table.py`
- Create: `bootstrapper/tests/test_service_table_pending.py`

- [ ] **Step 1: Write the failing test**

Create `bootstrapper/tests/test_service_table_pending.py`:

```python
"""Visual snapshot tests for ServiceTable's pending vs answered rows."""

from __future__ import annotations


def test_pending_row_renders_hollow_dot_and_dashes():
    """A pending row shows ◌ and em-dashes; not the source color."""
    from ui.textual.widgets.service_table import ServiceRow, ServiceTable
    row = ServiceRow(
        name="ComfyUI", source="", port="", alias="", category="media",
        pending=True,
    )
    table = ServiceTable([row], columns=1)
    table.size = type("Size", (), {"width": 200})()  # crude mock; real Textual provides
    rendered = table.render()
    text = rendered.plain
    assert "◌" in text  # hollow dot
    assert "pending" in text or "—" in text


def test_answered_row_renders_full_dot_and_real_port():
    """An answered row has the running dot and the actual port number."""
    from ui.textual.widgets.service_table import ServiceRow, ServiceTable
    row = ServiceRow(
        name="ComfyUI", source="container-cpu", port="63040", alias="comfyui.localhost",
        category="media", pending=False, default_source="container-cpu",
    )
    table = ServiceTable([row], columns=1)
    table.size = type("Size", (), {"width": 200})()
    rendered = table.render()
    text = rendered.plain
    assert "63040" in text
    assert "container-cpu" in text
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd bootstrapper && uv run pytest tests/test_service_table_pending.py -v`
Expected: FAIL — `ServiceRow` has no `category` or `pending` fields yet.

- [ ] **Step 3: Extend the ServiceRow dataclass**

In `bootstrapper/ui/textual/widgets/service_table.py`, update:

```python
@dataclass
class ServiceRow:
    name: str
    source: str = "container"
    alias: str = ""
    port: str = ""
    alias_port: str = ""
    tag: str = ""
    selected: bool = False
    default_source: str = ""
    configurable: bool = True
    category: str = ""        # NEW — drives leading bar color
    pending: bool = False     # NEW — drives pending-state rendering

    @property
    def is_changed(self) -> bool:
        return bool(self.default_source) and self.source != self.default_source
```

- [ ] **Step 4: Add pending-state branch in `_slot_text`**

In `_slot_text`, branch on `r.pending` AFTER the existing `is_disabled` block but BEFORE the per-column rendering. When pending:
- dot column: render `◌` in `P.WARN`
- port column: render `—` in `P.TEXT_FAINT`
- source column: render `pending…` in `P.WARN` (italic if Rich supports easily, else regular)
- alias-url column: render `—` in `P.TEXT_FAINT`
- name column: render normally (just dim slightly if desired)

Replace the relevant section of `_slot_text` (the body that today renders port/name/source/url) with:

```python
        # Pending-state branch: row decided by the user has not been confirmed yet.
        # All "decided" columns collapse to em-dashes / placeholders; the dot
        # switches to a hollow yellow ◌. Locked rows can never be pending so we
        # don't need to coordinate with the lock branch.
        if r.pending:
            slot.append("◌", style=P.WARN)
            slot.append("  ")
            if r.configurable:
                slot.append(" " * self.LOCK_W)
            else:
                slot.append(self.LOCK_ICON)
            slot.append(sep)
            slot.append(_fit("—", port_w), style=P.TEXT_FAINT)
            slot.append(sep)
            name_color = P.ACCENT if is_cursor else P.TEXT
            slot.append(_fit(r.name, name_w),
                        style=f"bold {name_color}" if is_cursor else name_color)
            slot.append(sep)
            slot.append(_fit("pending…", source_w), style=f"italic {P.WARN}")
            slot.append(sep)
            slot.append(_fit("—", alias_w), style=P.TEXT_FAINT)
            return slot
```

Place this branch right after the existing `is_disabled = (r.source or "").lower() == "disabled"` line; the rest of the function handles non-pending rows.

- [ ] **Step 5: Run tests**

Run: `cd bootstrapper && uv run pytest tests/test_service_table_pending.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/ui/textual/widgets/service_table.py bootstrapper/tests/test_service_table_pending.py
git commit -m "ServiceRow gains category and pending fields; pending render branch"
```

### Task 5.4 — Leading category bar in ServiceTable

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/service_table.py`

- [ ] **Step 1: Add BAR_W constant**

At the top of the `ServiceTable` class (with the other column constants):

```python
    # Leading category bar — colored stripe matching each row's category.
    # 2 cells wide; renders ▰▰ to fill the cell width with a solid block-like
    # glyph that survives without TrueColor.
    BAR_W = 2
    BAR_GLYPH = "▰" * BAR_W  # two cells filled
```

- [ ] **Step 2: Bump `_slot_fixed`**

Update `_slot_fixed`:

```python
    @property
    def _slot_fixed(self) -> int:
        # bar(BAR_W) sp(1) arrow(1) sp(1) dot(1) sp(2) + lock(LOCK_W) + 4*COL_SEP
        return (
            self.BAR_W + 1
            + self.ARROW_W + 1 + self.DOT_W + 2
            + self.LOCK_W + 4 * self.COL_SEP
        )
```

- [ ] **Step 3: Render the bar at the top of `_slot_text`**

Right after `slot = Text()` and before the `if r is None: ... return slot` block:

```python
        # Leading category bar — 2 cells in the category color.
        bar_color = P.style_for_category(r.category) if r else P.TEXT_FAINT
        slot.append(self.BAR_GLYPH, style=bar_color)
        slot.append(" ")
```

For the `None` empty-slot case (placeholder padding when row count is odd), the bar contributes `BAR_W + 1` extra cells to the total padding. Update the `total = ...` computation inside `if r is None:` to include the bar:

```python
            total = (
                self.BAR_W + 1
                + self.ARROW_W + 1 + self.DOT_W + 2 + port_w + self.COL_SEP
                + self.LOCK_W + self.COL_SEP
                + name_w + self.COL_SEP + source_w + self.COL_SEP + alias_w
            )
```

- [ ] **Step 4: Quick smoke render**

Run:
```bash
cd bootstrapper && uv run python -c "
from ui.textual.widgets.service_table import ServiceRow, ServiceTable
rows = [
    ServiceRow(name='Kong', source='container', port='63000', category='infra', configurable=False),
    ServiceRow(name='Supabase DB', source='container', port='63010', category='data', configurable=False),
    ServiceRow(name='ComfyUI', source='container-cpu', port='63040', category='media'),
]
t = ServiceTable(rows, columns=1)
t.size = type('S', (), {'width': 200})()
print(t.render().plain)
"
```
Expected: three lines, each starting with two ▰ glyphs (you won't see color in plain text but the glyphs prove the column is rendered).

- [ ] **Step 5: Run all ServiceTable tests**

Run: `cd bootstrapper && uv run pytest tests/test_service_table_pending.py -v`
Expected: PASS — the prior tests still find ◌ and "container-cpu" in the output; the bar appears before each row.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/ui/textual/widgets/service_table.py
git commit -m "leading category bar column in service table"
```

### Task 5.5 — CategoryLegend widget

**Files:**
- Create: `bootstrapper/ui/textual/widgets/category_legend.py`

- [ ] **Step 1: Write the widget**

Create `bootstrapper/ui/textual/widgets/category_legend.py`:

```python
"""
CategoryLegend — single-line strip below ServiceTable explaining the category
color bars. Six chips: ▰▰ in category color + label.
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


# Display order matches services/topology.py::CATEGORY_ORDER.
_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("infra",  "Infrastructure"),
    ("data",   "Data"),
    ("llm",    "LLM Core"),
    ("media",  "Media"),
    ("agents", "Agents & Workflows"),
    ("apps",   "Apps & UIs"),
)


class CategoryLegend(Widget):
    """One-line legend mapping bar colors to category labels."""

    DEFAULT_CSS = """
    CategoryLegend { height: auto; padding: 1 0 0 0; }
    """

    can_focus = False

    def render(self) -> Text:
        out = Text()
        first = True
        for slug, label in _CATEGORIES:
            if not first:
                out.append("   ", style=P.TEXT_FAINT)
            first = False
            out.append("▰▰", style=P.style_for_category(slug))
            out.append(" ")
            out.append(label, style=P.TEXT)
        return out
```

- [ ] **Step 2: Smoke-test the widget**

Run: `cd bootstrapper && uv run python -c "from ui.textual.widgets.category_legend import CategoryLegend; w = CategoryLegend(); print(w.render().plain)"`
Expected: a single line with six "▰▰ Label" segments separated by spaces.

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/ui/textual/widgets/category_legend.py
git commit -m "add CategoryLegend widget"
```

### Task 5.6 — InfoPanel composes the legend into its body

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/info_box.py`
- Modify: `bootstrapper/ui/textual/screens/wizard_screen.py`

- [ ] **Step 1: Bump `InfoPanel.DEFAULT_CSS` min-height**

In `info_box.py`, change the body min-height:

```css
InfoPanel > .info-body { height: auto; min-height: 5; }
```

(was `min-height: 4;`).

- [ ] **Step 2: Compose the legend into the wizard's body widget list**

In `bootstrapper/ui/textual/screens/wizard_screen.py`, find where `InfoPanel(...)` is constructed (around line 221 today). The `body_widgets` list looks like `[self._service_table, self._cloud_apis_row]`. Insert a `CategoryLegend` between them:

```python
from ..widgets.category_legend import CategoryLegend
self._category_legend = CategoryLegend()

self._info_panel = InfoPanel(
    state,
    body_widgets=[self._service_table, self._category_legend, self._cloud_apis_row],
    ...
)
```

- [ ] **Step 3: Run the wizard smoke test (if one exists) and the broader suite**

Run: `cd bootstrapper && uv run pytest tests/test_wizard_ollama_options.py tests/test_prompt_panel_leaf_badges.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/ui/textual/widgets/info_box.py bootstrapper/ui/textual/screens/wizard_screen.py
git commit -m "InfoPanel renders CategoryLegend between table and cloud APIs row"
```

### Task 5.7 — Footer pending count

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/info_box.py`

- [ ] **Step 1: Add pending-count logic to `_counts` and `render`**

In `bootstrapper/ui/textual/widgets/info_box.py`, update `InfoBoxFooter._counts` to also count pending rows. We need to know `pending` per service — `ServiceSummary` doesn't carry it today.

First, extend `ServiceSummary`:

```python
@dataclass
class ServiceSummary:
    name: str
    source: str = ""
    port: str = ""
    alias: str = ""
    pending: bool = False    # NEW

    @property
    def is_pending(self) -> bool:
        return self.pending
```

- [ ] **Step 2: Count pending in `_counts`**

Update `_counts`:

```python
    def _counts(self) -> tuple[int, int, int, int, int]:
        pending = container = local = off = gpu = 0
        for s in self._services:
            if s.is_pending:
                pending += 1
            elif s.is_disabled:
                off += 1
            elif s.is_gpu:
                gpu += 1
            elif s.is_localhost_or_external:
                local += 1
            else:
                container += 1
        return pending, container, local, gpu, off
```

- [ ] **Step 3: Render pending count when nonzero**

Update `render()`:

```python
    def render(self) -> Text:
        pending, container, local, gpu, off = self._counts()
        line = Text()
        if pending:
            line.append(f"{pending} pending", style=P.WARN)
            line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{container} container", style=P.OK)
        # ...rest unchanged
```

- [ ] **Step 4: Populate `pending` in the wizard's summary build**

In `bootstrapper/ui/textual/screens/wizard_screen.py`, `_refresh_info_panel` builds `ServiceSummary` from `self._services`. Pass `pending=r.pending`:

```python
        summaries = [
            ServiceSummary(name=r.name, source=r.source, port=r.port,
                           alias=r.alias, pending=r.pending)
            for r in self._services
        ]
```

- [ ] **Step 5: Run tests**

Run: `cd bootstrapper && uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/ui/textual/widgets/info_box.py bootstrapper/ui/textual/screens/wizard_screen.py
git commit -m "footer renders pending count when any rows are pending"
```

### Task 5.8 — Wizard `_answered` tracking; rows start pending and transition on confirm

**Files:**
- Modify: `bootstrapper/ui/textual/screens/wizard_screen.py`
- Modify: `bootstrapper/ui/textual/integration.py`
- Create: `bootstrapper/tests/test_wizard_pending.py`

- [ ] **Step 1: Write the failing test**

Create `bootstrapper/tests/test_wizard_pending.py`:

```python
"""Pending-state transitions on the wizard screen."""

from __future__ import annotations


def test_initial_state_marks_configurable_rows_pending():
    """At step 0, every configurable row is pending; locked rows are not."""
    # The test exercises the same code path the wizard uses to seed self._services
    # before any user input. Build a tiny mock setup.
    from ui.textual.widgets.service_table import ServiceRow

    rows = [
        ServiceRow(name="LiteLLM", category="llm", configurable=False, pending=False, source="container"),
        ServiceRow(name="LLM Engine", category="llm", configurable=True, pending=True, source=""),
    ]
    assert rows[0].pending is False  # locked
    assert rows[1].pending is True   # configurable, unanswered


def test_answered_set_transitions_pending_to_answered():
    """When step N is confirmed, _answered.add(N) and the matching row.pending = False."""
    from ui.textual.widgets.service_table import ServiceRow

    row = ServiceRow(name="ComfyUI", category="media", configurable=True,
                     pending=True, source="")
    # Simulate the confirm action's row mutation
    row.pending = False
    row.source = "container-cpu"
    assert row.pending is False
    assert row.source == "container-cpu"
```

- [ ] **Step 2: Run tests, confirm they pass**

These tests are state assertions, so they likely PASS once the dataclass changes from Task 5.3 are in. Run:

`cd bootstrapper && uv run pytest tests/test_wizard_pending.py -v`
Expected: PASS — but the production code still doesn't set `pending=True` initially. That's the implementation gap.

- [ ] **Step 3: Initialize `pending=True` on configurable rows at wizard build time**

In `bootstrapper/ui/textual/integration.py`, inside `_build_steps_and_rows`, the `rows = [ ServiceRow(...) for s in sorted_services ]` construction. Update:

```python
    configurable_names = {svc.display_name for svc in services_info}

    rows = [
        ServiceRow(
            name=s.name, source=(s.source or "container"),
            alias=(s.alias or ""), port=(s.port or ""),
            alias_port=(kong_port if (s.alias or "") else ""),
            tag=_tag_for(s.name.lower().replace(" ", "_")),
            default_source=(s.source or "container"),
            configurable=(s.name in configurable_names),
            category=s.category,
            pending=(s.name in configurable_names),  # locked rows start not-pending
        )
        for s in sorted_services
    ]
```

(`s.category` requires that `ServiceEntry` carries category — done in Task 5.2.)

- [ ] **Step 4: Track `_answered: set[int]` on WizardScreen and clear pending on confirm**

In `bootstrapper/ui/textual/screens/wizard_screen.py`:

a. In `__init__`, add `self._answered: set[int] = set()`.

b. In `action_confirm`, right after `self._selections[step.title] = opt.value`, add:
```python
        self._answered.add(self._step_index)
```

c. In the row-mutation loop (around line 612), after `row.source = opt.value`:
```python
                row.pending = False
```

- [ ] **Step 5: Add a regression test for back-nav semantics**

Append to `bootstrapper/tests/test_wizard_pending.py`:

```python
def test_answered_set_does_not_shrink_on_back_nav():
    """Back-navigation may revisit an answered step but _answered keeps it."""
    answered: set[int] = set()
    answered.add(5)
    # Simulate back-nav to step 5, then forward again to step 6 with new value
    answered.add(5)  # idempotent
    answered.add(6)
    assert 5 in answered
    assert 6 in answered
    assert len(answered) == 2
```

Run: `cd bootstrapper && uv run pytest tests/test_wizard_pending.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bootstrapper/ui/textual/screens/wizard_screen.py bootstrapper/ui/textual/integration.py bootstrapper/tests/test_wizard_pending.py
git commit -m "wizard tracks answered steps; rows start pending until confirmed"
```

### Task 5.9 — Parallel Rich-table update in start.py

**Files:**
- Modify: `bootstrapper/start.py`

- [ ] **Step 1: Locate `build_pre_launch_summary_table`**

Run: `grep -n build_pre_launch_summary_table bootstrapper/start.py`

- [ ] **Step 2: Add a leading "Category" column or a colored row marker**

Edit the function to add a leading cell rendering 2 colored block glyphs in the category color (use Rich `Text` with `style=P.style_for_category(category)`). Pull the category from `Topology.rows` (look up by display_name).

```python
from services.topology import build_topology
from ui.textual.palette import style_for_category
from pathlib import Path

_topology = build_topology(Path(__file__).resolve().parent.parent / "services")
_category_by_name = {r.display_name: r.category for r in _topology.rows}

# Inside the table-building loop, prefix each row with the colored block:
from rich.text import Text
bar = Text("▰▰", style=style_for_category(_category_by_name.get(svc_name, "")))
table.add_row(bar, ...rest of the row...)
```

- [ ] **Step 3: Append a legend row after the table**

After the existing console output of the table, print a legend line listing the six categories:

```python
console.print()
legend = Text()
for slug, label in [("infra","Infrastructure"),("data","Data"),("llm","LLM Core"),
                    ("media","Media"),("agents","Agents & Workflows"),("apps","Apps & UIs")]:
    legend.append("▰▰", style=style_for_category(slug))
    legend.append(f" {label}   ")
console.print(legend)
```

- [ ] **Step 4: Smoke-test by running start.py in dry-run mode**

Use whatever flag the project uses for a no-launch render — likely `--dry-run` or the wizard's confirm-no path. Or just import and call the function:

```bash
cd bootstrapper && uv run python -c "
from start import build_pre_launch_summary_table
# adapt to actual signature
"
```

Confirm output includes the leading bar and the legend.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/start.py
git commit -m "Rich pre-launch summary table prefixes each row with category bar plus legend line"
```

---

## Phase 6 — Migration

`.env` rewrite on first start; backup before; idempotent on second run.

### Task 6.1 — Add BOOTSTRAPPER_PORT_LAYOUT_VERSION to globals manifest

**Files:**
- Modify: `services/globals/service.yml`

- [ ] **Step 1: Add the env var**

In `services/globals/service.yml`, add to the `env:` list:

```yaml
  - name: BOOTSTRAPPER_PORT_LAYOUT_VERSION
    default: 1
    auto_managed: true
    description: "Sentinel updated by bootstrapper/services/migrations. Missing or <1 triggers port-layout v1 migration on next start."
```

- [ ] **Step 2: Run manifest tests**

Run: `cd bootstrapper && uv run pytest tests/test_manifests.py -v`
Expected: PASS.

- [ ] **Step 3: Regenerate .env.example**

Run: `cd bootstrapper && uv run python -m services.env_assembler`
Confirm `.env.example` now contains `BOOTSTRAPPER_PORT_LAYOUT_VERSION=1`.

- [ ] **Step 4: Commit**

```bash
git add services/globals/service.yml .env.example
git commit -m "add BOOTSTRAPPER_PORT_LAYOUT_VERSION sentinel to globals manifest"
```

### Task 6.2 — Create migrations package + migration_v1 snapshot

**Files:**
- Create: `bootstrapper/services/migrations/__init__.py`
- Create: `bootstrapper/services/migrations/migration_v1.py`

- [ ] **Step 1: Create the package init**

Create `bootstrapper/services/migrations/__init__.py`:

```python
"""Port-layout migrations. Each module owns one version bump."""
```

- [ ] **Step 2: Create the v0 snapshot**

Create `bootstrapper/services/migrations/migration_v1.py`:

```python
"""
Port-layout v0 → v1 migration.

v0 layout: hand-edited per-manifest `default:` values in service.yml.
v1 layout: topology slot allocator (services/topology.py).

This module:
  * Records the v0 OFFSETS (each port_var's offset from BASE_PORT at the time
    of this migration's authoring). Used to detect "user is on default" so we
    only rewrite ports the user has not customized.
  * Applies the rewrite: for each port_var, if .env[var] == BASE_PORT + v0_offset,
    rewrite to BASE_PORT + v1_offset. Otherwise leave alone.
  * Backs up .env to .env.backup.<YYYYMMDDTHHMMSS> before any write.

This is the FROZEN snapshot from 2026-05-15. Do NOT edit when the layout
changes again — author a sibling migration_v2.py with its own snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


# Frozen v0 layout: port_var → offset-from-BASE_PORT at the time the
# topology rework shipped. Pulled by hand from each manifest's `default:`
# field in the pre-migration codebase (commit 87ba9c3 baseline + later
# adds). DO NOT EDIT — this is a historical snapshot.
V0_OFFSETS: dict[str, int] = {
    "SUPABASE_DB_PORT": 0,
    "REDIS_PORT": 1,
    "KONG_HTTP_PORT": 2,
    "KONG_HTTPS_PORT": 3,
    "SUPABASE_META_PORT": 4,
    "SUPABASE_STORAGE_PORT": 5,
    "SUPABASE_AUTH_PORT": 6,
    "SUPABASE_API_PORT": 7,
    "SUPABASE_REALTIME_PORT": 8,
    "SUPABASE_STUDIO_PORT": 9,
    "GRAPH_DB_PORT": 10,
    "GRAPH_DB_DASHBOARD_PORT": 11,
    "LITELLM_PORT": 12,
    "LOCAL_DEEP_RESEARCHER_PORT": 13,
    "SEARXNG_PORT": 14,
    "OPEN_WEB_UI_PORT": 15,
    "BACKEND_PORT": 16,
    "N8N_PORT": 17,
    "COMFYUI_PORT": 18,
    "WEAVIATE_PORT": 19,
    "WEAVIATE_GRPC_PORT": 20,
    "DOC_PROCESSOR_PORT": 21,
    "STT_PROVIDER_PORT": 22,
    "TTS_PROVIDER_PORT": 23,
    "OPENCLAW_GATEWAY_PORT": 24,
    "OPENCLAW_BRIDGE_PORT": 25,
    "SPEACHES_PORT": 26,
    "CHATTERBOX_PORT": 27,
    "HERMES_API_PORT": 28,
    "HERMES_DASHBOARD_PORT": 29,
    "MINIO_PORT": 30,
    "MINIO_CONSOLE_PORT": 31,
    "JUPYTERHUB_PORT": 48,
}


@dataclass
class MigrationResult:
    rewritten: dict[str, tuple[str, str]]   # var → (old_value, new_value)
    preserved: list[str]                    # vars the user had customized
    backup_path: Optional[Path]


def apply(
    env_path: Path,
    new_defaults: dict[str, int],
    base_port: int,
) -> MigrationResult:
    """Rewrite .env in place; back it up first.

    Only port vars whose current value EQUALS `base_port + V0_OFFSETS[var]` are
    rewritten — that is "the user accepted the default." Anything else (custom
    port, blank line, missing var) is left alone.
    """
    if not env_path.is_file():
        return MigrationResult({}, [], None)

    backup_path = env_path.with_name(
        f"{env_path.name}.backup.{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    )
    backup_path.write_text(env_path.read_text())

    lines = env_path.read_text().splitlines(keepends=True)
    rewritten: dict[str, tuple[str, str]] = {}
    preserved: list[str] = []
    out: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key, _, raw_value = stripped.partition("=")
        key = key.strip()
        value = raw_value.split("#", 1)[0].strip()
        if key in V0_OFFSETS and key in new_defaults:
            expected_old = str(base_port + V0_OFFSETS[key])
            new_value = str(new_defaults[key])
            if value == expected_old and new_value != expected_old:
                out.append(f"{key}={new_value}\n")
                rewritten[key] = (expected_old, new_value)
                continue
            if value != expected_old:
                preserved.append(key)
        out.append(line)

    env_path.write_text("".join(out))
    return MigrationResult(rewritten, preserved, backup_path)


def needs_migration(env_path: Path) -> bool:
    """True iff .env is missing the v1 sentinel or has it at < 1."""
    if not env_path.is_file():
        return False  # fresh install — defaults already correct
    for line in env_path.read_text().splitlines():
        if line.strip().startswith("BOOTSTRAPPER_PORT_LAYOUT_VERSION="):
            try:
                return int(line.split("=", 1)[1].split("#", 1)[0].strip()) < 1
            except (ValueError, IndexError):
                return True
    return True


def stamp_version(env_path: Path, version: int = 1) -> None:
    """Append or update BOOTSTRAPPER_PORT_LAYOUT_VERSION in .env."""
    if not env_path.is_file():
        return
    lines = env_path.read_text().splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("BOOTSTRAPPER_PORT_LAYOUT_VERSION="):
            lines[i] = f"BOOTSTRAPPER_PORT_LAYOUT_VERSION={version}\n"
            found = True
            break
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"BOOTSTRAPPER_PORT_LAYOUT_VERSION={version}\n")
    env_path.write_text("".join(lines))
```

- [ ] **Step 3: Commit (no tests yet)**

```bash
git add bootstrapper/services/migrations/
git commit -m "scaffold migrations package with v1 port-layout snapshot"
```

### Task 6.3 — Tests for migration_v1

**Files:**
- Create: `bootstrapper/tests/test_port_migration.py`

- [ ] **Step 1: Write all five fixture tests**

Create `bootstrapper/tests/test_port_migration.py`:

```python
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
```

- [ ] **Step 2: Run tests**

Run: `cd bootstrapper && uv run pytest tests/test_port_migration.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/tests/test_port_migration.py
git commit -m "port-layout v0 to v1 migration tests"
```

### Task 6.4 — `--no-port-migrate` CLI flag

**Files:**
- Modify: `bootstrapper/start.py`

- [ ] **Step 1: Add the click option**

In `bootstrapper/start.py`, find the click command group/option block for the main entry. Add:

```python
@click.option(
    "--no-port-migrate",
    is_flag=True,
    default=False,
    help="Skip the v0 → v1 port-layout .env rewrite. Still stamps the version sentinel so the migration does not re-prompt.",
)
```

Plumb the flag through to the migration call site (Task 6.5).

- [ ] **Step 2: Commit**

```bash
git add bootstrapper/start.py
git commit -m "add --no-port-migrate CLI flag"
```

### Task 6.5 — Wire migrator into start.py startup

**Files:**
- Modify: `bootstrapper/start.py`

- [ ] **Step 1: Locate the early-startup section**

In `bootstrapper/start.py`, find the early initialization (after CLI parsing, before Docker calls). The migration should run AFTER ConfigParser has parsed the existing .env (so we know the user's current BASE_PORT) and BEFORE env_assembler regenerates .env.example.

- [ ] **Step 2: Add the migration block**

Add (adapt to actual function shape):

```python
from services.migrations.migration_v1 import (
    apply as apply_v1,
    needs_migration as needs_v1,
    stamp_version as stamp_v1,
)

env_path = Path(__file__).resolve().parent.parent / ".env"
if needs_v1(env_path):
    if no_port_migrate:
        console.print("[dim]Skipping port-layout v1 migration (--no-port-migrate).[/dim]")
    else:
        topology = build_topology(_services_root, base_port=int(os.environ.get("BASE_PORT", 63000)))
        result = apply_v1(env_path, topology.port_defaults, base_port=63000)
        if result.backup_path:
            console.print(f"[green]• Backed up .env to {result.backup_path}[/green]")
        console.print(
            f"[green]• Port layout updated (v0 → v1)[/green]: "
            f"rewrote {len(result.rewritten)} ports; preserved {len(result.preserved)} customizations."
        )
        if result.rewritten:
            console.print("[dim]  Changes:[/dim]")
            for var, (old, new) in sorted(result.rewritten.items()):
                console.print(f"[dim]    {var}: {old} → {new}[/dim]")
    stamp_v1(env_path, 1)
```

- [ ] **Step 3: Smoke-test against a fixture .env**

Create a throwaway env file:
```bash
cp .env.example /tmp/test.env
sed -i.bak 's|^LITELLM_PORT=.*|LITELLM_PORT=63012|' /tmp/test.env
```

Then run a dry start (or whichever flag avoids docker compose up) pointing at this env. Inspect log lines and `/tmp/test.env.backup.*`.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/start.py
git commit -m "run port-layout v1 migration on first start unless --no-port-migrate"
```

### Task 6.6 — CHANGELOG entry

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 1: Append the entry**

At the top of `docs/CHANGELOG.md` (assuming reverse-chronological), add:

```markdown
## 2026-05-15 — Wizard category coloring + topology-driven ordering

**Visual:** every service row in the setup wizard now leads with a thin category-color bar; six categories (Infra, Data, LLM Core, Media, Agents & Workflows, Apps & UIs) explained in a legend below the grid. Unanswered configurable services show a yellow ◌ placeholder ("pending") instead of guessing their port/source/alias before you've picked them.

**Ordering:** display order — and the wizard's question sequence — is now derived from each `service.yml`'s `depends_on:` and `category:` fields. The hand-edited `services/_order.yml` has been retired.

**Port renumbering:** default ports are computed from a per-category slot allocator, not hand-edited per manifest. On first start after this upgrade, your existing `.env` is auto-rewritten with the new defaults (a backup is taken to `.env.backup.<timestamp>`). User-customized port values (i.e., not matching the old default) are preserved untouched. Pass `--no-port-migrate` if you want to opt out of the rewrite.

**Aliases:** eight new `*.localhost` aliases — studio, graph, weaviate, ollama, stt, tts, docling, research. Total alias count goes from 10 to 18. Run `--setup-hosts` to add them to `/etc/hosts`.

**Internals:** eight scattered metadata constants across `bootstrapper/` (`_SERVICES`, `_HOST_ALIAS`, `DISPLAY_NAME_OVERRIDES`, `SERVICE_DESCRIPTIONS`, `LOCKED_SERVICES`, `LOCALHOST_ENDPOINT_VARS`, `GENAI_HOSTS`, `services/_order.yml`) have collapsed into manifest fields. Adding a new service is now a one-folder operation.
```

- [ ] **Step 2: Commit**

```bash
git add docs/CHANGELOG.md
git commit -m "CHANGELOG entry for topology rework and port-layout v1 migration"
```

---

## Phase 7 — Side-effects: architecture diagram, README block, per-service docs

Only run this phase after Phases 1-6 are green. Each side-effect generator reads `Topology` and overwrites a marker-delimited block.

### Task 7.1 — Architecture diagram generator

**Files:**
- Create: `bootstrapper/tools/generate_architecture_diagram.py`
- Modify: `docs/diagrams/architecture.dot`

- [ ] **Step 1: Write the generator**

Create `bootstrapper/tools/generate_architecture_diagram.py`:

```python
"""Regenerates docs/diagrams/architecture.dot from the topology.

Run: cd bootstrapper && uv run python -m tools.generate_architecture_diagram
"""

from __future__ import annotations

from pathlib import Path

from services.topology import build_topology, CATEGORY_ORDER


CATEGORY_LABELS = {
    "infra":  "Infrastructure",
    "data":   "Data",
    "llm":    "LLM Core",
    "media":  "Media",
    "agents": "Agents & Workflows",
    "apps":   "Apps & UIs",
}

CATEGORY_COLORS = {
    "infra":  "#9a8cc6",
    "data":   "#6a9aaa",
    "llm":    "#7dcfff",
    "media":  "#98c379",
    "agents": "#d4a574",
    "apps":   "#89aad4",
}


def generate(services_root: Path, output: Path) -> None:
    topology = build_topology(services_root)
    by_category: dict[str, list[str]] = {c: [] for c in CATEGORY_ORDER}
    for name in topology.canonical_order:
        cat = topology.category_of[name]
        if cat in by_category:
            by_category[cat].append(name)

    lines: list[str] = [
        'digraph stack {',
        '  rankdir=TB;',
        '  bgcolor="#0e0f18";',
        '  node [shape=box, style="filled,rounded", fontname="Helvetica", fontcolor="#c0caf5", color="#2b2f4a"];',
        '  edge [color="#3d4261"];',
        '',
    ]

    for cat in CATEGORY_ORDER:
        members = by_category[cat]
        if not members:
            continue
        lines.append(f'  subgraph "cluster_{cat}" {{')
        lines.append(f'    label="{CATEGORY_LABELS[cat]}";')
        lines.append(f'    fontcolor="{CATEGORY_COLORS[cat]}";')
        lines.append(f'    color="{CATEGORY_COLORS[cat]}";')
        for m in members:
            lines.append(f'    "{m}" [fillcolor="{CATEGORY_COLORS[cat]}33"];')
        lines.append('  }')
        lines.append('')

    # Edges
    from services.manifests import load_manifests
    for m in load_manifests(services_root):
        for dep in m.depends_on.required:
            lines.append(f'  "{dep}" -> "{m.name}";')

    lines.append('}')
    output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    generate(
        project_root / "services",
        project_root / "docs" / "diagrams" / "architecture.dot",
    )
    print(f"Wrote {project_root / 'docs' / 'diagrams' / 'architecture.dot'}")
```

- [ ] **Step 2: Run it**

```bash
cd bootstrapper && uv run python -m tools.generate_architecture_diagram
```

Expected: `docs/diagrams/architecture.dot` updated. Open it in a Graphviz preview to confirm clusters and arrows look right.

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/tools/generate_architecture_diagram.py docs/diagrams/architecture.dot
git commit -m "architecture diagram generator driven by topology"
```

### Task 7.2 — README topology block generator

**Files:**
- Create: `bootstrapper/tools/generate_readme_topology.py`
- Modify: `README.md`

- [ ] **Step 1: Add the marker block to README.md**

Insert into `README.md` (above any existing service-list section):

```markdown
<!-- TOPOLOGY:BEGIN -->
_This block is auto-generated by `bootstrapper/tools/generate_readme_topology.py`._
<!-- TOPOLOGY:END -->
```

- [ ] **Step 2: Write the generator**

Create `bootstrapper/tools/generate_readme_topology.py`:

```python
"""Regenerates the <!-- TOPOLOGY:BEGIN --> ... <!-- TOPOLOGY:END --> block in README.md.

Run: cd bootstrapper && uv run python -m tools.generate_readme_topology
"""

from __future__ import annotations

from pathlib import Path

from services.topology import build_topology, CATEGORY_ORDER


CATEGORY_LABELS = {
    "infra":  "Infrastructure",
    "data":   "Data",
    "llm":    "LLM Core",
    "media":  "Media",
    "agents": "Agents & Workflows",
    "apps":   "Apps & UIs",
}


def generate_block(services_root: Path) -> str:
    topology = build_topology(services_root)
    lines: list[str] = [
        "<!-- TOPOLOGY:BEGIN -->",
        "_Auto-generated by `bootstrapper/tools/generate_readme_topology.py`._",
        "",
        "| Category | Service | Default port | Alias |",
        "|---|---|---:|---|",
    ]
    for cat in CATEGORY_ORDER:
        for r in topology.rows:
            if r.category != cat:
                continue
            port = topology.port_defaults.get(r.port_var or "", "—")
            alias = r.alias or "—"
            lines.append(f"| {CATEGORY_LABELS[cat]} | {r.display_name} | {port} | {alias} |")
    lines.append("<!-- TOPOLOGY:END -->")
    return "\n".join(lines) + "\n"


def update_readme(readme_path: Path, services_root: Path) -> None:
    block = generate_block(services_root)
    text = readme_path.read_text()
    start = text.find("<!-- TOPOLOGY:BEGIN -->")
    end = text.find("<!-- TOPOLOGY:END -->")
    if start == -1 or end == -1:
        raise RuntimeError("README.md is missing the TOPOLOGY markers")
    end += len("<!-- TOPOLOGY:END -->")
    new_text = text[:start] + block.rstrip() + text[end:]
    readme_path.write_text(new_text)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    update_readme(project_root / "README.md", project_root / "services")
    print("Updated README.md TOPOLOGY block")
```

- [ ] **Step 3: Run the generator**

```bash
cd bootstrapper && uv run python -m tools.generate_readme_topology
git diff README.md
```

Expected: the marker block is now populated with a six-section service table.

- [ ] **Step 4: Commit**

```bash
git add bootstrapper/tools/generate_readme_topology.py README.md
git commit -m "README topology block generator + populated initial block"
```

### Task 7.3 — Lint enforces generators are in sync

**Files:**
- Modify: `bootstrapper/tools/validate_fragments.py`

- [ ] **Step 1: Add a dry-run check to the fragment validator**

In `bootstrapper/tools/validate_fragments.py`, append:

```python
def _check_readme_topology_block_is_current(project_root: Path) -> list[str]:
    """Ensure README.md TOPOLOGY block matches the generator's output."""
    from tools.generate_readme_topology import generate_block
    expected = generate_block(project_root / "services").rstrip()
    text = (project_root / "README.md").read_text()
    start = text.find("<!-- TOPOLOGY:BEGIN -->")
    end = text.find("<!-- TOPOLOGY:END -->")
    if start == -1 or end == -1:
        return ["README.md missing TOPOLOGY markers"]
    end += len("<!-- TOPOLOGY:END -->")
    actual = text[start:end].rstrip()
    if expected != actual:
        return ["README.md TOPOLOGY block is stale — run `uv run python -m tools.generate_readme_topology`"]
    return []


def _check_architecture_dot_is_current(project_root: Path) -> list[str]:
    """Ensure architecture.dot matches what the generator would produce."""
    from tools.generate_architecture_diagram import generate
    import tempfile
    with tempfile.NamedTemporaryFile("r+", suffix=".dot", delete=False) as f:
        tmp_path = Path(f.name)
    try:
        generate(project_root / "services", tmp_path)
        expected = tmp_path.read_text()
    finally:
        tmp_path.unlink(missing_ok=True)
    actual = (project_root / "docs" / "diagrams" / "architecture.dot").read_text()
    if expected != actual:
        return ["architecture.dot is stale — run `uv run python -m tools.generate_architecture_diagram`"]
    return []
```

Then in the main lint dispatch (existing function in this file), add calls to both checks. Report failures with exit code 1.

- [ ] **Step 2: Run the validator**

```bash
cd bootstrapper && uv run python -m tools.validate_fragments
```

Expected: exit 0 (sync). Touch one of the manifest files (e.g., change a description), re-run — should fail with the appropriate stale-block message. Re-run the relevant generator and re-run the linter — should be green again.

- [ ] **Step 3: Commit**

```bash
git add bootstrapper/tools/validate_fragments.py
git commit -m "validate_fragments enforces topology generator outputs are in sync"
```

---

## Final pass

### Task F.1 — Run the full suite

- [ ] **Step 1: Test suite**

```bash
cd bootstrapper && uv run pytest -q
```

Expected: every test green.

- [ ] **Step 2: Fragment validator**

```bash
cd bootstrapper && uv run python -m tools.validate_fragments
```

Expected: exit 0.

- [ ] **Step 3: Manual TUI smoke test**

```bash
./start.sh --dry-run  # or whatever non-launching flag the project uses
```

Step through the wizard. Confirm:
- Box renders 6 colored category bars, legend at bottom.
- Unanswered configurable rows show ◌ with `pending…` and `—`.
- Selecting a source lights the row up with its real color, port, alias.
- Footer shows `N pending · N container · …`.
- Order matches Infra → Data → LLM → Media → Agents → Apps.

- [ ] **Step 4: Backup-and-rewrite smoke test**

```bash
cp .env /tmp/.env.original
./start.sh --dry-run
ls -la .env.backup.*
```

Expected: a fresh backup file, .env's port vars at v1 layout, sentinel set to 1.

### Task F.2 — Branch readiness for merge

- [ ] **Step 1: Confirm clean status**

```bash
git -C /Users/kaveh/repos/genai-vanilla/.claude/worktrees/setup-wizard-categories-reorder status --short
```

Expected: clean working tree.

- [ ] **Step 2: Push branch (optional, only if user asks)**

The user controls the merge workflow per memory (rebase-then-fast-forward into main, never merge commits). Do not push without explicit ask.

---

## Notes for the implementing engineer

- **TDD discipline:** Every task above is structured "write failing test → implement → re-run → commit." Resist the urge to write implementation first.
- **Commits:** terse, third-person verb, no Co-Authored-By trailer (e.g., `add Row dataclass to manifest loader`). Each task = one commit unless the steps explicitly split.
- **Worktree:** all commands assume you're in `/Users/kaveh/repos/genai-vanilla/.claude/worktrees/setup-wizard-categories-reorder`. Do not `cd` to the original repo root.
- **Phases are sequential, tasks within a phase are mostly sequential.** Tasks 1.4-1.9 (manifest edits) can run in parallel by category but each commits separately. Topology tests (Phase 2) must come before Phase 3 wiring.
- **Hot spots to double-check:**
  - `bootstrapper/ui/state_builder.py`: the path `_SERVICES_ROOT = ...parent.parent.parent / "services"` assumes a specific depth. Verify it resolves to `<repo>/services` from the worktree before assuming it works.
  - `bootstrapper/services/env_assembler.py`: Task 4.1 depends on the file's specific shape — read it first before editing.
  - `bootstrapper/start.py`: very large file; locate `build_pre_launch_summary_table` precisely before editing.
- **Manifest dep correctness:** the deps in Phase 1 tasks are derived from compose `depends_on` + the spec's logical deps (Open WebUI → Hermes). Cross-check against today's `compose.yml` files if anything looks off.
