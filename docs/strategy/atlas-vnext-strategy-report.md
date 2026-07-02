# Atlas vNext Strategy Report

## 1. Executive Summary

Task 1 placeholder. Later tasks should replace this section with the final strategy summary, decision framing, and top recommendations.

## 2. Current-State Assessment

Task 1 internal evidence inventory:

- Repo inventory snapshot for this report pass: `34` `services/*/service.yml` manifests, `21` integration research row files in `docs/research/rows/`, and `34` candidate one-pagers in `docs/research/candidates/`.
- `docs/research/integration-matrix.md` currently indexes `21` service research rows across categories and `34` candidate services, which gives later sections a repo-local starting point before any external validation.
- Current track registry in `bootstrapper/tracks.yml` defines six track keys: `gen-ai-rag`, `gen-ai-eng`, `gen-ai-creative`, `ml-eng`, `data-eng`, and `all`.
- Scoped track membership snapshot:
  - `gen-ai-rag`: `open-webui`, `weaviate`, `neo4j`, `lightrag`, `doc-processor`, `tei-reranker`, `searxng`, `local-deep-researcher`
  - `gen-ai-eng`: `open-webui`, `n8n`, `hermes`, `openclaw`, `jupyterhub`, `comfyui`, `stt-provider`, `tts-provider`, `searxng`, `local-deep-researcher`
  - `gen-ai-creative`: `open-webui`, `comfyui`, `stt-provider`, `tts-provider`, `multi2vec-clip`, `doc-processor`
  - `ml-eng`: `spark`, `ray`, `jupyterhub`, `zeppelin`, `open-webui`, `minio`, `tei-reranker`
  - `data-eng`: `spark`, `airflow`, `jupyterhub`, `zeppelin`, `minio`, `weaviate`, `neo4j`
  - `all`: no filtering; every configurable service remains available
- Track-context note for later analysis: the registry already expresses broad AI, RAG, creative, ML, and data personas, but only as service-selection profiles; later tasks should assess whether those profiles feel productized enough for onboarding and roadmap positioning.

### 2.1 Strengths

Atlas already has a coherent platform grammar. The repo does not read like an accreted pile of one-off compose services; it reads like a system that standardized its operating model and then kept extending it. That matters because Atlas' main strategic asset is not any one service, but the repeatable way it wires heterogeneous services into one local platform.

- **Source-configurable service model with consistent deployment semantics.** The README's overview and SOURCE-system sections describe a shared contract across the stack: services are selected through SOURCE variables, the common modes are `container`, `localhost`, and `disabled`, and the LLM layer adds a cloud passthrough path through LiteLLM. `docs/CONTRIBUTING-services.md` reinforces the same contract for maintainers by standardizing source variants, localhost port overrides, runtime slices, and per-service manifests. The manifest inventory shows that this is not just documentation language: most configurable services expose the same operational choices, which gives Atlas unusual deployment flexibility for a compose-native AI stack.

- **Kong-centered routing with predictable `*.localhost` aliases.** Atlas has a clear access model rather than a random port jungle. `docs/deployment/ports-and-routes.md` defines the authoritative route table, and the README mirrors it with both a generated topology table and a browser-facing service overview. Kong fronts chat, notebooks, workflow tools, storage consoles, model gateways, graph and vector stores, and optional observability surfaces behind stable aliases such as `chat.localhost`, `api.localhost`, `litellm.localhost`, and `grafana.localhost`. The Kong service docs also show that route generation is tied to active SOURCE values, so the gateway adapts as services move between container, localhost, and disabled states.

- **Mature manifest, compose-fragment, and docs-generation discipline.** Atlas' internal architecture is more structured than most self-hosted "AI stack" repos. `docs/CONTRIBUTING-services.md` documents the per-service folder contract (`service.yml`, `compose.yml`, local subdirectories), the top-level compose file is intentionally thin, and the contribution workflow requires a regen-and-lint chain before landing changes. The repo guidance also points to concrete safety rails: manifest validation, compose equivalence checks, docs drift tests, Kong route audits, and source-dependency audits. That investment lowers the cost of continuing to expand the platform.

- **Tracks turn breadth into persona-oriented presets.** `bootstrapper/tracks.yml` defines six track keys covering RAG, agent engineering, creative multimodal work, ML engineering, data engineering, and a full-custom mode. The README exposes those tracks directly in quickstart commands and in the wizard flow. This is strategically important: Atlas is broad, but it is not forcing every user to boot every domain at once. The track system is an early productization layer over a large service catalog.

- **Strong self-host primitives across the core workload categories.** The shipped stack already covers the hard infrastructure a serious local AI platform needs: Supabase, Redis, LiteLLM, Kong, MinIO, Weaviate, Neo4j, n8n, Open WebUI, JupyterHub, Ray, Spark, Airflow, Prometheus, and Grafana are all represented in the repo's docs, manifests, and service READMEs. `docs/ROADMAP.md` also distinguishes between what is shipped and what remains candidate work, which makes the current-state boundary legible. The result is that Atlas already spans chat, automation, retrieval, storage, notebooks, distributed compute, and observability without depending on a single hosted control plane.

- **Better-than-usual documentation and drift discipline for a compose-native AI platform.** The README is not the only source of truth; it is backed by generated topology, per-service READMEs, route docs, manifest docs, and repo-level audits. `docs/CONTRIBUTING-services.md` explicitly treats READMEs, diagrams, manifests, and compose fragments as a maintained system, while the roadmap records what has shipped versus what is still only proposed. That documentation posture is a real strength because Atlas' surface area is already large enough that undocumented behavior would quickly become unmanageable.

### 2.2 Weaknesses

- **The root Kong entrypoint is still infrastructure-first rather than product-first.** `services/kong/README.md` and `docs/deployment/ports-and-routes.md` both state that `/` and the bare `localhost` root fall through to Supabase Studio. That is a valid operator shortcut, but it is not an Atlas home experience. The first gateway surface currently points users at an admin console for one subsystem, not at a platform dashboard, workspace selector, system health page, or recommended workflow launcher. For a stack trying to become a cohesive product, the front door is still effectively a routing convenience.

- **Authentication and SSO are fragmented across services.** The README's service overview table shows the problem plainly: Open WebUI uses account creation, n8n uses first-visit owner setup, Supabase Studio is gated by Kong basic auth, Neo4j uses its own credentials, Hermes uses a bearer token, JupyterHub uses an optional token, Grafana uses an admin password, and the backend is "None by default" on local/dev surfaces. The repo already knows this is unfinished: `services/open-webui/README.md` lists OIDC/SSO via Supabase Auth as future work, `services/kong/README.md` lists Keycloak and JWT-plugin options, and `services/supabase/README.md` notes OAuth providers as an easy next step. The building blocks exist, but the platform does not yet behave like it has one identity model.

- **MCP is well-theorized in the roadmap but not yet implemented as a shared runtime capability.** `docs/ROADMAP.md` contains a serious MCP architecture discussion, including aggregator options, a phased starter set, and a coverage matrix of likely targets and consumers. `services/open-webui/README.md` also calls out Open WebUI's native MCP client as future work. But that design has not crossed into the shipped stack: there is no MCP gateway manifest, no shared MCP route in the ports-and-routes table, and no current-state docs describing stack-wide MCP availability. Strategically, Atlas understands the opportunity but has not yet converted it into platform leverage.

- **LLM observability, trace correlation, and evaluation loops lag behind the stack's service breadth.** Atlas has solid infrastructure observability today: the README and roadmap document a shipped Prometheus + Grafana bundle with 13 scrape jobs and 7 starter dashboards. But the same repo evidence is explicit that this is not the whole story. `docs/ROADMAP.md` positions Langfuse as the missing LLM-specific layer for traces, prompts, evals, and cost attribution, and both the roadmap and the Prometheus/Grafana READMEs mark Loki, Tempo, and OpenTelemetry as future work. In other words, Atlas can observe containers and system metrics better than it can observe cross-service LLM behavior.

- **The stack's breadth still risks onboarding overload without a dashboard and stronger guided paths.** The repo inventory for this report pass includes 34 service manifests spread across six categories, while the route docs enumerate a long list of hostnames, direct ports, and auth modes. The wizard and tracks help, and that is a real mitigation, but the user still needs to understand a substantial amount of infrastructure vocabulary to orient themselves. The current docs are good; the experience is still cognitively dense.

- **Vertical-track ambition is ahead of first-class productization.** The roadmap already frames 3D/game-generation, financial/trading-AI, and RAG-enhancement as strategic tracks, but `bootstrapper/tracks.yml` only exposes the current six general-purpose track keys. That gap matters. Atlas has a credible multi-domain substrate, yet its most opinionated future verticals are still roadmap narratives rather than selectable, onboarding-ready product modes. The vision is visible; the product surface has not caught up.

## 3. Competitor Landscape

Task 1 placeholder. Later tasks should replace this section with current competitor categories, comparisons, and source-linked evidence.

## 4. Strategic Gaps

Task 1 placeholder. Later tasks should replace this section with the key platform and product gaps.

## 5. MCP Recommendation

Task 1 placeholder. Later tasks should replace this section with the MCP architecture recommendation and rationale.

## 6. Kong Root Dashboard Recommendation

Task 1 placeholder. Later tasks should replace this section with the recommendation for the main Kong-root Atlas entrypoint experience.

## 7. vNext Top 20

Task 1 placeholder. Later tasks should replace this section with the ranked top 20 candidate list.

## 8. Track Expansion

Task 1 placeholder. Later tasks should replace this section with track-expansion recommendations, including any new verticals.

## 9. Implementation Waves

Task 1 placeholder. Later tasks should replace this section with phased implementation waves derived from the strategy findings.

## 10. Appendices

### 10.1 Source Notes

Task 2 current-state evidence notes:

- `README.md`: current product framing, quickstart flows, SOURCE-system explanation, generated service tables, auth surface summary, and track positioning.
- `docs/ROADMAP.md`: shipped-versus-candidate boundary, observability gap notes, MCP architecture options, and future vertical-track language.
- `docs/deployment/ports-and-routes.md`: authoritative Kong alias table, root-route behavior, and direct evidence of route sprawl.
- `docs/CONTRIBUTING-services.md`: per-service manifest/compose contract, regen-and-lint chain, and maintainability posture.
- `bootstrapper/tracks.yml`: current first-class track registry and its limits relative to roadmap verticals.
- `services/kong/README.md`, `services/open-webui/README.md`, `services/supabase/README.md`, `services/grafana/README.md`: concrete evidence for root-entrypoint behavior, fragmented auth, future SSO work, and current-versus-future observability scope.
