# Wizard category coloring, topological ordering, and pending-state — design

Status: approved 2026-05-15
Author: Kaveh Razavi (with claude)

## Summary

Rework the setup wizard's stack overview box and the wizard step sequence so that:

1. Every service is bucketed into one of six categories with a stable color, rendered as a thin leading bar per row and explained by a legend.
2. Display order is **category-grouped, topologically sorted within category** — driven entirely by `depends_on:` declarations in each `service.yml`.
3. Default port numbers are computed from a per-category slot allocator (not hand-edited in manifests).
4. Box rows for configurable services that the user hasn't answered yet show a **pending** visual state: yellow hollow `◌` dot, port/source/alias hidden until the user picks.
5. Existing `.env` files are auto-migrated to the new port layout once, with a backup, on next start.
6. Eight scattered metadata constants in `bootstrapper/` collapse into manifest fields, making `service.yml` the single source of truth.

Side benefit: the architecture diagram, the README service table, and per-service docs can all generate from the same `Topology` object.

## Goals

- One canonical service order across the wizard box, the wizard's question sequence, `.env.example`, the architecture diagram, the README, and the per-service docs.
- Adding a new service is a one-folder operation (`services/<name>/service.yml`, `compose.yml`, plus a `depends_on:` line) — no edits to `_order.yml`, `_SERVICES`, `_HOST_ALIAS`, `DISPLAY_NAME_OVERRIDES`, `SERVICE_DESCRIPTIONS`, `LOCKED_SERVICES`, `LOCALHOST_ENDPOINT_VARS`, or `HostsManager.GENAI_HOSTS`.
- Wizard UX: never display a port, alias, or source-color for a service whose source the user hasn't picked yet.
- Migration: existing users see the new port layout on next start; their non-default customizations are preserved; backup is automatic.

## Non-goals

- Adding new services or new source variants.
- Changing how the bootstrapper assembles `docker-compose` fragments.
- Changing the cloud-provider (OpenAI/Anthropic/OpenRouter) wizard sub-step flow — it stays as today (spliced after LLM Engine).
- Adding aliases for TCP-only services (Postgres, Redis Bolt) — they can't be virtual-host routed.

## Categories and palette

| # | Category | Slug | Hex | Box rows |
|---|---|---|---|---|
| 1 | Infrastructure | `infra` | `#9a8cc6` | Kong API Gateway |
| 2 | Data | `data` | `#6a9aaa` | Supabase DB · Meta · Storage · Auth · API · Realtime · Studio · Redis · Neo4j Graph DB · MinIO · Weaviate |
| 3 | LLM Core | `llm` | `#7dcfff` | LiteLLM · LLM Engine (Ollama) |
| 4 | Media | `media` | `#98c379` | ComfyUI · STT Provider · TTS Provider · Document Processor · SearxNG |
| 5 | Agents & Workflows | `agents` | `#d4a574` | n8n · OpenClaw · Hermes Agent |
| 6 | Apps & UIs | `apps` | `#89aad4` | Backend API · Open WebUI · JupyterHub · Local Deep Researcher |

Display order top-to-bottom: `infra → data → llm → media → agents → apps`. Apps last because Open WebUI consumes Hermes Agent as a model (Apps depend on Agents).

Engine-only manifests (`speaches`, `chatterbox`) inherit their parent's category and don't render their own row; the user picks them as a source variant of the parent (STT/TTS Provider). Virtual manifests (`globals`, `cloud-providers`) are categorized for ordering and docs purposes but don't render as box rows.

## Manifest schema changes

`bootstrapper/schemas/service.schema.json` extended with three additions.

### `category:` — enum value change

Old: `data | llm | ai | app | infra`
New: `infra | data | llm | media | agents | apps`

Mappings applied across existing manifests:

| Manifest | Old | New |
|---|---|---|
| `kong`, `globals` | `infra` | `infra` (unchanged) |
| `supabase`, `redis`, `minio`, `neo4j` | `data` | `data` (unchanged) |
| `weaviate` | `ai` | `data` |
| `litellm`, `ollama`, `cloud-providers` | `llm` | `llm` (unchanged) |
| `comfyui`, `parakeet`, `tts-provider`, `speaches`, `chatterbox`, `docling` | `ai` | `media` |
| `searxng` | `app` | `media` |
| `hermes` | `ai` | `agents` |
| `n8n`, `openclaw` | `app` | `agents` |
| `backend`, `open-webui`, `jupyterhub`, `local-deep-researcher` | `app` | `apps` |

### `depends_on:` — reuses the existing schema field

Reuses the existing `depends_on.required` field from the schema (no new field is introduced):

```yaml
depends_on:
  required:
    - litellm     # manifest name (kebab-case)
    - supabase
  optional: []
```

Semantics: a logical dep edge. Includes both compose `depends_on` and "uses-at-runtime" deps not visible to Docker (e.g., Open WebUI → Hermes via LiteLLM model registration). Used by topology computation. Lint requires every name to resolve to a real manifest; lint requires the graph to be acyclic.

### `rows:` — new field

```yaml
rows:
  - display_name: "Supabase DB"
    source_var: SUPABASE_DB_SOURCE
    port_var: SUPABASE_DB_PORT
    description: "Postgres (always-on, container-only)"
    # no alias — TCP-only
  - display_name: "Supabase Studio"
    source_var: SUPABASE_STUDIO_SOURCE
    port_var: SUPABASE_STUDIO_PORT
    alias: studio.localhost
    description: "Browser UI for the database"
    localhost_endpoint_var: ""  # n/a for studio
```

One entry per box row. Most manifests have exactly one. Supabase has seven (one per HTTP-facing component). Each entry consolidates what was previously spread across `_SERVICES`, `_HOST_ALIAS`, `DISPLAY_NAME_OVERRIDES`, `SERVICE_DESCRIPTIONS`, and `LOCALHOST_ENDPOINT_VARS`.

Fields:
- `display_name` (required): human label shown in the box and in wizard prompts.
- `source_var` (required): the `*_SOURCE` env var driving this row's source pick.
- `port_var` (optional): the env var holding this row's primary display port. Omit for virtual rows.
- `scale_var` (optional): the `*_SCALE` env var. Absence ⇒ always-on (scale derived elsewhere).
- `alias` (optional): the `*.localhost` hostname Kong virtual-host-routes. Lint enforces uniqueness across all manifests.
- `description` (optional): one-line label used as wizard prompt subtitle.
- `localhost_endpoint_var` (optional): env var holding the URL when source is a localhost variant. Used to parse the display port out of e.g. `http://localhost:18188`.

### Per-port `default:` becomes optional/computed

Manifests stop declaring `default: 63012` for `*_PORT` env vars. The slot allocator computes those at startup and the `.env.example` generator writes the computed defaults. A manifest may still declare a `default:` as a hint, but the slot allocator overrides it.

### Retired modules and constants

| Path | Replacement |
|---|---|
| `services/_order.yml` | computed from `depends_on:` |
| `bootstrapper/ui/state_builder.py::_SERVICES` | manifest `rows:` |
| `bootstrapper/ui/state_builder.py::_HOST_ALIAS` | `rows[].alias` |
| `bootstrapper/wizard/service_discovery.py::DISPLAY_NAME_OVERRIDES` | `rows[].display_name` |
| `bootstrapper/wizard/service_discovery.py::SERVICE_DESCRIPTIONS` | `rows[].description` |
| `bootstrapper/wizard/service_discovery.py::LOCKED_SERVICES` | auto: a manifest with one source variant is locked |
| `bootstrapper/utils/endpoint_vars.py::LOCALHOST_ENDPOINT_VARS` | `rows[].localhost_endpoint_var` |
| `bootstrapper/utils/hosts_manager.py::HostsManager.GENAI_HOSTS` | computed from all `rows[].alias` |

## Topology engine

New module: `bootstrapper/services/topology.py`.

### Algorithm

1. Load every `services/*/service.yml`.
2. Build a directed graph with one edge `A → B` for each `B` in `A.depends_on`.
3. Topo-sort using Kahn's algorithm. Tiebreaker: lexicographic on manifest `name` for determinism.
4. Detect cycles → hard fail with the cycle path in the error message.
5. Partition by `category:`, preserving topo order within.
6. Concatenate in category display order: `infra → data → llm → media → agents → apps`. This is `canonical_order`.

### Slot allocator

Per-category slot blocks:

| Category | Base offset (from BASE_PORT) | Block size |
|---|---:|---:|
| Infra | 0 | 10 |
| Data | 10 | 20 |
| LLM Core | 30 | 10 |
| Media | 40 | 20 |
| Agents | 60 | 20 |
| Apps | 80 | 20 |

Total: 100 slots (BASE_PORT 63000 → 63099). Today's stack uses ~33; blocks sized for ~2× headroom.

For each manifest in canonical order, for each port var declared in its `env:` block in declaration order, assign `default = BASE_PORT + next_slot_in_category`. Virtual manifests consume no slots. Multi-port manifests get a contiguous run.

### BASE_PORT becomes the canonical anchor

Today, `bootstrapper/ui/textual/integration.py` reads `SUPABASE_DB_PORT` as a proxy for "current base port" because Supabase DB historically sat at BASE_PORT offset 0. With the new layout Supabase DB moves to slot 10 (BASE_PORT+10 = 63010 by default), and Kong HTTP takes BASE_PORT+0. The wizard's "Base port" step now reads and writes `BASE_PORT` directly — the single canonical anchor declared in `globals/service.yml`. Every other port var derives from `BASE_PORT + slot`.

### Exposed dataclass

```python
@dataclass(frozen=True)
class Row:
    manifest: str            # "supabase"
    display_name: str        # "Supabase Studio"
    source_var: str
    port_var: Optional[str]
    scale_var: Optional[str]
    alias: Optional[str]
    description: str
    localhost_endpoint_var: Optional[str]
    category: str            # "data"
    locked: bool             # True when manifest has 1 source variant

@dataclass(frozen=True)
class Topology:
    canonical_order: list[str]               # manifest names, display order
    category_of: dict[str, str]              # manifest → category slug
    port_defaults: dict[str, int]            # env var → computed default port
    rows: list[Row]                          # flat box-row list
    aliases: list[str]                       # *.localhost names, in canonical order
```

Every downstream consumer imports `Topology`.

### Determinism

Topo sort + lex tiebreak + manifest order is reproducible across machines. Two developers running the bootstrapper get identical port assignments. Adding a leaf service appends to its category's tail. Reordering deps can shift positions within a category but never across categories.

### Lint rules (in `tools/validate_fragments.py`)

- Every `depends_on:` name resolves to a real manifest.
- Combined dep graph is acyclic.
- Sum of `rows:` per category ≤ that category's slot block size.
- Every `alias:` is unique across manifests.
- Every compose `depends_on:` edge has a corresponding manifest `depends_on:` edge (compose deps are a subset of manifest deps).
- Engine-only manifests (no `rows:`, no virtual flag) must be referenced as a source variant of some other manifest's row.

## Wizard step ordering and pending state

### Step sequence

Built from `Topology.canonical_order`. Locked services are skipped (no source to pick). The LLM-cluster splice (Ollama variant step + Ollama models multiselect + cloud OpenAI/Anthropic/OpenRouter key+model pairs) keeps its current placement right after `LLM Engine`.

Final sequence with today's manifest set:

```
1. Base port range
2-4. Data configurables: Neo4j, MinIO, Weaviate
       (Supabase + Redis are locked — skipped)
5. LLM Engine source
   6-13. Spliced: Ollama variant → Ollama models → OpenAI key/models → Anthropic key/models → OpenRouter key/models
14-18. Media: ComfyUI, STT Provider, TTS Provider, Doc Processor, SearxNG
19-21. Agents: n8n, OpenClaw, Hermes
22-25. Apps: Backend, Open WebUI, JupyterHub, LDR
26. Cold start
27. Hosts setup
28. Confirm
```

### Per-row state machine

| State | When | Visual |
|---|---|---|
| `LOCKED` | manifest has 1 source variant | full port + source + alias from startup; 🔒 |
| `PENDING` | configurable, never confirmed | yellow `◌`, port `—`, source `pending…` italic, alias `—` |
| `IN_CURSOR` | current step targets this row | PENDING visual + cursor arrow `▸` |
| `ANSWERED` | step confirmed at least once | real source-color dot, real port, real alias |

Tracking lives on `WizardScreen` as `self._answered: set[int]`. Back-navigation does not revert a row to PENDING — the value is preserved; the cursor overlay alone signals "you can change this." Re-confirming an existing answer is idempotent.

### Live update on confirm (extends existing `action_confirm`)

1. `selections[step.title] = opt.value` (existing)
2. `_answered.add(self._step_index)` (new)
3. Find row by `service_name`, update `row.source`, re-derive `row.port` (existing)
4. Mark row state `PENDING → ANSWERED` (new; trivial since `_answered` is the source of truth)
5. Refresh `ServiceTable` + `InfoPanel` (existing)

### Locked detection at startup

A manifest with one source variant in its `sources:` block (or no `sources:` block with a single implicit `container` source) is locked. The wizard's `service_discovery.discover()` only emits steps for non-locked manifests. Locked rows render in the box from step 0 in their final state.

## Box rendering changes

### `service_table.py`

Three additions:

1. **Leading category bar.** A new 2-cell column at the start of every row, painted with the manifest's category hex. Per-slot layout:
   ```
   [bar 2][sep 1][cursor 1][dot 1][sp 2][lock 2][sep 2][port][sep 2][name][sep 2][source][sep 2][alias-url]
   ```
   `_slot_fixed` increases by 3 (bar + separator). At 2-col view the bar appears twice; at 1-col fallback, once.

2. **Pending-state branch.** When `row.pending`:
   - dot: hollow `◌` in `WARN`
   - port: `—` in `TEXT_FAINT`
   - source: `pending…` in `WARN` italic
   - alias-url: `—` in `TEXT_FAINT`
   - name: unchanged (legible, just no context yet)

3. **Sort method takes a `canonical_order` arg.** Replaces today's port-key sort.

### `category_legend.py` (new widget)

One-line horizontal strip of chips rendered below the `ServiceTable` inside `InfoPanel`'s body. Each chip: `▰` glyph in category hex + label. Six chips in display order. Collapses to two lines on narrow panels.

### `info_box.py`

`InfoPanel`'s body widgets become `[ServiceTable, CategoryLegend, CloudApisRow]`. `DEFAULT_CSS`'s `min-height` bumps `4` → `5`. The existing footer count line gains a leading `N pending` count during wizard mode (disappears once all rows answered).

### `palette.py`

Six new tokens: `CAT_INFRA`, `CAT_DATA`, `CAT_LLM`, `CAT_MEDIA`, `CAT_AGENTS`, `CAT_APPS` (hexes from the Categories table). Backwards-compat aliases keep the old `TAG_*` names. New helper `style_for_category(name)`.

### Data model

```python
@dataclass
class ServiceEntry:
    name: str
    port: Optional[str]
    source: str
    alias: Optional[str] = None
    category: str = ""        # NEW — drives bar color
    pending: bool = False     # NEW — drives pending rendering
```

`state_builder.build_app_state()` populates both from `Topology`.

### Parallel Rich-table update

`start.py::build_pre_launch_summary_table` (no-TUI fallback) gets the category bar (colored leading cell) and the legend row so both render paths match.

## Aliases — final set

Today (10): `litellm`, `minio`, `comfyui`, `openclaw`, `hermes`, `n8n`, `search` (SearxNG), `jupyter` (JupyterHub), `chat` (Open WebUI), `api` (Backend) — all `.localhost`.

Added (8): `studio` (Supabase Studio), `graph` (Neo4j Browser), `weaviate`, `ollama` (LLM Engine), `stt`, `tts`, `docling`, `research` (LDR) — all `.localhost`.

Final total: 18 `*.localhost` aliases. The `HostsManager.GENAI_HOSTS` constant is replaced by a derived list — `Topology.aliases`. Lint enforces uniqueness.

TCP-only services (Postgres in Supabase DB, Redis, Neo4j Bolt) get no alias — Kong virtual-host routing requires HTTP.

## Migration: .env rewrite with backup

### Sentinel

New env var `BOOTSTRAPPER_PORT_LAYOUT_VERSION` declared in `globals/service.yml`. Initial target value `1`. On startup, if the var is missing or `< 1`, the migration runs once. After the migration writes the version, future runs no-op.

### Backup

`.env.backup.<YYYYMMDDTHHMMSS>` adjacent to `.env`. Same pattern as `hosts_manager`'s hosts backup. Retention forever; user manages cleanup. Absolute path logged at startup.

### Rewrite policy — touch only ports that match the OLD default

```
For each port_var in old_layout:
    expected_old = current_BASE_PORT + old_layout[port_var]
    if env[port_var] == str(expected_old):
        env[port_var] = str(current_BASE_PORT + new_layout[port_var])
    else:
        keep as-is  (user customized — don't surprise them)
```

The old-layout snapshot lives in `bootstrapper/services/migrations/migration_v1.py` (contains the v0→v1 layout snapshot internally). Read once, never updated. Future migrations ship their own snapshots.

### Unchanged

`*_SOURCE` vars, API keys, secrets, non-port settings, /etc/hosts entries, Docker volumes, container data.

### Cascading regenerations (already part of every start)

- Kong dynamic config (`volumes/api/kong-dynamic.yml`) — regenerated by `kong_config_generator` from post-rewrite `.env`.
- LiteLLM config (`volumes/litellm/config.yaml`) — regenerated by `litellm_config_generator`.
- `.env.example` — regenerated by `env_assembler` from new manifest defaults.

### CLI override

`--no-port-migrate` skips the rewrite but still stamps the version sentinel.

### Logging at startup

```
• Port layout updated (v0 → v1: topology-driven slots)
• Backed up .env to .env.backup.20260515T120000
• Rewrote 17 port defaults; 3 user-customized ports preserved
  Set --no-port-migrate to skip future port migrations.
```

### Tests

Under `bootstrapper/tests/test_port_migration.py`:
- Fixture .env at all old defaults → every port rewrites, version stamped, backup created.
- Fixture .env with `LITELLM_PORT=54321` → that port preserved, others rewrite.
- Fixture .env already at version 1 → no-op, no backup.
- Fixture missing .env → migration skipped entirely (fresh install path).
- Idempotency: run twice → second run no-ops.

## Side-effects: architecture diagram, README, per-service docs

Once `Topology` exists, three places stop being hand-maintained:

1. **`docs/diagrams/architecture.dot`** — Graphviz source generator script walks `Topology`, emits one node per manifest (cluster-grouped by category, colored with the category hex), and one edge per `depends_on`. The diagram regenerates from the same source the wizard uses.

2. **`README.md` service list** — generated by a marker-block (`<!-- TOPOLOGY:BEGIN --> ... <!-- TOPOLOGY:END -->`) refreshed by a `make docs` target.

3. **Per-service README cross-links** at the bottom of each `docs/services/<name>.md`: "Depends on …", "Used by …", "Category: Data". Generated as footer blocks.

Lint fails if any of these are out of sync with what `Topology` would produce.

## Tests

New / extended test files under `bootstrapper/tests/`:

- `test_topology.py` — tiebreaker determinism, cycle detection, category overflow, alias uniqueness, lex sort of equal-rank nodes.
- `test_slot_allocator.py` — per-category block math, contiguous allocation per manifest, virtual-manifest skip.
- `test_port_migration.py` (covered above).
- `test_manifest_lint.py` extensions — every manifest declares `depends_on:` + at least one `rows:` (virtuals exempt).
- `test_wizard_pending.py` — pending → answered transitions, locked rows skip wizard, back-nav preserves `_answered`.
- `test_service_table_pending.py` — visual regression: snapshot of pending vs answered row rendering.

## Implementation phasing

Six phases, each independently shippable and revertable. `writing-plans` will refine step boundaries within each.

1. **Schema & manifests** — extend `service.schema.json`; add `depends_on:` + `rows:` to every manifest; rename `category:` values. Old constants stay. CI green.
2. **Topology module** — new `bootstrapper/services/topology.py`. No callers yet. Tests pass.
3. **Wire Topology into state/wizard** — replace `_SERVICES`, `_HOST_ALIAS`, `DISPLAY_NAME_OVERRIDES`, `SERVICE_DESCRIPTIONS`, `LOCALHOST_ENDPOINT_VARS`, `LOCKED_SERVICES`, `_order.yml`, `HostsManager.GENAI_HOSTS`. Old port defaults still come from manifests. Wizard sequence and box order now match canonical.
4. **Slot allocator + .env.example regen** — port defaults stop coming from per-manifest `default:` (those fields removed). `.env.example` regenerates from `Topology.port_defaults`. Existing `.env` files unaffected (runtime reads `.env` first).
5. **UI changes** — category bar, legend widget, pending state in `ServiceTable`, footer pending count, palette tokens, parallel Rich-table updates in `start.py`.
6. **Migration** — port-layout v1 sentinel, .env rewrite with backup, CLI flag, CHANGELOG, README note.

Phases 1-3 are pure refactor (no user-visible change). Phase 4 changes default values for new installs only. Phase 5 is the visual delivery. Phase 6 is the migration.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Manifest deps disagree with `compose.yml depends_on` | Lint: every compose `depends_on` edge is also a manifest edge (manifest may have additional logical edges). |
| Auto-renumbered port collides with a user's unrelated running process | Lint checks in-range collisions; migration log lists every changed port so the user can spot a clash. |
| Visual companion mockup colors look wrong in real Textual rendering | Phase 5 ships behind a Textual screenshot baseline test; iterate hex values before merge. |
| Engine-only manifests get orphaned in the dep graph | Lint: engine-only manifests must be referenced as a source variant of some row. |
| `cloud-providers` virtual manifest's deps | It depends on `litellm` (gateway-routed). Edge declared in its manifest. |
| Back-navigation breaks `_answered` semantics | Test covers forward → back → change → forward; `_answered` never shrinks; values mutate idempotently. |

## Rollback

Every phase is one PR. If phase 5 (UI) is unwell received, revert that PR alone — phases 1-4 leave the codebase architecturally cleaner regardless. The .env migration (phase 6) is reversible: `cp .env.backup.<ts> .env` plus deleting the version sentinel.
