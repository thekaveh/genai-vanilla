# Changelog

All notable changes to the GenAI Vanilla Stack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **OpenClaw AI Agent**: AI agent for messaging platforms (WhatsApp, Telegram, Discord, etc.)
  - Connects to messaging apps for AI-powered chat, file management, and task automation
  - Web dashboard for administration at `openclaw.localhost`
  - LLM integration: inherits stack's Ollama endpoint, supports Anthropic/OpenAI API keys
  - SOURCE options: `container`, `localhost` (Node.js 22+), `disabled` (default)
  - CLI option: `--openclaw-source [container|localhost|disabled]`
  - Default ports: 63024 (gateway, offset +24), 63025 (bridge, offset +25)
  - Kong routing via `openclaw.localhost` subdomain
- **JupyterHub Data Science IDE**: Interactive Jupyter Lab environment with pre-configured AI/ML libraries
  - 7 sample notebooks demonstrating all service integrations (Ollama, Weaviate, Neo4j, Supabase, ComfyUI, n8n, SearxNG)
  - Pre-installed libraries: Ollama, LangChain, LlamaIndex, Transformers, Weaviate client, Neo4j driver, and more
  - Kong routing support via `jupyter.localhost` domain
  - Persistent workspace with Docker volumes (`jupyterhub-data`)
  - Adaptive service that auto-configures based on available AI services
  - CLI option: `--jupyterhub-source [container|disabled]`
  - Default port: 63048 (offset +48 from base port)
  - Environment check notebook for service connectivity verification
- **Textual-based bootstrapper TUI**: A single Textual app (`bootstrapper/ui/textual/`) now owns the entire interactive experience — wizard prompts, the CLI-flag launch screen, the pre-launch pipeline (apply overrides → validate → ports → kong → supabase keys → hosts → encryption → localhost), and the live `docker compose` build / up / verify / `logs -f` stream — all rendered in one screen with a pinned info-box, a service overview, and a bordered log pane with filter chips. Press `ctrl+q` to detach (the stack keeps running). `--no-tui` falls back to a linear stdout flow for CI / non-TTY shells.
- **Brand customization via `BRAND_*` env vars**: The wizard's brand panel and info-box title / subtitle metadata (brand name, tagline, version, author, author email, license, repo URL) is overridable via `BRAND_NAME`, `BRAND_TAGLINE`, `BRAND_VERSION`, `BRAND_AUTHOR`, `BRAND_AUTHOR_EMAIL`, `BRAND_LICENSE`, `BRAND_REPO_URL` in `.env`. Defaults are GenAI Vanilla; forks can rebrand without code changes.
- **Always-on Supabase services in the bootstrapper overview**: `Supabase Auth`, `Supabase API`, `Supabase Realtime`, `Supabase Storage`, and `Supabase Meta` are now surfaced as rows in both the Textual `ServiceTable` and the `--no-tui` summary table, alongside Supabase DB and Studio.
- **`docs/scripts/check-compose-source-deps.py`**: Preventative linter that verifies `docker-compose.yml` does not declare hard `depends_on` edges from any service to a SOURCE-replaceable provider, and that core `depends_on` edges are still in place.
- **`docs/scripts/check-kong-routes.py`**: Preventative linter that verifies the checked-in Kong fallback config (`volumes/api/kong-dynamic.yml`) matches the documented default routes for `comfyui.localhost`, `n8n.localhost`, `search.localhost`, `jupyter.localhost`, `api.localhost`, and `chat.localhost`.
- **`docs/deployment/ports-and-routes.md`**: Canonical reference for `BASE_PORT` math, every service's direct localhost URL, and Kong host routes.
- **Per-service documentation expansion** under `docs/services/`: `backend.md`, `comfyui.md`, `local-deep-researcher.md`, `multi2vec-clip.md`, `n8n.md`, `ollama.md`, `open-webui.md`, `redis.md`, `searxng.md`, `weaviate.md` now have their own pages alongside the existing in-depth docs.
- **ROADMAP additions**: Tier 1 — unified LLM gateway (LiteLLM, or equivalent) and per-service configuration modularization. Tier 2 — Hermes Agent (Nous Research's programmable agent runtime, with Open WebUI integration link) and MinIO (S3-compatible object storage).
- New documentation structure under `/docs/`, ROADMAP.md, and this CHANGELOG.

### Changed
- **Loosened `depends_on` edges for SOURCE-replaceable providers**: `n8n`, `n8n-worker`, and `jupyterhub` no longer hard-depend on `weaviate` (`jupyterhub` also no longer hard-depends on `ollama` or `neo4j-graph-db`); `weaviate` no longer hard-depends on `multi2vec-clip`. `n8n` / `n8n-worker` / `jupyterhub` now depend on `supabase-db-init` instead of `supabase-db`. Optional consumers use `WEAVIATE_URL` (and equivalent endpoint env vars) plus runtime readiness checks instead of static compose dependencies — the stack still starts when those providers are disabled, localhost-backed, or externalized.
- **Weaviate module configuration now `.env`-driven**: `WEAVIATE_ENABLE_MODULES` and `CLIP_INFERENCE_API` are exposed in `.env.example` and consumed by the Weaviate compose service. Disabling the CLIP provider no longer requires editing `docker-compose.yml` — set `MULTI2VEC_CLIP_SOURCE=disabled`, drop `multi2vec-clip` from `WEAVIATE_ENABLE_MODULES`, and clear `CLIP_INFERENCE_API`.
- **Service-definition consolidation**: `bootstrapper/ui/state_builder.all_services()` is the single source of truth for the canonical service list, consumed by both the Textual `ServiceTable` and the `--no-tui` summary table. No duplicated inline service tables.
- **Single `DEFAULT_BASE_PORT`**: Lives in `bootstrapper/core/config_parser.py`; `start.py` and the wizard import the same constant.
- **README.md restructuring** for better usability and new documentation organization / navigation.
- **Architecture diagrams updated** to include JupyterHub and other recently added services.

### Removed
- **Legacy Rich-based bootstrapper UI** (the Rich `Live` + `readchar` wizard, the `Textual` post-wizard log app, and all of their supporting modules): `bootstrapper/ui/presentation_app.py`, `bootstrapper/ui/log_stream_app.py`, `bootstrapper/ui/select_widget.py`, `bootstrapper/ui/number_widget.py`, `bootstrapper/ui/status_ribbon.py`, `bootstrapper/ui/log_pane.py`, `bootstrapper/ui/info_box.py`, `bootstrapper/ui/palette.py`, `bootstrapper/ui/logo.py`, and `bootstrapper/wizard/tui_wizard.py`. The `GENAI_USE_LEGACY_WIZARD=1` env-var fallback that briefly let users opt back into the Rich Live wizard during the migration is also gone.
- **Earlier obsolete bootstrapper modules folded into the wizard rebuild**: `wizard/interactive_wizard.py`, `wizard/prompts.py`, `wizard/ui_renderer.py`, `utils/scroll_pin.py`, `utils/ansi_filter.py`, `ui/services_poller.py`, `ui/confirm_widget.py`. Pruned dead methods (`up_with_build`, `set_service_state`, `apply_service_snapshot`, `clear_status`, `prompt_confirm`), dead palette helpers (`style_for_service_state`, `dot_for_service_state`, `DOT_STARTING`, `DOT_OFF`, `DOT_UNHEALTHY`, `COLOR_STARTING`), and unused state constants / `ServiceEntry` fields (`SERVICE_STATE_*`, `GROUP_*`, `CATEGORY_*`, `state`, `group`, `category`, `is_default_source`, `endpoints`).

### Fixed
- **Kong route generator now honors `COMFYUI_LOCALHOST_URL`**: `bootstrapper/utils/kong_config_generator.py` previously hardcoded `http://host.docker.internal:8000/` for the `comfyui-api` route under `COMFYUI_SOURCE=localhost`, ignoring any `.env` override. It now parses `COMFYUI_LOCALHOST_URL` and uses its host:port for both the Kong service URL and the localhost reachability probe (matching the openclaw generator's per-service env-var pattern).

### Dependencies
- Added `textual >= 0.85` — owns the entire wizard / launch / log-streaming experience.
- Removed `readchar` (was used by the now-deleted Rich Live prompt widgets).
- Removed `InquirerPy` (replaced earlier in this `[Unreleased]` cycle).
- Bumped `requires-python` from `>=3.8` to `>=3.9` (Textual minimum).

## [2.0.0] - 2025-08-31 (Python Migration & Modular Architecture)

### Added

#### Python migration
- **Cross-platform Python bootstrapper**: Complete migration from Bash to Python for start/stop scripts
- **UV package manager support**: Automatic detection and use of UV for better dependency management
- **Enhanced error handling**: Better error messages and recovery mechanisms
- **Consistent behavior**: Same functionality across Windows, macOS, and Linux

#### Dynamic Kong configuration
- **Intelligent routing**: Kong routes dynamically generated based on SOURCE values
- **Health checking**: Automatic localhost service availability checking
- **Adaptive configuration**: Routes automatically removed for disabled services
- **No manual configuration**: Replaced static kong.yml/kong-local.yml files

#### CLI SOURCE overrides
- **Command-line configuration**: Override .env settings via CLI arguments
- **Temporary sessions**: CLI overrides don't modify .env file
- **All SOURCE types supported**: Complete CLI coverage for all service sources
- **Usage examples**: CLI documentation with common patterns

#### Enhanced service management
- **ComfyUI-init for all sources**: Model downloading for both container and localhost setups
- **Better dependency resolution**: Automatic service dependency management
- **Improved startup order**: Cold start cleanup moved to proper execution phase

### Changed

#### Project structure
- **Reorganized bootstrapper**: New `bootstrapper/` directory with Python modules
- **Service utilities**: `bootstrapper/utils/kong_config_generator.py` for dynamic configuration
- **Moved scripts**: `generate_supabase_keys.sh` relocated to `bootstrapper/`
- **Modular architecture**: Clear separation of concerns in codebase

#### Kong gateway
- **Dynamic route generation**: Routes created based on active services
- **SOURCE-aware**: Different routing strategies for container/localhost/external sources
- **WebSocket support**: Proper WebSocket routing for realtime services
- **Authentication handling**: Dynamic auth configuration per service

#### Service configuration
- **SOURCE system refinement**: Clear documentation of which services support localhost
- **Localhost support clarification**: Only Ollama, ComfyUI, and Weaviate support localhost SOURCE
- **Container-only services**: N8N, SearxNG, Open-WebUI, Backend API are container-only
- **External URL support**: Proper handling of external service configurations

### Fixed

#### Startup issues
- **Cold start port conflicts**: Fixed cleanup order to occur before port checking
- **Service initialization**: ComfyUI-init now runs for localhost ComfyUI setups
- **Port management**: Better handling of port conflicts and base port configuration

#### Integration issues
- **Kong routing**: Fixed localhost service routing through Kong gateway
- **Service discovery**: Proper health checking for localhost services
- **Cross-service communication**: Improved service-to-service connectivity

#### Documentation
- **Corrected SOURCE support**: Fixed incorrect localhost support claims
- **Updated examples**: All examples reflect new dynamic configuration approach
- **Consistent terminology**: Standardized language throughout documentation

### Removed

#### Obsolete files
- **Static Kong configuration**: Removed `volumes/api/kong.yml` and `volumes/api/kong-local.yml`
- **Dual configuration approach**: Eliminated the "relic" dual Kong config system
- **Manual route configuration**: Removed need for manual Kong route management

#### Cleanup
- **Unnecessary Kong routes**: Removed routes for Weaviate and Neo4j (not user-facing)
- **Duplicate documentation**: Consolidated multiple sections about same services
- **Outdated references**: Removed references to legacy Bash-only approach

## [1.5.0] - 2025-07-29 (Service Integration & Workflow Enhancement)

### Added

#### n8n workflow automation
- **Complete n8n integration**: Workflow automation with queue management
- **Redis queue backend**: Distributed task processing with n8n-worker
- **Pre-built workflows**: Ready-to-use AI workflow templates
- **Kong gateway routing**: Access via n8n.localhost subdomain

#### ComfyUI image generation
- **Full ComfyUI integration**: AI image generation with workflow support
- **Multiple deployment options**: Container CPU/GPU and localhost support
- **Model management**: Automatic model downloading and caching
- **API integration**: REST API access and workflow execution

#### SearxNG privacy search
- **Privacy-focused search**: Local search aggregation without tracking
- **Multiple search engines**: Aggregated results from various sources
- **API access**: Programmatic search capabilities for AI workflows
- **Rate limiting**: Built-in protection against abuse

#### Open WebUI enhancement
- **Research tools integration**: AI-powered research capabilities
- **ComfyUI tool integration**: Direct image generation from chat
- **Multi-LLM support**: Support for various LLM providers
- **Custom tool development**: Framework for adding new AI tools

### Changed

#### Architecture improvements
- **Service modularity**: Better separation between services
- **Docker network optimization**: Improved inter-service communication
- **Volume management**: More efficient data persistence
- **Resource allocation**: Better memory and CPU management

#### Configuration enhancement
- **Environment-based scaling**: Services scale based on SOURCE configuration
- **Dependency management**: Automatic service dependency resolution
- **Health monitoring**: Better service health checking and recovery

### Fixed

#### Bug fixes
- **Service startup order**: Fixed dependency-based startup sequencing
- **Memory management**: Resolved OOM issues with large models
- **Network connectivity**: Fixed inter-service communication issues
- **Volume permissions**: Resolved file permission problems

## [1.0.0] - 2025-04-26 (Initial Release)

### Added

#### Core foundation
- **Supabase ecosystem**: Complete database, auth, and storage solution
- **Kong API Gateway**: Centralized API management and routing
- **Ollama integration**: Local LLM inference with CPU/GPU support
- **Docker Compose architecture**: Complete containerized environment

#### Database services
- **PostgreSQL**: Primary database with Supabase extensions
- **Neo4j**: Graph database for relationship modeling
- **Redis**: Caching and session management
- **Real-time subscriptions**: WebSocket-based live data updates

#### Authentication and security
- **Supabase Auth**: Complete authentication system
- **JWT token management**: Secure API access tokens
- **Role-based access**: User roles and permissions
- **API key authentication**: Service-to-service security

#### Development tools
- **Supabase Studio**: Database management interface
- **Environment configuration**: Flexible .env-based setup
- **Docker orchestration**: Multi-service container management
- **Development scripts**: Easy start/stop scripts

### Infrastructure

#### Container architecture
- **Service isolation**: Each component in dedicated container
- **Network segmentation**: Proper Docker networking
- **Volume persistence**: Data persistence across restarts
- **Resource management**: Memory and CPU optimization

#### Configuration management
- **Environment variables**: Centralized configuration
- **Service discovery**: Automatic service registration
- **Port management**: Configurable port assignments
- **Cross-platform support**: Works on macOS, Linux, and Windows

---

## Migration Guide

### From 1.x to 2.0 (Python Migration)

**Required Actions:**
1. **Update start/stop usage**: New CLI arguments available
2. **Check SOURCE configurations**: Verify localhost support for your services
3. **Update hosts file**: Run `./start.sh --setup-hosts` for *.localhost domains
4. **Review Kong routes**: Routes now generated dynamically

**Optional Improvements:**
- Install UV package manager for better dependency management
- Use new CLI SOURCE overrides for easier configuration
- Leverage new troubleshooting documentation

**Breaking Changes:**
- Static `kong.yml` files no longer used (automatically migrated)
- Some services no longer support localhost SOURCE (see documentation)
- `generate_supabase_keys.sh` moved to `bootstrapper/` directory

### Compatibility Notes

- **Environment files**: Existing `.env` files remain compatible
- **Data volumes**: All data preserved across updates
- **Service APIs**: No changes to service endpoints or functionality
- **Docker images**: Updated but backward compatible

---

## Acknowledgments

### Contributors
- Core development team
- Community contributors
- Beta testers and early adopters

### Special Thanks
- Open source projects that make this stack possible
- Community feedback and feature requests
- Documentation contributors and reviewers

---

*For more details on any release, see the corresponding [GitHub release](https://github.com/thekaveh/genai-vanilla/releases) or [documentation](README.md).*