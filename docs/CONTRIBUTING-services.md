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

## Cross-referencing sections in service READMEs

Service READMEs follow a numbered convention (`## 1. Overview`, `## 2. Access`, …). The "Dependencies & Integrations" block sits at whatever section number N the README's structure places it — typically 5, but 7/9/12/14 in READMEs with extra pre-Deps content. The `bootstrapper/docs/regen.py` tool detects N and emits matching subsection numbering (`### N.1` through `### N.6`) inside the block.

**Never link to a sub-section by number across services.** "See section 5.4 in the backend README" breaks the moment the target README adds a new pre-Deps section and shifts to 6.4. Always reference by heading text instead: "See *Future — Missing pair integrations* in the backend README."

## Schema cheatsheet

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
