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
- [ ] **Commit and push.** CI's three jobs (manifest-lint+pytest, compose-equivalence+permutation matrix, docs-drift+audit-scripts) gate the change.

If you're new to this codebase, read the six decisions sections in order before touching code. The worked example threads through them.

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

## Folder flavors: container, virtual, doc-only

Three legitimate flavors of folder live under `services/`. Pick the right one when adding new content:

| Flavor | `service.yml`? | `virtual: true`? | `compose.yml`? | Examples |
|---|---|---|---|---|
| Container service | ✓ | absent / false | ✓ | most services — backend, supabase, ollama, … |
| Virtual manifest | ✓ | true | ✗ | `cloud-providers/` (LiteLLM-routed APIs), `globals/` (project + branding env), `tts-provider/` (engine selector) |
| Doc-only folder | ✗ | n/a | ✗ | `stt-provider/`, `doc-processor/`, `multi2vec-clip/` — aggregator docs + diagrams for a role whose engines live in sibling folders |

Use a **virtual manifest** when the folder owns env vars / `SOURCE` toggles that the bootstrapper must read, but no container runs. Use a **doc-only folder** when the role is a documentation surface aggregating other manifests and has no env vars of its own.

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
