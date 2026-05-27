# Design — Expand `docs/CONTRIBUTING-services.md` into a decision-driven service-addition runbook

**Status:** Implemented 2026-05-24 — see docs/CONTRIBUTING-services.md.
**Author:** Kaveh + Claude (audit + brainstorm session 2026-05-23 / 24)
**Target:** rewrite of `docs/CONTRIBUTING-services.md` (in place, expanding the existing 234-line file to ~600-750 lines).

---

## 1. Problem

The existing `docs/CONTRIBUTING-services.md` is **reference-style**: a terse 9-step "Adding a new service" list, plus a schema cheatsheet, plus validator/byte-equivalence/`_user`-overlay sections. It assumes the reader already knows *which* category to pick, *which* port slot they'll get, *how* `depends_on` interacts with topological order, and *when* a Python helper in `service_config.py` becomes necessary.

In practice, a contributor adding a new service has to make six discrete decisions before they can write the manifest, and the existing doc doesn't walk through any of them. The recent audit surfaced a representative example: the manifest `depends_on.required` lists were silently overloaded with display-ordering edges, and trimming them caused port reshuffles — a footgun nobody was warned about.

This spec proposes expanding the existing doc with **decision-driven walkthrough sections**, threaded with a single worked example (a fictional Qdrant vector-database addition), so a contributor can land the right shape on the first try.

## 2. Non-goals

- **Not** a from-scratch rewrite. The existing reference sections (schema cheatsheet, validator rules, byte-equivalence, `_user/` overlay, doc-only manifest fields) stay verbatim — they're already correct and concise.
- **Not** a duplicate of `bootstrapper/schemas/service.schema.json`. The schema remains the field-by-field reference; this doc links to it but doesn't repeat it.
- **Not** generic Docker / Compose tutorial material. Assumes the reader can read a `compose.yml`.
- **Not** a replacement for the per-service `services/<name>/README.md` files (those describe the service after it's added; this doc describes the *process* of adding it).

## 3. Target audience

Two readers, both contributors to genai-vanilla:

- **The seasoned maintainer** — wants to scan a 60-second checklist, jump straight to the one section they need (e.g. "how does port allocation work?"), and get back to coding.
- **The first-time contributor** — wants to read the whole walkthrough once, following the worked example end-to-end, and understand *why* each decision is made the way it is.

The TL;DR + decision-section structure serves both: skim the TL;DR, drill into a section when needed.

## 4. Document outline

Sections **bold** are new. Sections *italic* are existing, kept as-is (possibly reordered).

| # | Section | Status | Approx. size |
|---|---------|--------|--------------|
| 1 | **TL;DR — the 60-second checklist** | new | ~40 lines |
| 2 | **The six decisions you have to make** | new | ~25 lines (overview table) |
| 3 | **Decision 1 — Folder flavor: container, virtual, or doc-only** | extends existing "Folder flavors" | ~60 lines |
| 4 | **Decision 2 — Category** | new | ~70 lines |
| 5 | **Decision 3 — Source variants** | new | ~80 lines |
| 6 | **Decision 4 — Port allocation** | new | ~60 lines |
| 7 | **Decision 5 — Dependencies (`depends_on.required` / `optional`)** | new | ~100 lines (most nuanced) |
| 8 | **Decision 6 — Adaptive behavior + when to write a hook** | new | ~60 lines |
| 9 | **Mechanics — putting it all together** | new | ~90 lines (the full qdrant manifest + compose) |
| 10 | **After you save the files — regen + lint commands in order** | new | ~30 lines |
| 11 | **Audit-script + CI implications** | new | ~50 lines |
| 12 | **Common gotchas + anti-patterns** | new | ~80 lines |
| 13 | *Subdirectory naming convention* | kept verbatim | ~20 lines |
| 14 | *Modifying an existing service* + **Additional notes subsection** | mostly kept | ~30 lines |
| 15 | *Schema cheatsheet* | kept, with 1-line pointer prepended | ~70 lines |
| 16 | *Validator rules (what the lint catches)* | kept verbatim | ~12 lines |
| 17 | *Byte-equivalence* | kept verbatim | ~22 lines |
| 18 | *`services/_user/` overlay slot* | kept verbatim | ~30 lines |
| 19 | *Documentation-only manifest fields* | kept verbatim | ~18 lines |

**Total expansion:** existing 234 lines → ~870 lines. Despite the length, the doc is **scannable**: TL;DR up front, six clearly-labeled decision sections, one mechanics section, one gotchas appendix. Readers either skim the TL;DR or read one drill-down section.

## 5. Worked example: "Add Qdrant, a self-hosted vector DB, with container + localhost + external + disabled sources"

A single fictional service threaded through every decision section. Qdrant is real open-source software but **not currently in the stack** — Weaviate is the vector DB. This makes the example concrete (real product, real architecture) without confusing the reader about whether it's an actual proposal.

Each decision section shows the qdrant answer next to the rationale:

| Decision | Qdrant answer |
|----------|---------------|
| 1. Folder flavor | container (runs as a container, has env vars) |
| 2. Category | `data` (vector DB sibling to Weaviate, Supabase, Neo4j) |
| 3. Sources | container · localhost · external · disabled |
| 4. Port slot | auto-assigned: next free in the data block (`63010-63029` range) |
| 5. Dependencies | required: `[supabase]` (data-tier sibling, gives ordering); optional: `[]` |
| 6. Adaptive / hook | no hook needed — declarative `runtime_sc` covers all four sources |

The **Mechanics** section (#9) then renders the full `services/qdrant/service.yml` + `services/qdrant/compose.yml` resulting from these answers, with line-by-line callouts pointing back to the decision section that explains each choice.

## 6. Section-by-section content plan

### 6.1 TL;DR — the 60-second checklist (new)

A numbered punch list a maintainer can scan in under a minute. Each bullet links to the relevant deep-dive heading.

```
□ 1. Pick a folder flavor (Decision 1)
□ 2. Pick a category (Decision 2)
□ 3. Pick your sources (Decision 3)
□ 4. Write services/<name>/service.yml (mechanics §9)
□ 5. Write services/<name>/compose.yml IF folder flavor = container (mechanics §9)
□ 6. Add the include line to docker-compose.yml IF you wrote a compose fragment
□ 7. Run the four-command regen+lint chain (§10)
□ 8. Update audit-script allowlists IF your service has hard deps (§11)
□ 9. Commit; CI runs both the unit-test suite and the new docs-drift + audit-scripts gates
```

### 6.2 The six decisions you have to make (new)

A single overview table with the six rows, the "default answer" column for the easy case, and the section number to drill into:

| # | Decision | Default if you're unsure | Drill-down |
|---|----------|--------------------------|------------|
| 1 | Folder flavor | container | Decision 1 |
| 2 | Category | the category of the service you're most similar to | Decision 2 |
| 3 | Source variants | `container` + `disabled` (minimum); add `localhost` if users might run this themselves | Decision 3 |
| 4 | Port allocation | nothing — it's auto-assigned. Just declare `<NAME>_PORT` in the env block. | Decision 4 |
| 5 | Dependencies | the manifest of the closest sibling in your category, to preserve display order | Decision 5 |
| 6 | Adaptive / hooks | none — start with declarative `runtime_sc`, escalate to a Python helper only when YAML can't express it | Decision 6 |

### 6.3 Decision 1 — Folder flavor (extends existing section)

Already in the doc as "Folder flavors: container, virtual, doc-only" — added in the recent audit. **Keep the existing table.** Add:

- A short flowchart in prose: *Does this run as a container? → container. Does it own env vars / SOURCE toggles but with no compose fragment? → virtual. Is it a documentation-only aggregator for an existing role (like stt-provider)? → doc-only.*
- Worked example callout: "Qdrant runs as a container with its own image → container flavor."
- A reminder: virtual manifests **must** set `virtual: true` (the validator enforces it).

### 6.4 Decision 2 — Category (new)

The six categories with concrete examples:

| Category | Wizard block | Service examples in stack | When to pick |
|----------|--------------|---------------------------|--------------|
| `infra` | Infrastructure | Kong, globals | Gateways, project-wide config, observability |
| `data` | Data | Supabase, Redis, MinIO, Neo4j, Weaviate | Databases, caches, object storage |
| `llm` | LLM Core | LiteLLM, Ollama, cloud-providers | LLM gateways / engines |
| `media` | Media | ComfyUI, parakeet, speaches, chatterbox, docling, searxng, multi2vec-clip, tts-provider | Multimodal AI (image / audio / doc / search) |
| `agents` | Agents & Workflows | Hermes, n8n, openclaw | Programmable AI agents, workflow runners |
| `apps` | Apps & UIs | Backend, Open WebUI, JupyterHub, Local Deep Researcher | User-facing UIs |

Explains the two effects of the category:
- **Wizard placement** — categories render in fixed order (infra → data → llm → media → agents → apps), and within a category, services follow topological order.
- **Port-slot block** — each category gets a block of 10 port slots (`CATEGORY_SLOTS` constant in `topology.py`). Some categories are getting full — flag the current utilization.

Worked example callout: "Qdrant is a vector DB → sibling of Weaviate/Supabase/Neo4j → `data`."

### 6.5 Decision 3 — Source variants (new)

Explains the SOURCE pattern: every user-configurable service has an `<SVC>_SOURCE` env var with these standard options:

| Option | Meaning | When to offer it |
|--------|---------|------------------|
| `container` | Run as a Docker container alongside the stack | Always, for container-flavor services |
| `container-cpu` / `container-gpu` | Split when the container has CPU/GPU variants | When you publish a GPU variant of the image |
| `localhost` | Connect to a user-managed instance on the host | When users typically already have this software installed (e.g. Ollama, ComfyUI) |
| `external` | Connect to a remote URL | When users may point at a managed cloud version of this service |
| `api` | Use a hosted cloud API (no container) | LLM gateways only |
| `disabled` | Excluded from compose entirely | Always — every optional service must support this |
| `<engine>-*` | Engine-specific sub-variants | For aggregator services that pick from multiple engines (STT/TTS) |

Explains:
- **Locked vs. user-choice** — if a service has only one source variant, the wizard treats it as locked (no prompt). The Topology helper `_is_locked` enforces this.
- **`requires:`** — declare per-option env-var prerequisites (e.g. `external` requires `<SVC>_EXTERNAL_URL`).
- **`<SVC>_LOCALHOST_URL` symmetry rule** (from memory: don't add asymmetric overrides). If you add localhost support, both the compose `runtime_sc.<svc>.localhost.environment` AND the Kong route generator must read the same `<SVC>_LOCALHOST_URL` var. Otherwise Kong and in-container clients silently disagree.

Worked example callout: "Qdrant — most users won't already run it locally, but we offer all four: container · localhost · external · disabled. Localhost variant gets `QDRANT_LOCALHOST_URL` defaulting to `http://host.docker.internal:6333` (Qdrant's standard host port)."

### 6.6 Decision 4 — Port allocation (new)

The bootstrapper auto-assigns ports. **You do not pick a port.**

How it works:
- `BASE_PORT` (default 63000) is the bottom of the port range.
- `CATEGORY_SLOTS` in `bootstrapper/services/topology.py` assigns each category an offset + block size. Current values (cite the constant by name; numbers here are accurate as of 2026-05-24):

  | Category | Offset | Block size | Resolved range with default `BASE_PORT=63000` |
  |----------|-------:|-----------:|-----------------------------------------------|
  | `infra` | 0 | 10 | 63000-63009 |
  | `data` | 10 | 20 | 63010-63029 |
  | `llm` | 30 | 10 | 63030-63039 |
  | `media` | 40 | 20 | 63040-63059 |
  | `agents` | 60 | 20 | 63060-63079 |
  | `apps` | 80 | 20 | 63080-63099 |

- Within each category block, services consume slots in **topological order** (driven by `depends_on.required` — see Decision 5). Multi-port services (e.g. Supabase's 8 containers, Weaviate's HTTP + gRPC pair) get a contiguous run.
- A category-overflow lint trips if you blow past the block. The fix is moving manifests to a different category (rare) or extending the block size (also rare — coordinate with the maintainers).

How to declare:
- Add an env entry `name: <SVC>_PORT` with **no `default:` line** (the comment `# default removed — computed by services/topology.py slot allocator` is the convention).
- The assembler emits the resolved port into `.env.example` automatically when you run `python -m services.env_assembler`.

Worked example callout: "Qdrant declares `QDRANT_PORT` with no default. Topology slots it into the data block at the next free offset — depending on where it lands in the topo sort relative to its siblings (Supabase microservices, Redis, MinIO, Neo4j, Weaviate), today that's ~63024-63026. The exact number is auto-resolved at every regen; never hand-edit `.env.example`."

### 6.7 Decision 5 — Dependencies (most nuanced section, new)

The pivotal section. Explains the dual semantics of `depends_on.required`:

**Runtime semantics (intended):** "These services must be up before this one boots." Maps to compose `depends_on:` in your fragment.

**Display-ordering semantics (overloaded):** The bootstrapper uses `depends_on.required` as the canonical-order backbone for the wizard and overview box. Within a category, services sort topologically; an edge from A → B means A appears after B in the same category's wizard block.

**The footgun.** These two semantics get conflated. The audit found Kong's manifest listed 19 services in `required` because Kong **proxies** to them — but Kong doesn't need them to **boot**. Trimming Kong's list was correct. But the audit also found that trimming `litellm` from `ollama.depends_on.required` correctly removed a fake runtime edge — and broke a UI ordering test, because `ollama` was using the edge to pin its display position.

**Current convention** (codified in the manifest comments I wrote in commit `d98bc5a`):
- Use `required` for genuine bootstrap blockers AND for cross-category display-ordering pins.
- Comment any non-runtime edge inline as "encodes display ordering, not a runtime call."
- A future schema change may add a separate `display_order:` field; until then, comment the intent.

**Don't:**
- Don't list every service you *call* in `required`. Use `data_flow.calls` for that (it drives the architecture diagram, not topology).
- Don't depend on virtual aggregates (`globals`, `cloud-providers`) — they have no runtime presence.
- Don't list `optional` deps that compose doesn't enforce; they're documentation-only.

Worked example callout: "Qdrant's `depends_on.required = [supabase]` — Supabase is the data-tier substrate and listing it pins qdrant's position in the data block topologically. `optional = []`."

### 6.8 Decision 6 — Adaptive behavior + when to write a hook (new)

Most services can express their per-source behavior with declarative `runtime_sc` YAML:

```yaml
runtime_sc:
  qdrant:
    container:
      scale: 1
      environment: { QDRANT_LOG_LEVEL: info }
      deploy: {}
      extra_hosts: []
    localhost:
      scale: 0
      environment: { QDRANT_ENDPOINT: ${QDRANT_LOCALHOST_URL} }
      deploy: {}
      extra_hosts: [host.docker.internal:host-gateway]
    disabled:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []
```

You need a `_generate_<svc>_config()` Python helper in `bootstrapper/services/service_config.py` ONLY when:

- The output depends on **multiple** input SOURCE variables (e.g. `_generate_stt_provider_config` reads both `STT_PROVIDER_SOURCE` and `TTS_PROVIDER_SOURCE` to dedupe Speaches).
- The output depends on **derived state** (e.g. `_generate_cloud_providers_config` reads three `CLOUD_*_SOURCE` toggles + their API keys to compute `LITELLM_ENABLED_PROVIDERS`).
- You need to write env vars that depend on **another service's port** computed at runtime.

For everything else, stay declarative.

Worked example callout: "Qdrant — single SOURCE, no cross-service dependencies, no derived state → no hook needed."

### 6.9 Mechanics — putting it all together (new)

The full result of the six decisions, rendered as the two files you actually save:

**`services/qdrant/service.yml`** (annotated with `# ← Decision N` callouts on the relevant lines)

```yaml
# services/qdrant/service.yml — Qdrant vector database
name: qdrant
label: "Qdrant (vector database)"
category: data                                # ← Decision 2
docs: services/qdrant/README.md

containers:
  - qdrant

images:
  - var: QDRANT_IMAGE
    default: "qdrant/qdrant:v1.12.0"
    container: qdrant

sources:                                      # ← Decision 3
  var: QDRANT_SOURCE
  default: disabled                           #     (off by default; user opts in)
  options:
    - id: container
      label: "Container"
    - id: localhost
      label: "Host (existing Qdrant)"
    - id: external
      label: "External (custom URL)"
      requires: [QDRANT_EXTERNAL_URL]
    - id: disabled
      label: "Disabled"

env:
  - name: QDRANT_SOURCE
    default: disabled
  - name: QDRANT_PORT                         # ← Decision 4 (no default — auto-assigned)
  - name: QDRANT_LOCALHOST_URL
    default: "http://host.docker.internal:6333"
    description: "Used when QDRANT_SOURCE=localhost. Same var consumed by Kong's qdrant.localhost route."
  - name: QDRANT_EXTERNAL_URL
    default: ""
    description: "Required when QDRANT_SOURCE=external."
  - name: QDRANT_ENDPOINT
    auto_managed: true
  - name: QDRANT_SCALE
    auto_managed: true

depends_on:                                   # ← Decision 5
  required:
    - supabase
  optional: []

exports: []

rows:
  - display_name: "Qdrant"
    source_var: QDRANT_SOURCE
    port_var: QDRANT_PORT
    scale_var: QDRANT_SCALE
    alias: qdrant.localhost
    description: "Vector database (Qdrant)."
    localhost_endpoint_var: QDRANT_ENDPOINT

runtime_sc:                                   # ← Decision 6 (declarative, no hook)
  qdrant:
    container:
      scale: 1
      environment:
        QDRANT_ENDPOINT: http://qdrant:6333
      deploy: {}
      extra_hosts: []
    localhost:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ${QDRANT_LOCALHOST_URL}
      deploy: {}
      extra_hosts: [host.docker.internal:host-gateway]
    external:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ${QDRANT_EXTERNAL_URL}
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ''
      deploy: {}
      extra_hosts: []

data_flow:
  calls: []
```

**`services/qdrant/compose.yml`**

```yaml
# services/qdrant/compose.yml — Qdrant vector database
services:
  qdrant:
    image: ${QDRANT_IMAGE}
    container_name: ${PROJECT_NAME}-qdrant
    restart: unless-stopped
    deploy:
      replicas: ${QDRANT_SCALE:-0}
    ports:
      - "${QDRANT_PORT}:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    healthcheck:
      test: ["CMD", "wget", "-q", "-O-", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - backend-network

volumes:
  qdrant-data:
    name: ${PROJECT_NAME}-qdrant-data
    driver: local
```

Plus the one-line addition to `docker-compose.yml`'s `include:` block:

```yaml
  # Data tier
  - services/qdrant/compose.yml
```

### 6.10 After you save the files — regen + lint commands in order (new)

```bash
cd bootstrapper

# 1. Regenerate .env.example from manifests
uv run python -m services.env_assembler

# 2. Regenerate README.md TOPOLOGY block (auto-includes the new row)
uv run python -m tools.generate_readme_topology

# 3. Regenerate docs/diagrams/architecture.dot (+ run `dot -Tsvg` to refresh the SVG)
uv run python -m tools.generate_architecture_diagram
dot -Tsvg ../docs/diagrams/architecture.dot > ../docs/diagrams/architecture.svg

# 4. Lint — fails if any of the above were skipped
uv run python -m tools.validate_fragments

# 5. (Optional but recommended) Regen per-service docs for new manifests
PYTHONPATH=. python -m docs.regen qdrant   # creates services/qdrant/README.md + SVG + HTML
```

Note: the per-service README/SVG/HTML are auto-generated; you only need to commit them after the first regen. Future changes to `data_flow.calls` trigger them to regenerate via the docs-drift CI gate.

### 6.11 Audit-script + CI implications (new)

After adding a service, check:

**`scripts/check-compose-source-deps.py`** — has two allowlists:
- `REQUIRED_DEPENDS_ON` — add entries here if your service's compose fragment hard-depends on `litellm`, `redis`, `supabase-db`, `weaviate-init`, etc. The script will fail CI if your manifest claims a hard dep that the compose doesn't enforce, OR vice versa.
- `FORBIDDEN_OPTIONAL_DEPENDS_ON` — add entries here if you've intentionally added a depends_on to a SOURCE-replaceable service for some special reason.

**`scripts/check-kong-routes.py`** — if your service publishes a `*.localhost` alias, the generated Kong route gets baseline-default-checked. The script's allowlist needs an entry if your route uses any non-default settings (e.g. `preserve_host: True` for SPAs, custom plugin chain, etc.).

**`.github/dependabot.yml`** — if your service ships a `requirements.txt` / `pyproject.toml` in a `build/` or `provider/` subdirectory, add the path to the `directories:` list. Memory note: ALL active manifests must be enumerated; omitted paths drop from scan coverage.

**CI gates** that run on every push:
- `Manifest lint + unit tests` — runs `validate_fragments` + pytest.
- `Compose merge + byte-equivalence + source-permutation matrix` — verifies your manifest can render every source variant without breaking the merged compose.
- `Docs drift + audit scripts` — runs `regen --all --check` + the 5 audit scripts. Catches: stale per-service READMEs/SVGs/HTMLs, missing `REQUIRED_DEPENDS_ON` entries, Kong route default drift, internal-markdown-link rot, research-schema violations.

### 6.12 Common gotchas + anti-patterns (new)

Distilled from real audit findings (each entry cites the commit / memory it came from):

- **Cross-category `depends_on.required` is a display-order pin** — removing `litellm` from `ollama.required` is correct from a runtime POV but shifts the wizard's row order and reshuffles port slots in the media block. Keep cross-category edges and document the intent inline (see commits `d98bc5a`).
- **Don't depend on virtual aggregates in `required`** — `globals`, `cloud-providers`, `tts-provider` are virtual (no container, no compose). Depending on them adds a phantom node to the topo sort. Audit removed phantom `globals` edges from `supabase` and `docling`.
- **`<SVC>_LOCALHOST_URL` overrides must be symmetric** — if you read it in a new in-container consumer, Kong's route generator must read the same var too, otherwise the two paths silently disagree (memory: `feedback_localhost_url_override_symmetry`).
- **Init containers use vanilla `alpine:latest` + inline `apk add`** — don't ship a Dockerfile that builds a custom init image. Memory: `project_init_container_pattern` — the global tag gets clobbered if you do.
- **Compose-only deps vs. manifest deps go BOTH ways** — Kong's manifest listed 19 proxy targets in `required` but compose only had 5 (truly correct). Backend's manifest only listed `supabase, redis` but compose waited for `litellm` health (under-claimed). Audit corrected both; CI's `check-compose-source-deps.py` now catches missing edges.
- **Kong routes fronting browser SPAs need `preserve_host: True`** — otherwise the SPA emits unreachable redirect URLs containing the internal Docker hostname (memory: `reference_kong_preserve_host`).
- **TTS/STT engine in-container ports are NOT all 8000** — parakeet/speaches/docling = 8000, chatterbox = 4123. Don't assume (memory: `reference_tts_stt_engine_ports`).
- **`.env.example` is byte-equivalence-tested** — after any manifest change that affects env vars or port allocation, regen `.env.example` or `test_env_example_consistency` will fail CI.
- **`test_fragment_equivalence` is sensitive to Compose-version defaults** — don't regenerate the baseline reflexively; extend `_strip_volatile_defaults` instead (memory: `project_compose_baseline_test`).

### 6.13 Existing sections — kept verbatim

- *Subdirectory naming convention* (table of `app/`, `build/`, `init/`, etc.)
- *Modifying an existing service* (terse bullet list)
- *Schema cheatsheet* (full YAML template with field-by-field commentary)
- *Validator rules (what the lint catches)* (8 cross-manifest checks)
- *Byte-equivalence* (golden baseline + permutation matrix explanation)
- *`services/_user/` overlay slot* (downstream submodule consumers)
- *Documentation-only manifest fields* (`label`, `description`, `notes`, etc.)

### 6.14 Modifications subsection — new additions

Short walk-throughs for common modification flows that don't require the full "new service" runbook:

- **Adding a new source variant to an existing service** — add to `sources.options`, add a `runtime_sc.<key>.<new-source>` slice, regen `.env.example`. Watch out for: source-permutation matrix test in CI exercises every variant.
- **Renaming a service's display name (`rows[].display_name`)** — update the row, regen the README topology block, update any test that hardcodes the name (e.g. `test_wizard_app_discovery.EXPECTED_DISCOVERED`).
- **Bumping a container image version** — edit `images[].default` only; the compose fragment uses the var so nothing else changes.
- **Splitting a service family** — non-trivial; rare. Out of scope for this section; cite the supabase manifest as a reference for multi-container families.

## 7. Style + format conventions

- Each decision section: **rationale (~80-150 words)** → **worked example callout (qdrant snippet)** → **gotcha sidebar (where relevant)**.
- Code snippets use fenced ```yaml or ```bash blocks. No line numbers.
- Cross-references use heading text, not section numbers (recently codified convention).
- No emojis (the existing doc has none).
- Tables for enumerations (categories, source options, etc.). Prose for rationale.
- "Worked example" callouts visually distinct via blockquote (`>` prefix) so a reader can skip them and still get the rationale-only thread.

## 8. Risks + mitigations

| Risk | Mitigation |
|------|------------|
| Doc grows to 870 lines and becomes intimidating | TL;DR + decision-table at the top let readers skim; each decision is a self-contained drill-down |
| Worked example using "qdrant" might confuse readers into thinking it's a real proposal | Add a one-line note at the example's introduction: "Qdrant is real software but NOT currently in the stack — Weaviate is our vector DB. Used purely as an instructional example." |
| Section numbers in the existing reference half drift if a new decision section is added later | Convention already codified: cross-refs use heading text, not numbers (added in commit `80ad83e`) |
| `CATEGORY_SLOTS` numbers cited in the doc could go stale if the constant is edited | Cite the constant by name + file path (`CATEGORY_SLOTS` in `bootstrapper/services/topology.py`); show example numbers as "today's values" with a footnote pointer to the source |
| Worked-example YAML snippets could go stale if the schema evolves | Worked example is fully validatable by the schema; if schema changes, the qdrant snippets fail the lint and force a doc update |

## 9. Out of scope (deferred / explicit non-goals)

- Building qdrant as a real service in the stack.
- Splitting the doc into multiple files (decided: expand in place per user request).
- Replacing the schema cheatsheet with field-level docs (the schema JSON is authoritative).
- Visual diagrams of category placement / port slots (text tables are sufficient; can revisit later).
- Translating the doc to other languages.
- Auto-generation of the doc from manifests (the doc is human-curated guidance, not a manifest-derived artifact).

## 10. Acceptance criteria

The expanded doc is "done" when:

1. A new contributor can read it once and successfully add a fictional service end-to-end without asking for help.
2. The six decision sections each have a worked-example callout that names qdrant's specific answer.
3. The mechanics section's qdrant `service.yml` validates against `bootstrapper/schemas/service.schema.json`.
4. All cross-references resolve (no broken anchor links).
5. The existing reference sections (schema cheatsheet, validator rules, byte-equivalence, `_user/` overlay, doc-only manifest fields) remain in the doc, intact.
6. `python scripts/check_doc_links.py` exits 0 (no link rot introduced).
7. The doc passes a casual read-through without any obvious "TBD" or placeholder content.

## 11. Implementation order (preview — will be detailed by writing-plans)

1. Insert the TL;DR + six-decision-overview at the very top of the doc.
2. Insert the six Decision sections, one at a time, each with its worked-example callout.
3. Insert the Mechanics section (full qdrant snippets).
4. Insert the regen + lint commands section.
5. Insert the audit-script + CI implications section.
6. Insert the gotchas section.
7. Reorder the existing sections so the reference half flows at the end.
8. Add the cross-reference link from the existing "Adding a new service" 9-step list at the top to "see also: TL;DR".
9. Add the "Modifications — additional notes" subsection.
10. Final pass: run `check_doc_links.py` + read end-to-end once for narrative flow.
