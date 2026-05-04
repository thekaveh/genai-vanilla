# GenAI Vanilla Repo Audit Report: Documentation, Architecture, and Service Dependency Drift

Date: 2026-05-02
Branch inspected: feature/textual-wizard-migration
Scope: documentation accuracy, architecture diagrams, SOURCE configuration docs, service dependencies, service coverage, and neglected integration details.

## Executive Summary

I inspected the current repo against the live implementation: `docker-compose.yml`, `.env.example`, `bootstrapper/service-configs.yml`, `bootstrapper/services/*`, `bootstrapper/core/port_manager.py`, `bootstrapper/utils/kong_config_generator.py`, `README.md`, and `docs/**`.

The largest issues are not cosmetic. Several docs describe behavior that the bootstrapper does not implement, and several dependency definitions appear stale or internally inconsistent. The most important fixes are:

1. Fix stale URL and port documentation in `README.md` and service docs.
2. Reconcile `BASE_PORT` documentation with the actual port-rewrite implementation.
3. Fix wrong external/localhost variable names and ports in SOURCE docs.
4. Update architecture diagrams to match actual Kong routes, compose services, and dependency behavior.
5. Fix neglected service dependency modeling, especially `depends_on` for services that can be scaled to zero by SOURCE selection.
6. Fix misleading docs for `BACKEND_SOURCE=disabled`; the implementation currently forces `BACKEND_SCALE=1`.
7. Expand service documentation coverage for major first-class services that have no docs.
8. Add an automated documentation/config drift check so this does not recur.

Repository facts observed:

- `docker-compose.yml` defines 32 services.
- `bootstrapper/service-configs.yml` defines 28 `source_configurable` entries, 6 `adaptive_services`, and 7 `service_dependencies` entries.
- `docs/` contains 15 Markdown docs.
- `docs/services/` has only 8 service docs.
- Kong generator currently defines these host routes: `api.localhost`, `chat.localhost`, `comfyui.localhost`, `jupyter.localhost`, `n8n.localhost`, `openclaw.localhost`, `search.localhost`.

## Severity Legend

- Critical: likely breaks startup, disables documented configurations, or causes users to follow invalid instructions.
- High: major documentation/architecture mismatch that causes confusion or failed setup.
- Medium: incomplete coverage, stale detail, missing dependency explanation.
- Low: broken links, polish, maintainability.

---

## Critical Issues

### C1. `BACKEND_SOURCE=disabled` is documented but not actually supported

Evidence:

- `.env.example` documents: `BACKEND_SOURCE=container  # Options: container, disabled`.
- `README.md` lists Backend API as container-only with `BACKEND_SOURCE=container|disabled`.
- `docs/deployment/source-configuration.md` lists Backend API options as `container`, `disabled`.
- Implementation in `bootstrapper/services/service_config.py` forces:
  - `_generate_adaptive_services_config()`: `env_vars['BACKEND_SCALE'] = '1'`
- CLI help does not expose `--backend-source`, while docs imply the SOURCE can be changed.
- `bootstrapper/service-configs.yml` has `backend` only under `adaptive_services`, not as a real `source_configurable` entry with `disabled`.

Impact:

Users will think Backend can be disabled via `.env`, but generation resets it to scale 1. If validation runs, `BACKEND_SOURCE=disabled` may also be treated as invalid because pure adaptive services only support `container`.

Recommended fix:

Choose one of these and make all files agree:

A. If Backend must always run:
- Remove `disabled` from `.env.example`, README, and SOURCE docs.
- Explain Backend is always-on when the stack runs.

B. If Backend should be optional:
- Add backend to `source_configurable` with `container` and `disabled`.
- Update `_generate_adaptive_services_config()` to respect `BACKEND_SOURCE`.
- Add CLI option `--backend-source [container|disabled]`.
- Ensure Kong route generation skips `api.localhost` when disabled.

---

### C2. Compose `depends_on` is static, but SOURCE modes scale dependencies to zero

Evidence:

Several services have hard `depends_on` entries for services that SOURCE settings can scale to `0`:

- `jupyterhub` depends on `weaviate`, `ollama`, and `neo4j-graph-db` unconditionally in `docker-compose.yml`.
- `n8n` and `n8n-worker` depend on `weaviate` unconditionally.
- `weaviate` depends on `multi2vec-clip` unconditionally.
- `openclaw-gateway` depends on `openclaw-init` unconditionally.

But SOURCE configuration can set scales to zero:

- `LLM_PROVIDER_SOURCE=ollama-localhost`, `ollama-external`, `api`, or `disabled` can set `OLLAMA_SCALE=0`.
- `WEAVIATE_SOURCE=localhost` or `disabled` can set `WEAVIATE_SCALE=0`.
- `NEO4J_GRAPH_DB_SOURCE=localhost` or `disabled` can set `NEO4J_SCALE=0`.
- `MULTI2VEC_CLIP_SOURCE=disabled` can set `CLIP_SCALE=0`.
- `OPENCLAW_SOURCE=localhost` sets `OPENCLAW_INIT_SCALE=0`.

Impact:

Documented SOURCE combinations can be structurally incompatible with static compose startup ordering. For example, `./start.sh --llm-provider-source ollama-localhost --jupyterhub-source container` is documented as normal, but JupyterHub still has a compose-level dependency on the `ollama` container service. Similar risks exist for Weaviate localhost/disabled and Multi2Vec disabled.

Recommended fix:

- Audit every `depends_on` in `docker-compose.yml` against SOURCE modes.
- For optional/localhost/external dependencies, move readiness logic into service startup scripts or bootstrapper-generated compose overlays.
- Alternatively split compose fragments by profile/source rather than relying only on `deploy.replicas`.
- Update docs to distinguish:
  - logical dependency: service can use endpoint if available
  - compose dependency: container must start first
  - SOURCE dependency: local/external provider replaces container

---

### C3. Dependency manager treats some disabled optional services as available

Evidence:

`bootstrapper/services/dependency_manager.py` only maps scale variables for:

- `n8n`, `n8n-worker`, `weaviate`, `neo4j-graph-db`, `searxng`, `backend`, `jupyterhub`, `openclaw-gateway`

But `service-configs.yml` dependency lists include optional service names:

- `parakeet`
- `xtts`
- `docling`
- `ollama`

Those names do not map to actual scale variables such as:

- `PARAKEET_GPU_SCALE`
- `XTTS_GPU_SCALE`
- `DOCLING_GPU_SCALE`
- `OLLAMA_SCALE`

In `get_service_scale()`, unknown service names default to `1`.

Impact:

Dependency messages can claim disabled optional services are available. This undermines dependency validation and can hide real misconfiguration. It also makes docs around optional STT/TTS/Docling dependencies less trustworthy.

Recommended fix:

- Normalize names across compose, YAML, dependency manager, and docs.
- Add mappings for actual service names and logical service aliases:
  - `parakeet` / `parakeet-gpu` -> `PARAKEET_GPU_SCALE`
  - `xtts` / `xtts-gpu` -> `XTTS_GPU_SCALE`
  - `docling` / `docling-gpu` -> `DOCLING_GPU_SCALE`
  - `ollama` -> `OLLAMA_SCALE` or endpoint availability based on `LLM_PROVIDER_SOURCE`
- Add tests for dependency reporting under default config where STT/TTS/Docling are disabled.

---

### C4. Multiple GPU profile selections can overwrite `COMPOSE_PROFILES`

Evidence:

`bootstrapper/services/service_config.py` sets `COMPOSE_PROFILES` in these methods:

- `_generate_stt_provider_config()` sets `parakeet-gpu`
- `_generate_tts_provider_config()` sets `xtts-gpu`
- `_generate_doc_processor_config()` sets `docling-gpu,doc-gpu`

Each method reads `current_profiles = self.service_sources.get('COMPOSE_PROFILES', '')`, not the already accumulated `env_vars`. Because `self.service_sources` is loaded once from the original `.env`, enabling multiple GPU optional services in the same run can cause later generators to overwrite earlier profile additions.

Impact:

Documented combinations such as enabling STT GPU + TTS GPU + Docling GPU may only activate the last generated profile set. This is both a code issue and a documentation risk because docs present GPU variants as independently composable.

Recommended fix:

- Accumulate profiles in a local set during `generate_service_environment()`.
- Write `COMPOSE_PROFILES` once at the end.
- Document exact profile names only after implementation is stable.

---

## High Priority Documentation Drift

### H1. README Quick Start URLs are inconsistent with actual port mapping and Kong routes

Evidence:

`README.md` Quick Start says:

- Open WebUI: `http://localhost:63015`
- n8n: `http://localhost:63002`
- Supabase Studio: `http://localhost:63009`
- SearxNG: `http://localhost:63014`
- ComfyUI: `http://comfyui.localhost:63002`
- JupyterHub: `http://localhost:63048`

Actual mappings:

- `KONG_HTTP_PORT = BASE_PORT + 2 = 63002`
- `N8N_PORT = BASE_PORT + 17 = 63017`
- n8n Kong route host is `n8n.localhost`, not root `localhost:63002`.
- `COMFYUI_PORT = BASE_PORT + 18 = 63018`, with Kong host `comfyui.localhost`.
- `SEARXNG_PORT = BASE_PORT + 14 = 63014`, with Kong host `search.localhost`.
- `OPEN_WEB_UI_PORT = BASE_PORT + 15 = 63015`, with Kong host `chat.localhost`.
- `JUPYTERHUB_PORT = BASE_PORT + 48 = 63048`, with Kong host `jupyter.localhost`.

Impact:

New users may open Kong root and see Supabase Studio instead of n8n. This is likely the first thing users try.

Recommended fix:

Replace Quick Start access lines with direct and Kong forms, for example:

- Open WebUI: direct `http://localhost:63015`, gateway `http://chat.localhost:63002`
- n8n: direct `http://localhost:63017`, gateway `http://n8n.localhost:63002`
- Supabase Studio: direct `http://localhost:63009`, gateway `http://localhost:63002`
- SearxNG: direct `http://localhost:63014`, gateway `http://search.localhost:63002`
- ComfyUI: direct `http://localhost:63018`, gateway `http://comfyui.localhost:63002`
- JupyterHub: direct `http://localhost:63048`, gateway `http://jupyter.localhost:63002`
- Backend API: direct `http://localhost:63016`, gateway `http://api.localhost:63002`
- OpenClaw: direct `http://localhost:63024`, gateway `http://openclaw.localhost:63002`

---

### H2. `BASE_PORT` is documented as an env var, but `.env.example` does not define it

Evidence:

Docs repeatedly say all ports are offset from `BASE_PORT`, and `docs/deployment/submodule-usage.md` shows:

```env
BASE_PORT=64000
```

But `.env.example` does not contain `BASE_PORT` at all. The actual default is `DEFAULT_BASE_PORT = 63000` in `bootstrapper/core/config_parser.py`, and `bootstrapper/core/port_manager.py` rewrites each individual `*_PORT` variable.

There is also new Textual integration code referencing `BASE_PORT`, but classic port management is based on concrete service port vars.

Impact:

Users who add `BASE_PORT=64000` to `.env` may believe ports will recompute, but the main documented path is `./start.sh --base-port 64000`, which rewrites concrete `*_PORT` entries. This is a serious config mental-model mismatch.

Recommended fix:

Choose and document one canonical model:

A. `BASE_PORT` is real:
- Add `BASE_PORT=63000` to `.env.example`.
- Make port manager read it and recompute ports at startup.
- Keep per-service overrides clear.

B. `--base-port` is the only supported base-port API:
- Remove `BASE_PORT=...` examples from docs.
- Explain that `--base-port` rewrites concrete `*_PORT` values in `.env`.
- Keep `DEFAULT_BASE_PORT` documented as an internal default constant.

---

### H3. SOURCE docs use wrong external variable for Ollama

Evidence:

`docs/deployment/source-configuration.md` documents:

```env
LLM_PROVIDER_SOURCE=ollama-external
OLLAMA_EXTERNAL_URL=https://your-ollama-api.com
```

Actual `.env.example` uses:

```env
LLM_PROVIDER_EXTERNAL_URL=  # Required when SOURCE=ollama-external
```

Actual `bootstrapper/service-configs.yml` uses:

```yaml
OLLAMA_ENDPOINT: "${LLM_PROVIDER_EXTERNAL_URL}"
```

Impact:

Users following docs will set `OLLAMA_EXTERNAL_URL`, which the stack does not consume for `ollama-external`.

Recommended fix:

Update all docs to use `LLM_PROVIDER_EXTERNAL_URL`, or add backward-compatible support for `OLLAMA_EXTERNAL_URL` and document deprecation.

---

### H4. ComfyUI localhost docs disagree on port 8188 vs implementation port 8000

Evidence:

`docs/deployment/source-configuration.md` says ComfyUI localhost requires `localhost:8188` and starts with:

```bash
python main.py --port 8188
```

Implementation uses:

- `bootstrapper/service-configs.yml`: `COMFYUI_ENDPOINT: "http://host.docker.internal:8000"`
- `bootstrapper/utils/kong_config_generator.py`: checks `localhost:8000` and routes to `http://host.docker.internal:8000/`
- `README.md` architecture diagram also shows `host.docker.internal:8000`.

Impact:

A user following the SOURCE guide will start ComfyUI on 8188, but the stack will route to 8000.

Recommended fix:

Either standardize on 8188, which is ComfyUI's common native default, or standardize on 8000. Then update:

- `service-configs.yml`
- `kong_config_generator.py`
- `.env.example`
- README
- SOURCE docs
- troubleshooting docs

---

### H5. ComfyUI external mode is documented but `.env.example` does not define `COMFYUI_EXTERNAL_URL`

Evidence:

- CLI supports `--comfyui-source external`.
- `service-configs.yml` has `external` but hardcodes `http://external.comfyui.provider.com` in the YAML environment.
- `kong_config_generator.py` expects `COMFYUI_EXTERNAL_URL` and returns no route if missing.
- `.env.example` does not contain `COMFYUI_EXTERNAL_URL`.
- `docs/deployment/source-configuration.md` documents `COMFYUI_EXTERNAL_URL`.

Impact:

External ComfyUI is a documented and CLI-supported mode, but users do not get a template variable in `.env.example`, and internal config has a placeholder URL that could be misleading.

Recommended fix:

- Add `COMFYUI_EXTERNAL_URL=` to `.env.example`.
- Remove hardcoded provider placeholder from `service-configs.yml` or make it `${COMFYUI_EXTERNAL_URL}`.
- Add validation that fails early with a clear message when `COMFYUI_SOURCE=external` and URL is missing.

---

### H6. OpenClaw localhost docs use native port 18789, while stack expects 63024 by default

Evidence:

`docs/services/openclaw.md` Localhost Mode says:

```bash
openclaw gateway --port 18789
```

But `.env.example` and service config expect localhost OpenClaw at:

```env
OPENCLAW_LOCALHOST_URL=http://host.docker.internal:63024
OPENCLAW_GATEWAY_PORT=63024
```

`bootstrapper/services/service_config.py` uses `OPENCLAW_GATEWAY_PORT` to build the localhost endpoint.

Impact:

A user following the OpenClaw localhost doc will run OpenClaw on 18789, but the stack will try to reach 63024 unless they also override `OPENCLAW_LOCALHOST_URL` or `OPENCLAW_GATEWAY_PORT`.

Recommended fix:

Update docs to either:

- run native gateway on 63024: `openclaw gateway --port 63024`, or
- explicitly set `OPENCLAW_LOCALHOST_URL=http://host.docker.internal:18789` before starting the stack.

---

### H7. Python version requirements are inconsistent

Evidence:

- `README.md` says Python 3.10+.
- `bootstrapper/pyproject.toml` says `requires-python = ">=3.9"`.
- `docs/quick-start/interactive-setup-wizard.md` says Python >= 3.9.
- `docs/CHANGELOG.md` says the project bumped from >=3.8 to >=3.9.

Impact:

Users and contributors do not know whether 3.9 is supported. CI/test docs would be ambiguous.

Recommended fix:

Pick the real supported floor. If Textual stack works on 3.9, update README to 3.9+. If the repo wants 3.10+, update `pyproject.toml`, docs, and changelog language.

---

## Architecture Diagram Issues

### A1. There are three architecture diagram sources that can drift

Files:

- `docs/images/architecture.png` referenced by `README.md`
- `docs/diagrams/architecture.svg`
- `docs/diagrams/architecture.html`
- `docs/diagrams/architecture.mermaid`
- `docs/diagrams/generate_diagram.sh`

Observed issue:

The README displays `docs/images/architecture.png`, but there is also an SVG/HTML diagram and a Mermaid file with different abstraction levels and content. There is no documented rule identifying the canonical source.

Impact:

Future service/dependency changes may update one diagram but not the others.

Recommended fix:

- Declare one canonical source, preferably `docs/diagrams/architecture.html` or SVG if it is hand-designed.
- Add a README note: "Generated PNG comes from X via Y command. Do not edit generated output directly."
- Add a CI/check script that fails if generated PNG/SVG is stale.

---

### A2. Mermaid architecture claims broad modes and generated compose behavior that are not precise

Evidence:

`docs/diagrams/architecture.mermaid` says:

- Services can run as `container-cpu`, `container-gpu`, `localhost`, `external`, `api`, or `disabled`.
- `start.sh` is a `YAML Parser & Env Generator`.
- `start-sh -- Generated Environment Variables --> docker-compose.yml`.
- `disabled: Service not started (scale=0)`.

Problems:

- Not every service supports every mode.
- The bootstrapper does not generate `docker-compose.yml`; it updates `.env` and generates Kong config.
- Some disabled modes are not actually supported, notably Backend.
- Some services are hidden behind profiles, not just `deploy.replicas`.

Recommended fix:

Make the diagram distinguish:

- Static compose file: `docker-compose.yml`
- Generated/updated runtime files: `.env`, `volumes/api/kong-dynamic.yml`
- SOURCE matrix: `service-configs.yml`
- Profiles: GPU-only optional services
- Scale-to-zero behavior vs true compose exclusion

---

### A3. Architecture HTML/SVG dependency cards overstate or misstate dependencies

Evidence:

`docs/diagrams/architecture.html` dependency card says:

- Backend -> Ollama, Weaviate, Neo4j, Redis, SearxNG, n8n, Supabase DB, Parakeet, XTTS, Docling
- n8n -> Ollama, Weaviate required, Parakeet, XTTS, Docling
- OpenClaw -> Ollama optional

Implementation shows:

- Backend compose `depends_on`: `supabase-db-init`, `redis`, `supabase-storage`, `supabase-realtime`, `kong-api-gateway`.
- Backend adaptive config includes LLM, Weaviate, STT, TTS, Docling, but dependency YAML marks most as optional.
- `service-configs.yml` says n8n adapts to STT/TTS/Docling; it does not list Ollama in n8n adaptive config. n8n may use Ollama at workflow level, but that is not modeled as a startup dependency.
- OpenClaw dependency YAML says optional `[ollama]`, but its actual LLM support also includes Anthropic/OpenAI envs.

Impact:

The diagram mixes compose startup dependencies, runtime integrations, and optional feature-level connections without labeling them. This makes it hard to reason about what must be enabled.

Recommended fix:

Use separate edge styles:

- solid = compose `depends_on`
- dashed = adaptive runtime endpoint injection
- dotted = optional feature integration
- warning marker = dependency currently stale/needs modeling

---

### A4. Kong route list in docs is incomplete

Evidence:

`docs/services/kong.md` Dynamic Routes lists:

- `comfyui.localhost`
- `n8n.localhost`
- `search.localhost`
- `api.localhost`
- `chat.localhost`

Actual `kong_config_generator.py` also creates:

- `jupyter.localhost`
- `openclaw.localhost`

Recommended fix:

Update Kong docs and the main README service access table with all current route hosts.

---

## Service Documentation Coverage Gaps

### D1. Major first-class services have no dedicated service docs

`docs/services/` currently has docs for:

- STT Provider
- TTS Provider
- Document Processor
- Supabase
- Neo4j
- Kong
- JupyterHub
- OpenClaw

Missing dedicated docs for first-class services in compose/config:

- Ollama / LLM Provider
- Open WebUI
- n8n and n8n-worker
- SearxNG
- Weaviate
- Redis
- Local Deep Researcher
- Multi2Vec CLIP
- ComfyUI
- Backend API

Impact:

The services users are most likely to interact with are documented only in the main README or not documented at all. This also causes dependency details to be duplicated inconsistently across README, diagrams, and SOURCE docs.

Recommended fix:

Create service docs for at least:

1. `services/ollama.md`
2. `services/open-webui.md`
3. `services/n8n.md`
4. `services/weaviate.md`
5. `services/comfyui.md`
6. `services/backend.md`
7. `services/searxng.md`
8. `services/local-deep-researcher.md`
9. `services/multi2vec-clip.md`
10. `services/redis.md`

Each should include:

- SOURCE options
- Direct and Kong URLs
- Environment variables
- Compose service names
- Dependencies: compose/startup/runtime/optional
- Common failure modes

---

### D2. README project structure is stale

Evidence:

`README.md` shows:

```text
genai-vanilla/
├── bootstrapper/
├── services/
├── volumes/
├── docs/
├── docker-compose.yml
├── .env.example
├── start.sh
└── stop.sh
```

There is no top-level `services/` directory in the inspected repo. Actual top-level service directories include `backend`, `comfyui-init`, `doc-processor`, `graph-db`, `jupyterhub`, `local-deep-researcher`, `n8n`, `open-webui`, `searxng`, `stt-provider`, `supabase`, `tts-provider`, `weaviate-init`, etc.

Recommended fix:

Replace the project tree with the actual top-level structure and explain which directories are service source/config dirs versus generated volumes.

---

### D3. JupyterHub docs recommend editing `docker-compose.yml` directly

Evidence:

`docs/services/jupyterhub.md` Advanced Configuration says:

```text
If using GPU-enabled services, add to docker-compose.yml:
...
```

This conflicts with the repo's architecture and contributor guidance: service configuration should go through SOURCE variables, `service-configs.yml`, and the bootstrapper, not ad-hoc direct compose edits.

Impact:

Users may make local compose edits that are not represented in docs, diagrams, or SOURCE management.

Recommended fix:

Replace with a SOURCE-aware approach or state that JupyterHub GPU access is not currently managed by the bootstrapper and requires an explicit tracked feature.

---

### D4. Changelog has a broken local docs link

Evidence:

`docs/CHANGELOG.md` ends with:

```md
[documentation](docs/README.md)
```

From inside `docs/CHANGELOG.md`, this resolves to `docs/docs/README.md`, which does not exist.

Recommended fix:

Change to `[documentation](README.md)` or `[documentation](./README.md)`.

---

## SOURCE Matrix and Environment Documentation Issues

### S1. SOURCE support matrix omits several configurable services

Evidence:

`docs/deployment/source-configuration.md` lists localhost-supporting services and container-only services, but omits or under-documents:

- STT Provider
- TTS Provider
- Document Processor
- JupyterHub
- Neo4j localhost option
- Multi2Vec CLIP
- Local Deep Researcher
- Supabase component SOURCE vars
- Kong SOURCE var
- init services and how they are auto-managed

Actual `.env.example` has 30 `*_SOURCE` variables.

Impact:

The SOURCE guide does not function as the canonical SOURCE matrix.

Recommended fix:

Generate the matrix from `bootstrapper/service-configs.yml` and `.env.example`, or maintain a table with every `*_SOURCE` variable and mark:

- user-facing vs internal/auto-managed
- allowed values
- default
- compose service(s) affected
- scale variable(s) generated
- profile(s) activated

---

### S2. `LLM_PROVIDER_SOURCE=api` is underspecified and may be misleading

Evidence:

`service-configs.yml` sets for `api`:

```yaml
OLLAMA_ENDPOINT: "http://api.provider.com"  # Configure API endpoint
```

Docs say cloud APIs are configured in Open WebUI/database/API keys. However the backend, Weaviate, JupyterHub, and other components often expect Ollama-like endpoints or receive `OLLAMA_BASE_URL`/`OLLAMA_ENDPOINT`.

Impact:

Users may expect `api` to provide a working stack-wide LLM endpoint. In practice, `api` seems more like "do not run Ollama; let UI/provider-specific configuration handle it". That distinction is not clearly documented.

Recommended fix:

Document exactly what `api` means per consumer:

- Open WebUI behavior
- Backend behavior
- Weaviate behavior
- JupyterHub notebooks
- Ollama model pull behavior

If `http://api.provider.com` is a placeholder only, remove it from generated envs or replace with empty/explicit disabled behavior.

---

### S3. Init service behavior is inconsistently explained

Evidence:

- `.env.example` exposes init SOURCE vars like `OLLAMA_PULL_SOURCE`, `WEAVIATE_INIT_SOURCE`, `COMFYUI_INIT_SOURCE`, `N8N_INIT_SOURCE`, `OPENCLAW_INIT_SOURCE`.
- Comments say they are auto-managed by parent services.
- Docs do not consistently explain which init containers still run for localhost modes.
- `COMFYUI_INIT_SCALE` runs for localhost and container when ComfyUI is enabled.
- `OLLAMA_PULL_SCALE` runs for `ollama-localhost` and `ollama-external`, but not `api` or `disabled`.

Impact:

Users may not know why init containers run when the parent service is localhost/external, or when they should disable them.

Recommended fix:

Add an "Auto-managed init services" section to SOURCE docs and architecture diagram.

---

## Recommended Fix Plan

### Phase 1: Stop user-facing setup failures

1. Fix README Quick Start URL table.
2. Fix `LLM_PROVIDER_EXTERNAL_URL` docs.
3. Fix ComfyUI localhost port mismatch.
4. Fix OpenClaw localhost port instructions.
5. Fix `BACKEND_SOURCE=disabled` docs or implementation.
6. Add `COMFYUI_EXTERNAL_URL` to `.env.example` or remove external support from docs/CLI until implemented cleanly.

### Phase 2: Dependency model cleanup

1. Normalize service names across:
   - compose service names
   - SOURCE keys
   - scale vars
   - dependency YAML
   - docs and diagrams
2. Fix `DependencyManager.get_service_scale()` alias handling.
3. Audit static `depends_on` against SOURCE modes.
4. Decide whether generated compose overlays are needed for localhost/external/disabled modes.
5. Add tests for common configurations:
   - default CPU
   - Ollama localhost
   - minimal API/no local AI
   - Weaviate disabled
   - JupyterHub with localhost/external dependencies
   - STT+TTS+Docling GPU enabled together

### Phase 3: Architecture and docs consolidation

1. Declare canonical architecture diagram source.
2. Update diagram edge semantics.
3. Regenerate PNG/SVG consistently.
4. Fill service docs coverage gaps.
5. Generate SOURCE matrix docs from `service-configs.yml` or add a check that fails on drift.

### Phase 4: Add automated drift checks

Add a small script such as `scripts/check_docs_drift.py` that verifies:

- Every `*_SOURCE` in `.env.example` appears in SOURCE docs or is explicitly marked internal.
- Every CLI SOURCE option appears in docs.
- Every Kong host route appears in Kong docs and README access table.
- Every port mapping appears in the access table or generated docs.
- Every docs local Markdown link resolves.
- Architecture generated assets are up-to-date with canonical source.

---

## Suggested Ownership

- Documentation owner: README, docs index, service docs, architecture diagrams.
- Bootstrapper owner: SOURCE validation, dependency manager, port/base-port semantics.
- Compose owner: `depends_on` audit and profiles/scales behavior.
- QA owner: add configuration matrix smoke checks.

## Bottom Line

The repo has evolved quickly: Textual wizard, OpenClaw, JupyterHub, LangMem, Docling/STT/TTS, dynamic Kong, and SOURCE-driven config all exist at once. The documentation still mixes older assumptions with newer implementation details. The highest-value cleanup is to make `service-configs.yml`, `.env.example`, `docker-compose.yml`, and docs agree on a single canonical model for:

- service names,
- SOURCE values,
- scale variables,
- routes and ports,
- startup dependencies,
- runtime optional integrations,
- generated vs static files.

Until that happens, users can follow documented setup paths that do not match what the bootstrapper and compose file actually do.
