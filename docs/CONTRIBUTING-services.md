# Contributing — adding or modifying a service

The stack uses a **per-service folder layout** under `services/<name>/`. Each service family (one or more co-lifecycled containers) owns:

- `service.yml` — manifest: env vars, source variants, image refs, dependencies, plus per-source bootstrapper runtime data under `runtime_sc:` / `runtime_adaptive:` / `runtime_deps:`
- `compose.yml` — Docker Compose fragment for that family's containers
- optional subdirectories holding Dockerfiles, init scripts, source code, configuration files, snapshots, etc. — see the **Subdirectory naming convention** below

The thin top-level `docker-compose.yml` merges fragments via Compose's native `include:` directive (requires Compose ≥ v2.20; v2.26+ recommended).

## TL;DR — the 60-second checklist

A maintainer who already understands the stack can land a new service in under an hour by following this list. Each step links to the relevant deep-dive section.

- [ ] **Pick a folder flavor** → [Decision 1](#decision-1--folder-flavor-container-virtual-or-doc-only)
- [ ] **Pick a category** → [Decision 2](#decision-2--category)
- [ ] **Pick your sources** → [Decision 3](#decision-3--source-variants)
- [ ] **Write `services/<name>/service.yml`** → [Mechanics](#mechanics--putting-it-all-together)
- [ ] **Write `services/<name>/compose.yml`** (only if folder flavor = container) → [Mechanics](#mechanics--putting-it-all-together)
- [ ] **Add the `include:` line to `docker-compose.yml`** (only if you wrote a compose fragment)
- [ ] **Run the four-command regen + lint chain** → [After you save the files](#after-you-save-the-files--regen--lint-commands-in-order)
- [ ] **Update audit-script allowlists** if your service has hard deps → [Audit-script + CI implications](#audit-script--ci-implications)
- [ ] **Commit and push.** CI gates the change (three jobs: manifest-lint+pytest, compose-equivalence+permutation matrix, docs-drift+audit-scripts).

If you're new to this codebase, read Decisions 1–6 in sequence; the Qdrant worked example illustrates each one.

## The six decisions you have to make

| # | Decision | Default if you're unsure | Drill-down |
|---|----------|--------------------------|------------|
| 1 | Folder flavor | `container` | [Decision 1](#decision-1--folder-flavor-container-virtual-or-doc-only) |
| 2 | Category | the category of the service you're most similar to | [Decision 2](#decision-2--category) |
| 3 | Source variants | `container` + `disabled` (minimum); add `localhost` if users might run this themselves | [Decision 3](#decision-3--source-variants) |
| 4 | Port allocation | nothing — it's auto-assigned. Just declare `<NAME>_PORT` in the env block. | [Decision 4](#decision-4--port-allocation) |
| 5 | Dependencies | the manifest of the closest sibling in your category, to preserve display order | [Decision 5](#decision-5--dependencies-depends_onrequired--optional) |
| 6 | Adaptive / hooks | none — start with declarative `runtime_sc`, escalate to a Python helper only when YAML can't express it | [Decision 6](#decision-6--adaptive-behavior--when-to-write-a-hook) |

> **Worked example throughout:** Adding **Qdrant**, a self-hosted vector database. (Qdrant is real software but NOT currently in the stack — Weaviate is our vector DB. Used here purely as an instructional example, not a proposal.)

## Adding a new service

> For a decision-driven walkthrough with worked example, see [TL;DR — the 60-second checklist](#tldr--the-60-second-checklist) and the six **Decision** sections that follow it. The 9-step list below is the terse "I know what I'm doing" path.

1. Create the folder: `mkdir services/myservice`
2. Write `services/myservice/service.yml`. Schema: `bootstrapper/schemas/service.schema.json`.
   - `name:` must equal the folder name (kebab-case).
   - `category:` one of `infra | data | llm | media | agents | apps`.
   - `containers:` lists every container name in your compose.yml.
   - `env:` declares every env var the service owns. Use `auto_managed: true` for vars computed by `runtime_sc.<key>.<source>.environment` or a Python helper in `bootstrapper/services/service_config.py`; use `secret: true` for credentials (default never echoed into `.env.example`).
   - `sources:` (optional) declares source variants the wizard surfaces — each option carries an `id`, `label`, and optional `requires:` list.
   - `runtime_sc:` carries the per-source bootstrapper data (`scale`, `environment`, `deploy`, `extra_hosts`) for each source variant. This is the operational source the bootstrapper consumes; the sources block is wizard-only.
   - `images:` lists each container's `${X_IMAGE}` env var so version bumps happen in one place.
3. Write `services/myservice/compose.yml`. Use `${VAR}` interpolation; never inline literal images. Conventions:
   - `services:` lists only this family's containers
   - `volumes:` lists only this family's named volumes (`name: ${PROJECT_NAME}-<service>-<purpose>`, plus `driver: local` for byte-equivalence with the legacy monolithic shape)
   - `networks:` references `backend-network`; never redefines it
   - Bind-mount paths are **relative to the fragment file** — i.e., to `services/myservice/` (e.g., `./init/scripts:/scripts`, `./build/snapshot:/snapshot`). Use `../../` only to reach genuinely cross-cutting locations: `../../bootstrapper/utils/` (catalog modules) and `../../volumes/...` (bootstrapper-generated runtime config like `volumes/litellm/config.yaml` and `volumes/api/kong-dynamic.yml`).
4. Add the fragment to the `include:` list in `docker-compose.yml`.
5. Service order is derived automatically from `depends_on:` topology — no manual ordering file needed.
6. If declarative `runtime_sc.<key>.<source>.environment` blocks can't
   express your computation, add the logic to
   `bootstrapper/services/service_config.py` as a new
   `_generate_<name>_config()` method and call it from
   `generate_service_environment()`. Cross-service computations
   (e.g. `_generate_cloud_providers_config()` aggregating three
   `CLOUD_*_SOURCE` toggles into the `LITELLM_ENABLED_PROVIDERS` list)
   already live there; follow the same shape.
7. Run the lint locally:
   ```bash
   cd bootstrapper && uv run python -m tools.validate_fragments
   ```
8. If you added or renamed a service, regenerate the generated artifacts:
   ```bash
   cd bootstrapper && uv run python -m tools.generate_architecture_diagram
   cd bootstrapper && uv run python -m tools.generate_readme_topology
   ```
   The lint in step (7) will fail if these are out of sync.
9. Run the test suite:
   ```bash
   cd bootstrapper && uv run pytest tests/ -q
   ```

## Decision 1 — Folder flavor: container, virtual, or doc-only

Three legitimate flavors of folder live under `services/`. Pick the right one before writing anything else.

| Flavor | `service.yml`? | `virtual: true`? | `compose.yml`? | Examples in this repo |
|---|---|---|---|---|
| **Container service** | yes | absent / false | yes | most services — backend, supabase, ollama, weaviate, … |
| **Virtual manifest** | yes | `true` | no | `cloud-providers/` (LiteLLM-routed APIs), `globals/` (project + branding env), `tts-provider/` (engine selector) |
| **Doc-only folder** | no | n/a | no | `stt-provider/`, `doc-processor/`, `multi2vec-clip/` — aggregator docs + diagrams for a role whose engines live in sibling folders |

**Flowchart:**

1. Does it run as a container with its own image? → **container**.
2. Does it own env vars / `SOURCE` toggles but with no compose fragment of its own? → **virtual**. Set `virtual: true`; omit `compose.yml`. The validator enforces this.
3. Is it documentation-only — aggregating other manifests under one user-facing role? → **doc-only**. No `service.yml`, no `compose.yml`, just `README.md` + `architecture.svg` / `architecture.html`.

> **Worked example — Qdrant:** Qdrant ships as a container image (`qdrant/qdrant:v1.12.0`), exposes a real HTTP API, and has its own env vars → **container flavor**.

**Common mistakes:**
- Adding a virtual manifest with a compose fragment — the schema validator will reject it. Either remove `compose.yml` (if no container runs) or unset `virtual: true` and keep the compose fragment (container flavor).
- Adding a doc-only folder when the role has env vars to manage — use a virtual manifest instead.

## Decision 2 — Category

Every manifest declares one of six categories. The category drives two things: the wizard block your row renders in, and the port-slot block your service draws from.

| Category | Wizard block | Services currently in this category | When to pick |
|---|---|---|---|
| `infra` | Infrastructure | Kong, globals | Gateways, project-wide config, observability |
| `data` | Data | Supabase, Redis, MinIO, Neo4j, Weaviate (+ `multi2vec-clip` as a Weaviate sub-module) | Databases, caches, object storage |
| `llm` | LLM Core | LiteLLM, Ollama, cloud-providers | LLM gateways / engines |
| `media` | Media | ComfyUI, parakeet, speaches, chatterbox, docling, searxng, tts-provider | Multimodal AI (image / audio / doc / search) |
| `agents` | Agents & Workflows | Hermes, n8n, openclaw | Programmable AI agents, workflow runners |
| `apps` | Apps & UIs | Backend, Open WebUI, JupyterHub, Local Deep Researcher | User-facing UIs |

**Effects of the category:**
- **Wizard placement.** Categories render in fixed order (`infra` → `data` → `llm` → `media` → `agents` → `apps`). Within a category, services follow topological order (driven by `depends_on.required`).
- **Port-slot block.** Each category gets its own port-offset range — see [Decision 4](#decision-4--port-allocation).
- **Architecture-diagram clustering.** The full-stack diagram at `docs/diagrams/architecture.svg` (generated from `architecture.dot`) clusters services by category. (Per-service architecture diagrams under `services/<name>/architecture.svg` are a different artifact — they cluster the call graph instead.)

> **Worked example — Qdrant:** Qdrant is a vector database. Its closest siblings in the stack are Weaviate and Supabase (which are also `data`-tier). → **`category: data`**.

**How to pick when you're unsure:** find the most-similar existing service and use its category. If your service genuinely doesn't fit any of the six, that's a design conversation, not a category decision — open an issue first.

## Decision 3 — Source variants

Every user-configurable service has an `<SVC>_SOURCE` env var. The wizard reads its values from the `sources.options` block in your manifest.

**Standard option names** (use these; don't invent new ones unless your service genuinely needs them):

| Option | Meaning | When to offer it |
|---|---|---|
| `container` | Run as a Docker container alongside the stack | Always, for container-flavor services |
| `container-cpu` / `container-gpu` | Split when the container has CPU/GPU variants | When you publish a GPU variant of the image |
| `localhost` | Connect to a user-managed instance on the host | When users typically already have this software installed locally (e.g. Ollama, ComfyUI) |
| `external` | Connect to a remote URL | When users may point at a managed cloud version |
| `api` | Use a hosted cloud API (no container) | LLM gateways only |
| `disabled` | Excluded from compose entirely | Always — every optional service must support this |
| `<engine>-*` | Engine-specific sub-variants | For aggregator services that pick from multiple engines (STT/TTS) |

**Implications of your choices:**

- **Locked vs. user-choice.** A service with only one source variant is "locked" — the wizard skips its prompt entirely. The `_is_locked` helper in `bootstrapper/services/topology.py` enforces this. Services like Backend, Kong, LiteLLM are locked because they're always-on.
- **`requires:` per option.** Use `requires: [<ENV_VAR>]` on a source option to declare prerequisite env vars (e.g. `external` typically requires `<SVC>_EXTERNAL_URL`).
- **`<SVC>_LOCALHOST_URL` symmetry.** If you offer `localhost`, BOTH the in-container consumers (`runtime_sc.<svc>.localhost.environment`) AND the Kong route generator (`bootstrapper/utils/kong_config_generator.py`) must read the SAME `<SVC>_LOCALHOST_URL` env var. Otherwise Kong and in-container clients silently disagree about where the localhost upstream lives. See [Common gotchas](#common-gotchas--anti-patterns).
- **`runtime_sc` slice per source.** Every source variant declared in `sources.options` should have a matching `runtime_sc.<key>.<source>` slice with `scale`, `environment`, `deploy`, `extra_hosts`. The manifest validator does NOT currently check coverage — a missing slice silently scales that source to 0 — so add a slice for every option you declare.

> **Worked example — Qdrant:** Most users won't already run Qdrant locally, so `container` is the primary path. But we offer all four anyway for flexibility:
> - `container` — default, scale=1
> - `localhost` — `QDRANT_LOCALHOST_URL` defaults to `http://host.docker.internal:6333` (Qdrant's standard host port)
> - `external` — `requires: [QDRANT_EXTERNAL_URL]`
> - `disabled` — scale=0

## Decision 4 — Port allocation

**The bootstrapper auto-assigns ports. You do not pick a port.**

**How it works:**
- `BASE_PORT` (default `63000`) is the bottom of the port range. Users can override with `./start.sh --base-port 64000`.
- `CATEGORY_SLOTS` in `bootstrapper/services/topology.py` assigns each category an `(offset, block_size)` tuple. Current values (accurate as of 2026-05-24):

  | Category | Offset | Block size | Resolved range with default `BASE_PORT=63000` |
  |---|---:|---:|---|
  | `infra` | 0 | 10 | 63000-63009 |
  | `data` | 10 | 20 | 63010-63029 |
  | `llm` | 30 | 10 | 63030-63039 |
  | `media` | 40 | 20 | 63040-63059 |
  | `agents` | 60 | 20 | 63060-63079 |
  | `apps` | 80 | 20 | 63080-63099 |

- Within each category block, services consume slots in **topological order** (driven by `depends_on.required` — see Decision 5). Multi-port services (e.g. Supabase's 8 containers, Weaviate's HTTP + gRPC pair, MinIO's API + Console pair) get a contiguous run.
- A category-overflow lint trips if you blow past your block. Fixes: move manifests to a different category (rare), or extend the block size in `CATEGORY_SLOTS` (also rare — coordinate with maintainers).

**How to declare a port:**

In your `env:` block, declare `name: <SVC>_PORT` with NO `default:` line. Convention is a single-line comment:

```yaml
env:
  - name: QDRANT_PORT
    # default removed — computed by services/topology.py slot allocator
```

The `services/env_assembler.py` regen step emits the resolved port into `.env.example`. Never hand-edit `.env.example` — it's a generated artifact (byte-equivalence-tested in CI).

> **Worked example — Qdrant:** Qdrant declares `QDRANT_PORT` with no default. Topology slots it into the `data` block at the next free offset, determined by where it lands in the topo sort relative to its siblings (Supabase microservices, Redis, MinIO, Neo4j, Weaviate). The exact number is auto-resolved at every regen — don't pin it.

## Decision 5 — Dependencies (`depends_on.required` / `optional`)

This is the most nuanced decision. The field `depends_on.required` in `service.yml` has **two semantics that get conflated**:

**Runtime semantics (intended):** "These services must be up before this one boots." Maps to the corresponding `depends_on:` block in your `compose.yml` fragment.

**Display-ordering semantics (overloaded):** The bootstrapper uses `depends_on.required` as the canonical-order backbone for the wizard's row order and the overview-box display. Within a category, services sort topologically; an edge from A → B means A appears AFTER B in the same category's wizard block.

### Why this matters — the footgun

Kong's manifest used to list 19 services in `required` because Kong **proxies** to them — but Kong doesn't need them to **boot** (only Supabase + Redis). Trimming the list to its real boot dependencies was correct.

But trimming `litellm` from `ollama.depends_on.required` correctly removed a fake runtime edge — and broke a UI ordering test (`test_row_order_stability.py`), because `ollama` was relying on that edge to pin its position in the wizard's LLM block. Removing it shifted port slots throughout the LLM and media blocks.

### Current convention (codified in manifest comments in commit `d98bc5a`)

- Use `required` for **genuine bootstrap blockers** AND for **cross-category display-ordering pins**.
- Comment any non-runtime edge inline as a display-ordering pin so readers don't try to "fix" it. Example from `services/ollama/service.yml`:

  ```yaml
  depends_on:
    # `litellm` is listed here NOT because the ollama container calls
    # LiteLLM (the call direction is the opposite), but because the
    # bootstrapper uses `depends_on.required` as the canonical-order
    # backbone for the wizard / overview-box display. […]
    required:
      - supabase
      - litellm
  ```

- A future schema change may add a separate `display_order:` field that takes over the ordering job; until then, comment the intent.

### Things to avoid

- **Don't** list every service you *call* in `required`. Use `data_flow.calls` for that (it drives the architecture diagram and the per-service README's Dependencies & Integrations block — not topology).
- **Don't** depend on virtual aggregates (`globals`, `cloud-providers`) in `required`. They have no runtime presence; the audit removed phantom `globals` edges from `supabase` and `docling`.
- **Don't** list `optional` deps that compose doesn't enforce. The `optional` list is documentation; if compose doesn't gate on it, it has no effect.
- **Don't** list a depends-on for a service that's source-replaceable (`localhost`, `external`, `disabled`). The audit script `scripts/check-compose-source-deps.py` enforces this; SOURCE-replaceable consumers should reach their target via endpoint env vars + runtime readiness checks, not via compose `depends_on`.

> **Worked example — Qdrant:** Qdrant's only data-tier sibling that always runs is Supabase (the substrate the bootstrapper provisions before any other service starts). Listing it as a required dep pins Qdrant's position in the data block topologically. → `required: [supabase]`, `optional: []`.

### `data_flow.calls` is separate

The `data_flow.calls` field is a runtime call graph that drives the architecture diagram and the per-service README's Dependencies & Integrations block. It is **independent** of `depends_on`. Use it to describe which services this one calls at runtime in the request path (excluding init-time bootstrap calls).

## Decision 6 — Adaptive behavior + when to write a hook

Most services express their per-source behavior with declarative `runtime_sc` YAML. The synthesizer in `bootstrapper/services/sc_synthesizer.py` concatenates all manifests' `runtime_sc` slices into the runtime service-config dict the bootstrapper consumes.

**Declarative example** (suffices for ~90% of services):

```yaml
runtime_sc:
  qdrant:
    container:
      scale: 1
      environment:
        QDRANT_LOG_LEVEL: info
      deploy: {}
      extra_hosts: []
    localhost:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ${QDRANT_LOCALHOST_URL}
      deploy: {}
      extra_hosts:
        - host.docker.internal:host-gateway
    disabled:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []
```

### When you need a `_generate_<svc>_config()` Python helper

Write a helper in `bootstrapper/services/service_config.py` and wire it into `generate_service_environment()` ONLY when one of these is true:

1. **Multi-input SOURCE dependencies.** Your output depends on more than one `<SVC>_SOURCE` value. Example: `_generate_stt_provider_config` and `_generate_tts_provider_config` cooperate via a `shared_env` dict — STT runs first and writes `SPEACHES_SCALE`; TTS reads STT's output and avoids double-scheduling Speaches when both roles pick a Speaches variant.
2. **Derived / aggregated state.** You need to compute env vars from a set of toggles. Example: `_generate_cloud_providers_config` reads three `CLOUD_*_SOURCE` toggles + their API keys and emits `LITELLM_ENABLED_PROVIDERS` as a comma-separated string.
3. **Runtime-computed values.** You need an env var whose value depends on another service's port, computed at runtime from `BASE_PORT`.

For everything else, stay declarative. Adding a hook means writing Python, adding a unit test for it, and giving future maintainers an extra place to read.

> **Worked example — Qdrant:** Single SOURCE, no cross-service dependencies, no derived state. → **No hook needed.** The declarative `runtime_sc` covers all four sources.

### `runtime_adaptive` and `runtime_deps`

Two adjacent fields that occasionally apply:

- **`runtime_adaptive`** — for services like `backend` that adapt their behavior based on which upstream services are enabled. Declares `adapts_to:` (a list of provider keys) and `environment_adaptation:` (env vars conditionally set when those providers are active). See `services/backend/service.yml` for the reference pattern.
- **`runtime_deps`** — declares optional runtime dependencies (services this one calls only if they're enabled). Drives the info-message shown to the user during the wizard.

Use these only if your service is genuinely adaptive. Today seven manifests declare `runtime_adaptive` (backend, comfyui, hermes, jupyterhub, n8n, ollama, weaviate); backend is the most heavily adaptive and the canonical reference. Don't reach for these fields by default — start with declarative `runtime_sc` and only escalate when the adaptive behavior is non-trivial.

## Mechanics — putting it all together

After making the six decisions, you write two files. Here's the full result for Qdrant. Line callouts (`# ← Decision N`) point back to the decision section that explains the choice.

### `services/qdrant/service.yml`

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
  default: disabled                           # off by default; user opts in
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
    # default removed — computed by services/topology.py slot allocator
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

### `services/qdrant/compose.yml`

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

### `docker-compose.yml` — one new include line

Add to the top-level `include:` block in the `# Data tier` section:

```yaml
  # Data tier
  - services/supabase/compose.yml
  - services/redis/compose.yml
  - services/minio/compose.yml
  - services/neo4j/compose.yml
  - services/qdrant/compose.yml              # ← new
```

## After you save the files — regen + lint commands in order

Five commands, in this order:

```bash
cd bootstrapper

# 1. Regenerate .env.example from manifests
uv run python -m services.env_assembler

# 2. Regenerate README.md TOPOLOGY block (auto-includes the new row)
uv run python -m tools.generate_readme_topology

# 3. Regenerate docs/diagrams/architecture.dot (+ render the SVG via Graphviz)
uv run python -m tools.generate_architecture_diagram
dot -Tsvg ../docs/diagrams/architecture.dot > ../docs/diagrams/architecture.svg

# 4. Lint — fails if any of steps 1-3 were skipped
uv run python -m tools.validate_fragments

# 5. (Optional, recommended for new manifests) Regen per-service README + diagram
PYTHONPATH=. uv run python -m docs.regen qdrant
# After this, services/qdrant/{README.md, architecture.svg, architecture.html} exist.
```

**When to re-run each step:**

- **`env_assembler`** — after any change to a manifest's `env:` block, port allocation, or source variants.
- **`generate_readme_topology`** — after any change to a manifest's `rows:`, `display_name`, `category`, or `alias`.
- **`generate_architecture_diagram` + `dot -Tsvg`** — after any change to a manifest's `depends_on` or `data_flow.calls`.
- **`validate_fragments`** — always, as the final check before committing.
- **`docs.regen`** — only after creating a new service, or after editing `data_flow.calls` on an existing service. The drift gate in CI (`bootstrapper.docs.regen --all --check`) catches stale per-service READMEs/SVGs/HTMLs.

**Graphviz prerequisite:** the `dot` command requires Graphviz. Install with `brew install graphviz` (macOS), `sudo apt-get install graphviz` (Debian/Ubuntu), or `choco install graphviz` (Windows). See `docs/diagrams/README.md`.

## Audit-script + CI implications

After adding a service, check these allowlists. Skipping them means CI fails on the next push.

### `scripts/check-compose-source-deps.py` — two allowlists

- **`REQUIRED_DEPENDS_ON`** — set of `(service, dependency)` tuples that MUST appear in compose `depends_on`. Add entries here if your compose fragment hard-depends on `litellm`, `redis`, `supabase-db`, `weaviate-init`, etc. The script fails CI if your manifest claims a hard dep that compose doesn't enforce, OR vice versa.
- **`FORBIDDEN_OPTIONAL_DEPENDS_ON`** — set of edges that MUST NOT exist (depending on a SOURCE-replaceable service via `depends_on` is unsafe because that service may not run as a container). Add entries here if you have an intentional exception with documented justification.

### `scripts/check-kong-routes.py` — baseline-default audit

The script runs the Kong route generator against `.env.example` defaults (in a tmp working dir) and verifies the resulting routes match a hardcoded `EXPECTED_HOST_ROUTES` table at the top of the script. If your service publishes a `*.localhost` alias AND its source variant is on-by-default (i.e. `<SVC>_SOURCE`'s default value renders a route), add an entry to `EXPECTED_HOST_ROUTES` mapping the host to the expected upstream URL. Services that are off by default need no entry.

### `.github/dependabot.yml` — `directories:` list

If your service ships a `requirements.txt` / `pyproject.toml` in a `build/` or `provider/` subdirectory, add the path to the `directories:` list of the `pip` ecosystem block. **Memory note:** all active manifests must be enumerated; omitted paths drop from scan coverage and silent vulnerabilities accumulate.

### CI gates that run on every push

The `.github/workflows/services-lint.yml` workflow has three jobs:

| Job | What it catches |
|---|---|
| **Manifest lint + unit tests** | `validate_fragments` lint + 315+ pytest tests. Catches: manifest schema violations, dependency cycles, env-example drift, category overflow. |
| **Compose merge + byte-equivalence + source-permutation matrix** | Renders `docker compose config` for the merged fragment list + verifies it matches the golden baseline + tests every source variant of every service. Catches: compose-syntax errors, source-permutation regressions. |
| **Docs drift + audit scripts** | `regen --all --check` + the 5 audit scripts (`check_doc_links`, `check-compose-source-deps`, `check-docs-drift`, `check-kong-routes`, `validate_research_schema`). Catches: stale per-service docs, missing `REQUIRED_DEPENDS_ON` entries, Kong route default drift, broken markdown links, research-schema violations. |

Run the equivalent of all three locally before pushing:

```bash
cd bootstrapper && uv run pytest -q                                    # job 1 + 2 (minus byte-equivalence)
cd bootstrapper && uv run python -m tools.validate_fragments           # job 1 lint
cp .env.example .env && docker compose -f docker-compose.yml config -q # job 2 merge check
cd .. && PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen --all --check  # job 3 docs drift
python scripts/check_doc_links.py                                      # job 3 link check
python scripts/check-compose-source-deps.py                            # job 3 deps audit
python scripts/check-docs-drift.py                                     # job 3 docs structural audit
python scripts/check-kong-routes.py                                    # job 3 kong audit
python scripts/validate_research_schema.py --all                       # job 3 research schema
```

## Common gotchas + anti-patterns

Distilled from real audit findings — each entry cites the commit, PR, or memory note it came from.

### Dependency-list gotchas

- **Cross-category `depends_on.required` is a display-order pin.** Removing `litellm` from `ollama.required` is correct from a runtime POV but shifts the wizard's row order in the llm block (and transitively can affect media services like ComfyUI that chain through ollama). Keep cross-category edges and document the intent inline. See commit `d98bc5a`.
- **Don't depend on virtual aggregates in `required`.** `globals`, `cloud-providers`, `tts-provider` are virtual — no container, no compose. Depending on them adds a phantom node to the topo sort. The audit removed phantom `globals` edges from `supabase` and `docling`.
- **Compose-only deps vs. manifest deps must align both ways.** Kong's manifest used to list 19 proxy targets in `required` but compose only had 5 (truly correct — over-claimed). Backend's manifest only listed `[supabase, redis]` but compose waited for `litellm` health (under-claimed). The audit corrected both; `scripts/check-compose-source-deps.py` now catches missing edges.

### URL / localhost handling

- **`<SVC>_LOCALHOST_URL` overrides must be symmetric.** If you read it in a new in-container consumer, Kong's route generator must read the same var too. Otherwise the two paths silently disagree about where the upstream lives.
- **Kong routes fronting browser SPAs need `preserve_host: True`.** Without it the SPA emits unreachable redirect URLs containing the internal Docker hostname.

### Init-container patterns

- **Init containers use vanilla `alpine:latest` + inline `apk add`.** Don't ship a Dockerfile that builds a custom init image — the global `alpine:latest` tag gets clobbered.
- **TTS/STT engine in-container ports are NOT all 8000.** Parakeet, Speaches, Docling listen on `8000`; Chatterbox listens on `4123`. Don't assume.

### Regen / test gotchas

- **`.env.example` is byte-equivalence-tested.** After any manifest change affecting env vars or port allocation, regen `.env.example` or `test_env_example_consistency` will fail CI.
- **`test_fragment_equivalence` is sensitive to Compose-version defaults.** Don't regenerate the golden baseline reflexively when this test fails. Extend `_strip_volatile_defaults` in the test fixture instead.
- **`docker compose config` needs `.env` to render properly.** In CI, the audit-scripts job copies `.env.example` to `.env` before running the source-deps audit. Locally, you have a real `.env` so this is invisible — but if you remove your `.env`, the audit script's fallback to raw parsing of the top-level `docker-compose.yml` (which is an `include:`-only shell) produces spurious "missing required core dependency" failures.

### Topology / category gotchas

- **A new service in a near-full category block can trip the category-overflow lint.** `data` and `media` blocks are 20 slots each but Supabase alone uses 7. Check current utilization before assuming there's room.
- **Renaming a `row.display_name` breaks tests that hardcode it.** `test_wizard_app_discovery.py` has an `EXPECTED_DISCOVERED` frozenset; update it when renaming.

## Subdirectory naming convention

Each service folder can hold additional subdirectories beyond `service.yml` and `compose.yml`. Use these well-known names so navigation stays predictable across the stack:

| Subdir | Holds | Example |
|---|---|---|
| `app/` | Source code for an app the manifest builds (the manifest's primary container is **this** code) | `services/backend/app/` (FastAPI source) |
| `build/` | Dockerfile + build inputs when the manifest builds a container from scratch | `services/jupyterhub/build/`, `services/neo4j/build/`, `services/local-deep-researcher/build/` |
| `init/` | Scripts + templates bind-mounted into a `<service>-init` sidecar container that prepares state before the main container starts | `services/n8n/init/`, `services/hermes/init/`, `services/comfyui/init/`, `services/minio/init/`, `services/weaviate/init/` |
| `catalog-init/` | Same as `init/` but for a *second* init sidecar that runs in a different tier (used by litellm only) | `services/litellm/catalog-init/` |
| `pull/` | Same as `init/` but the sidecar is named `<service>-pull` (only ollama) | `services/ollama/pull/` |
| `config/` | Read-only configuration files bind-mounted into the main container at runtime | `services/searxng/config/` (settings.yml) |
| `db/` | Database snapshots + SQL migration scripts | `services/supabase/db/` (snapshot/ + scripts/) |
| `provider/` | Multiple host/container providers for a single capability the manifest exposes via a SOURCE variable (one engine = one subfolder of `provider/`) | `services/parakeet/provider/{gpu,mlx,whisper-cpp,shared}`, `services/docling/provider/{gpu,localhost,shared}`, `services/tts-provider/provider/localhost` |
| `extras/` | User-managed bind-mounted data exposed inside the running container (tools, functions, workflows you can edit on the host) | `services/open-webui/extras/{tools,functions,workflows}` |
| `workflows-stage/` | Workflow JSON the init sidecar imports into the main container's DB on startup | `services/n8n/workflows-stage/` |

**Family folders.** Some manifests own a family of related containers (e.g. supabase = 8 containers, n8n = main + worker + init). Each family folder gets a brief `README.md` listing the containers it ships and pointing at their definition in `compose.yml`. The fragment's `services:` keys are the authoritative container list; the manifest's `containers:` must match 1:1 (the manifest_validator enforces this — see "Validator rules" below).

## Modifying an existing service

- Env var default change → edit the manifest's `env:` block. Re-run the lint.
- Image version bump → edit the manifest's `images[].default`. The compose fragment references the var, so no compose change is needed.
- New container in the family → add to `containers:` in the manifest AND to `services:` in the fragment.
- New source variant → add to `sources.options[]` in the manifest.

### Common modification flows

Short walk-throughs for the modifications you'll do most often:

- **Add a new source variant to an existing service.** Edit `sources.options` + `runtime_sc.<key>` to include the new source. Regen `.env.example`. The source-permutation matrix in CI will exercise every variant — make sure your new variant has a valid `runtime_sc` slice.
- **Rename a service's display name (`rows[].display_name`).** Update the row, then regen the README topology block. Search the test suite for the old name — `bootstrapper/tests/test_wizard_app_discovery.py::EXPECTED_DISCOVERED` is the most common dependency.
- **Bump a container image version.** Edit `images[].default` only. The compose fragment uses `${X_IMAGE}` interpolation, so nothing else changes. Don't forget to test the new image locally before committing.
- **Split a service family into multiple manifests.** Non-trivial. The supabase manifest (8 containers in one family) is the reference pattern; consult it before splitting.

## Cross-referencing sections in service READMEs

Service READMEs follow a numbered convention (`## 1. Overview`, `## 2. Access`, …). The "Dependencies & Integrations" block sits at whatever section number N the README's structure places it — typically 5, but 7/9/12/14 in READMEs with extra pre-Deps content. The `bootstrapper/docs/regen.py` tool detects N and emits matching subsection numbering (`### N.1` through `### N.6`) inside the block.

**Never link to a sub-section by number across services.** "See section 5.4 in the backend README" breaks the moment the target README adds a new pre-Deps section and shifts to 6.4. Always reference by heading text instead: "See *Future — Missing pair integrations* in the backend README."

## Schema cheatsheet

> This section is a quick field reference. For guidance on which fields apply when (and why), see Decisions 1–6 above.

```yaml
name: myservice
label: "My service (human-readable)"
category: apps                          # infra | data | llm | media | agents | apps
docs: services/myservice/README.md        # optional
virtual: false                          # true for env-only manifests like cloud-providers

containers:                             # may be [] when virtual: true
  - myservice

images:
  - var: MYSERVICE_IMAGE
    default: "myorg/myservice:1.0.0"
    container: myservice

sources:                                # OPTIONAL; omit for single-source services
  var: MYSERVICE_SOURCE
  default: container
  options:
    - id: container
      label: "Container"
    - id: disabled
      label: "Disabled"

# Per-source runtime data — what the bootstrapper actually consumes.
# The synthesizer (bootstrapper/services/sc_synthesizer.py) concatenates
# this block (plus all other manifests' runtime_sc blocks) into the dict
# that ConfigParser.load_yaml_config() returns.
runtime_sc:
  myservice:                             # the key matches a name service_config.py reads
    container:
      scale: 1
      environment:
        MYSERVICE_ENDPOINT: "http://myservice:8080"
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment:
        MYSERVICE_ENDPOINT: ""
      deploy: {}
      extra_hosts: []

env:
  - name: MYSERVICE_SOURCE
    default: container
  - name: MYSERVICE_PORT
    default: 63099
  - name: MYSERVICE_API_KEY
    default: ""
    secret: true                        # default never echoed into .env.example
  - name: MYSERVICE_SCALE
    auto_managed: true                  # computed by service_config.py from source value
  - name: MYSERVICE_ENDPOINT
    auto_managed: true

depends_on:                             # logical deps (compose-level lives in compose.yml)
  required: []
  optional: []

exports:                                # documents the cross-service env-var contract
  - name: MYSERVICE_ENDPOINT
    consumers: [backend, n8n]
```

## Validator rules (what the lint catches)

1. **schema check** — every `service.yml` matches `bootstrapper/schemas/service.schema.json`
2. **duplicate_env_var** — exactly one manifest owns each env-var name
3. **duplicate_container** — exactly one manifest owns each container name
4. **unknown_dependency** — `depends_on.required/optional` references a known manifest
5. **undeclared_export** — every `exports[].name` is declared in `env:` OR written by some `runtime_sc.<key>.<source>.environment`
6. **undeclared_source_var** — the SOURCE var itself is declared in `env:`
7. **unknown_consumer** — every `exports[].consumers` entry is a known manifest

## Byte-equivalence

`bootstrapper/tests/test_fragment_equivalence.py` asserts that
`docker compose -f docker-compose.yml config` matches the golden baseline at
`bootstrapper/tests/fixtures/rendered_config_baseline.yml`. If you change a
fragment's compose shape, you'll either need to update the baseline (after
confirming the change is intentional) or restore byte-equivalence.

```bash
# Inspect drift
docker compose --env-file .env -f docker-compose.yml config > /tmp/actual.yml
diff bootstrapper/tests/fixtures/rendered_config_baseline.yml /tmp/actual.yml

# Refresh baseline (only when the drift is intentional)
docker compose --env-file .env -f docker-compose.yml config > \
    bootstrapper/tests/fixtures/rendered_config_baseline.yml
```


## `services/_user/` overlay slot (downstream submodule consumers)

Downstream forks that consume this repo as a git submodule may want to layer
additional services without modifying the upstream tree. Drop them under
`services/_user/<name>/`:

```
services/
├── _user/                    # gitignored upstream; tracked downstream
│   └── my-extra-service/
│       ├── service.yml
│       └── compose.yml
├── supabase/
├── ollama/
└── …
```

The default manifest loader (`bootstrapper.services.manifests.load_manifests`)
skips directories whose name starts with `_`, so `_user/` is invisible to the
core stack. A downstream `start.sh` wrapper can call
`load_manifests(services_dir / "_user")` and merge the results into its own
runtime — the manifest schema and the synthesizer are the same.

This slot is reserved by convention; the upstream `.gitignore` excludes
`services/_user/` so the directory never leaks into a fork's PRs.


## Documentation-only manifest fields

A few fields on `service.yml` are accepted by the schema but not yet consumed
by any operational code. They exist for clarity and future use:

- `images[].notes` — free-form note on what the image is used for. Not read
  by any Python code.
- `docs:` — pointer to a `services/<name>.md` file. Useful for grep,
  but no Python imports it.
- `exports[]` — declares the env-var contract this service offers to other
  services. The cross-manifest validator (`bootstrapper/services/manifest_validator.py`)
  checks closure (every consumer name resolves) but does NOT check that the
  exported value is actually produced at runtime.

Treat these as documentation. Setting them helps future readers; omitting
them never breaks anything.
