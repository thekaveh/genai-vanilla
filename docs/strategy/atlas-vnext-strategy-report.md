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

- **Source-configurable service model with consistent deployment semantics.** The README's overview and SOURCE-system sections describe a shared contract across the stack: services are selected through SOURCE variables, the common modes are `container`, `localhost`, and `disabled`, and the LLM layer adds a cloud passthrough path through LiteLLM. `docs/CONTRIBUTING-services.md` reinforces the same contract for maintainers by standardizing source variants, localhost port overrides, runtime slices, and per-service manifests. The manifest inventory shows that this is not just documentation language: most configurable services expose the same operational choices, which gives Atlas a broad range of deployment modes inside its current compose-based operating model.

- **Kong-centered routing with predictable `*.localhost` aliases.** Atlas has a clear access model rather than a random port jungle. `docs/deployment/ports-and-routes.md` defines the authoritative route table, and the README mirrors it with both a generated topology table and a browser-facing service overview. Kong fronts chat, notebooks, workflow tools, storage consoles, model gateways, graph and vector stores, and optional observability surfaces behind stable aliases such as `chat.localhost`, `api.localhost`, `litellm.localhost`, and `grafana.localhost`. The Kong service docs also show that route generation is tied to active SOURCE values, so the gateway adapts as services move between container, localhost, and disabled states.

- **Mature manifest, compose-fragment, and docs-generation discipline.** Atlas' internal architecture is explicitly standardized around per-service contracts and generated artifacts. `docs/CONTRIBUTING-services.md` documents the per-service folder contract (`service.yml`, `compose.yml`, local subdirectories), the top-level compose file is intentionally thin, and the contribution workflow requires a regen-and-lint chain before landing changes. The repo guidance also points to concrete safety rails: manifest validation, compose equivalence checks, docs drift tests, Kong route audits, and source-dependency audits. That investment lowers the cost of continuing to expand the platform.

- **Tracks turn breadth into persona-oriented presets.** `bootstrapper/tracks.yml` defines six track keys covering RAG, agent engineering, creative multimodal work, ML engineering, data engineering, and a full-custom mode. The README exposes those tracks directly in quickstart commands and in the wizard flow. This is strategically important: Atlas is broad, but it is not forcing every user to boot every domain at once. The track system is an early productization layer over a large service catalog.

- **Strong self-host primitives across the core workload categories.** The shipped stack already covers the hard infrastructure a serious local AI platform needs: Supabase, Redis, LiteLLM, Kong, MinIO, Weaviate, Neo4j, n8n, Open WebUI, JupyterHub, Ray, Spark, Airflow, Prometheus, and Grafana are all represented in the repo's docs, manifests, and service READMEs. `docs/ROADMAP.md` also distinguishes between what is shipped and what remains candidate work, which makes the current-state boundary legible. The result is that Atlas already spans chat, automation, retrieval, storage, notebooks, distributed compute, and observability without depending on a single hosted control plane.

- **Documentation and drift discipline are treated as part of the product surface.** The README is not the only source of truth; it is backed by generated topology, per-service READMEs, route docs, manifest docs, and repo-level audits. `docs/CONTRIBUTING-services.md` explicitly treats READMEs, diagrams, manifests, and compose fragments as a maintained system, while the roadmap records what has shipped versus what is still only proposed. That documentation posture is a real strength because Atlas' surface area is already large enough that undocumented behavior would quickly become unmanageable.

### 2.2 Weaknesses

- **The root Kong entrypoint is still infrastructure-first rather than product-first.** `services/kong/README.md` and `docs/deployment/ports-and-routes.md` both state that `/` and the bare `localhost` root fall through to Supabase Studio. That is a valid operator shortcut, but it is not an Atlas home experience. The first gateway surface currently points users at an admin console for one subsystem, not at a platform dashboard, workspace selector, system health page, or recommended workflow launcher. For a stack trying to become a cohesive product, the front door is still effectively a routing convenience.

- **Authentication and SSO are fragmented across services.** The README's service overview table shows the problem plainly: Open WebUI uses account creation, n8n uses first-visit owner setup, Supabase Studio is gated by Kong basic auth, Neo4j uses its own credentials, Hermes uses a bearer token, JupyterHub uses an optional token, Grafana uses an admin password, and the backend is "None by default" on local/dev surfaces. The repo already knows this is unfinished: `services/open-webui/README.md` lists OIDC/SSO via Supabase Auth as future work, `services/kong/README.md` lists Keycloak and JWT-plugin options, and `services/supabase/README.md` notes OAuth providers as an easy next step. The building blocks exist, but the platform does not yet behave like it has one identity model.

- **MCP is well-theorized in the roadmap but not yet implemented as a shared runtime capability.** `docs/ROADMAP.md` contains a serious MCP architecture discussion, including aggregator options, a phased starter set, and a coverage matrix of likely targets and consumers. `services/open-webui/README.md` also calls out Open WebUI's native MCP client as future work. But that design has not crossed into the shipped stack: there is no MCP gateway manifest, no shared MCP route in the ports-and-routes table, and no current-state docs describing stack-wide MCP availability. Strategically, Atlas understands the opportunity but has not yet converted it into platform leverage.

- **LLM observability, trace correlation, and evaluation loops lag behind the stack's service breadth.** Atlas has solid infrastructure observability today: the README and roadmap document a shipped Prometheus + Grafana bundle with 13 scrape jobs and 7 starter dashboards. But the same repo evidence is explicit that this is not the whole story. `docs/ROADMAP.md` positions Langfuse as the missing LLM-specific layer for traces, prompts, evals, and cost attribution, and both the roadmap and the Prometheus/Grafana READMEs mark Loki, Tempo, and OpenTelemetry as future work. In other words, Atlas can observe containers and system metrics better than it can observe cross-service LLM behavior.

- **The stack's breadth still risks onboarding overload without a dashboard and stronger guided paths.** The repo inventory for this report pass includes 34 service manifests spread across six categories, while the route docs enumerate a long list of hostnames, direct ports, and auth modes. The wizard and tracks help, and that is a real mitigation, but the user still needs to understand a substantial amount of infrastructure vocabulary to orient themselves. The current docs are good; the experience is still cognitively dense.

- **Vertical-track ambition is ahead of first-class productization.** The roadmap already frames 3D/game-generation, financial/trading-AI, and RAG-enhancement as strategic tracks, but `bootstrapper/tracks.yml` only exposes the current six general-purpose track keys. That gap matters. Atlas has a credible multi-domain substrate, yet its most opinionated future verticals are still roadmap narratives rather than selectable, onboarding-ready product modes. The vision is visible; the product surface has not caught up.

## 3. Competitor Landscape

External competitor research, checked on July 2, 2026, suggests Atlas does not have one exact peer. It sits in the overlap between local AI workbenches, self-hosted app builders, RAG frameworks, coding-agent control planes, and broader AI/data platform stacks. That breadth is an asset, but it also means Atlas loses whenever the user only wants one narrow job done with minimal setup.

### 3.1 Competitor Matrix

| Category | Examples | What they do better | What Atlas does better | Strategic implication |
|---|---|---|---|---|
| Local AI workbenches | [Open WebUI](https://docs.openwebui.com/), [AnythingLLM](https://docs.useanything.com/), [Jan](https://github.com/janhq/jan), [LM Studio](https://lmstudio.ai/docs/developer/core/server) | They deliver a tighter chat-first experience, clearer model UX, and faster first-run success. Open WebUI already ships desktop plus Docker/Python/Kubernetes paths, while Jan and LM Studio expose local OpenAI-compatible APIs from desktop apps. | Atlas is broader: it can bring the chat UI together with notebooks, workflow automation, vector/graph stores, observability, and multiple tracks in one system. | Atlas should not try to beat these on pure chat polish first. It should package a sharper "Atlas Workbench" starting path on top of its wider platform. |
| Model runtime and local inference layer | [Ollama](https://docs.ollama.com/api/introduction), [LM Studio](https://lmstudio.ai/docs/developer/core/server), [Jan](https://github.com/janhq/jan) | They make local model serving feel simple and productized: one install, one local API, one clear model catalog, and compatibility with OpenAI-style clients. | Atlas can orchestrate runtimes together with gateways, upstream services, and hybrid localhost/container deployment choices. | Atlas should treat runtime UX as a dependency it packages well, not as the core battleground. Lean into best-of-breed runtime integration. |
| App-store / one-click local launcher | [Pinokio](https://desktop.pinokio.co/), [Open WebUI Desktop](https://docs.openwebui.com/) | Pinokio's strongest move is discoverability and one-click install/launch for local AI apps, with a searchable directory and side-by-side version management. | Atlas is much stronger once the user wants a repeatable multi-service environment rather than one isolated app. | Atlas needs a curated catalog mindset: track bundles, recommended stacks, and install recipes that feel closer to a product shelf than a manifest inventory. |
| Agentic app builders and workflow studios | [Dify](https://docs.dify.ai/en/learn/key-concepts), [Flowise](https://docs.flowiseai.com/), [Langflow](https://docs.langflow.org/) | These products give users a visual canvas, app publishing flow, and opinionated developer UX. Dify also spans [cloud](https://docs.dify.ai/en/quick-start), [self-hosting](https://docs.dify.ai/en/self-host/deploy/overview), and a [plugin distribution model](https://docs.dify.ai/en/cloud/use-dify/workspace/plugins). Langflow and Flowise both push hard on agent tooling and low-code iteration speed. | Atlas is better as the substrate underneath these builders: databases, gateways, notebooks, automation, and service composition are already part of the platform. | Atlas should integrate with this category, not rebuild it from scratch. One default visual builder per track would close a major product-gap quickly. |
| RAG engines and agent frameworks | [RAGFlow](https://ragflow.io/docs/), [LlamaIndex](https://developers.llamaindex.ai/python/framework/), [Haystack](https://haystack.deepset.ai/) | These tools are more specialized around retrieval, ingestion, agent workflows, and evaluation loops than Atlas is. RAGFlow is opinionated about document pipelines; LlamaIndex and Haystack offer deeper framework-level primitives for production RAG and agent design. | Atlas can host the whole surrounding environment: object storage, vector DBs, graph DBs, notebooks, job runners, gateways, and adjacent apps. | Atlas should pick reference RAG stacks and make them first-class options instead of implying Atlas itself is the RAG framework. |
| Coding-agent platforms | [OpenHands](https://docs.openhands.dev/overview/introduction) | OpenHands is more focused on AI-driven software delivery, with a local Agent Canvas plus managed integrations for GitHub, GitLab, Bitbucket, Slack, Jira, and Linear, and an enterprise Kubernetes deployment path. | Atlas covers a much wider set of workloads beyond software agents and can host the surrounding tools those agents need. | In the `gen-ai-eng` track, Atlas should present coding agents as packaged workloads or integrations, not invent a parallel developer-agent product surface. |
| ML, data, and observability layers | [MLflow](https://mlflow.org/docs/latest/), [Langfuse](https://langfuse.com/docs), [OpenMetadata](https://docs.open-metadata.org/v1.13.x), [Dagster](https://docs.dagster.io/), [Superset](https://superset.apache.org/user-docs/intro/) | Each of these products owns a clearer category story than Atlas: MLflow for experiment/LLM lifecycle, Langfuse for tracing/evals, OpenMetadata for catalog/governance, Dagster for data orchestration, Superset for BI. | Atlas can colocate these layers with the rest of the AI stack and reduce integration friction for self-hosted teams. | This is an integration zone, not a head-to-head arena. Atlas should win by bundling and wiring category leaders coherently. |
| Kubernetes-based AI platform stacks | [Kubeflow](https://www.kubeflow.org/docs/started/introduction/), [Open Data Hub](https://opendatahub.io/docs/getting-started-with-open-data-hub/) | They are built for larger-scale platform teams that want Kubernetes-native modularity, portability, and production operations across the AI lifecycle. | Atlas is lighter-weight, faster to stand up on a single machine or small team server, and friendlier to hybrid localhost/container development. | Atlas should position itself as the on-ramp before a Kubernetes program, not as a near-term replacement for enterprise AI platform stacks. |

### 3.2 Local Workbenches And Install UX

The local AI workbench market is moving toward compressed time-to-value. [Open WebUI](https://docs.openwebui.com/) already combines an offline-first self-hosted interface with Docker, Python, Kubernetes, and native desktop install paths, and its getting-started docs call out plugins, tool calling, RAG, Open Terminal, and agent connections directly in the onboarding path. [Ollama](https://docs.ollama.com/api/introduction) and [LM Studio](https://lmstudio.ai/docs/developer/core/server) do a similar thing one layer lower: they make local inference feel like a clean product with a predictable local API and compatibility endpoints instead of a system-integration project. [Jan](https://github.com/janhq/jan) packages that same local-first model story into a desktop app with custom assistants, a local OpenAI-compatible server, and MCP support, while [AnythingLLM](https://docs.useanything.com/) bundles agents, API access, browser tooling, chat modes, and vector-database controls into one opinionated application.

[Pinokio](https://desktop.pinokio.co/) sharpens a different user expectation: AI apps should be discoverable and one-click installable, more like a curated launcher ecosystem than a repo you hand-configure. Atlas is much stronger once the user wants an integrated environment rather than one app, but it is still weaker than this category on first impressions, app discovery, and "it just works" local ergonomics. The strategic implication is straightforward: Atlas needs a stronger default workbench surface and curated install bundles before it tries to market its full breadth.

### 3.3 Agent Builders And RAG Products

The agent-builder layer is crowded by tools that are narrower than Atlas but more legible to buy or adopt. [Dify](https://docs.dify.ai/en/learn/key-concepts) presents itself as an agentic app builder with drag-and-drop workflows that can publish to API, web, or MCP server surfaces, and it spans both [Dify Cloud](https://docs.dify.ai/en/quick-start) and [self-hosted deployment](https://docs.dify.ai/en/self-host/deploy/overview). Its [integration model](https://docs.dify.ai/en/cloud/use-dify/workspace/plugins) is especially notable because it gives users an official Marketplace path, GitHub-based installs, and local package upload. [Flowise](https://docs.flowiseai.com/) pushes on the same low-code territory with a visual editor, 100+ integrations, execution logs, visual debugging, and air-gapped self-hosted options. [Langflow](https://docs.langflow.org/) is similarly strong on visual iteration, real-time testing, flow serving, custom components, and both MCP-server and MCP-client support.

On the RAG side, [RAGFlow](https://github.com/infiniflow/ragflow) is explicitly optimized around retrieval and document understanding, with current repo/docs evidence for Docker deployment, orchestrable ingestion, newer document parsers, and MCP-oriented agent workflows. [LlamaIndex](https://developers.llamaindex.ai/python/framework/) and [Haystack](https://haystack.deepset.ai/) sit one level down as frameworks: they provide deeper primitives for RAG, agents, branching logic, retrieval strategies, and evaluation than Atlas should try to own itself. Atlas' advantage is that it can host all the surrounding services these frameworks need, but that is a platform advantage, not a framework advantage. Strategically, Atlas should choose a few blessed integrations and templates here instead of broad, generic parity claims.

### 3.4 Coding Agents, Data Systems, And Observability

[OpenHands](https://docs.openhands.dev/overview/introduction) is a reminder that "AI platform" increasingly includes software agents, not just chat and RAG. Its local Agent Canvas starts a browser-based agent stack with one command, while OpenHands Cloud adds multi-user collaboration, permissions, reporting, budgeting, and integrations across source control and project-management systems. Atlas can host or route to a tool like this, but it is not yet a coding-agent control plane in its own right.

The same pattern appears in adjacent platform layers. [MLflow](https://mlflow.org/docs/latest/) already unifies LLM tracing, prompt management, evaluation, classic experiment tracking, model packaging, registry, and deployment. [Langfuse](https://langfuse.com/docs) has a much tighter story for LLM traces, latency/cost visibility, and collaborative debugging. [OpenMetadata](https://docs.open-metadata.org/v1.13.x) is pushing hard on context, governance, quality, and MCP-aware metadata access. [Dagster](https://docs.dagster.io/) has a clearer asset-centric orchestration and lineage model than Atlas, and [Superset](https://superset.apache.org/user-docs/intro/) remains a stronger analytics/dashboard product than anything Atlas currently exposes at the root experience. Atlas should not compete feature-for-feature with these systems; it should make them easy to enable, discover, authenticate, and connect.

### 3.5 Market Position Summary

The clearest market position for Atlas is between desktop/local workbenches and heavyweight Kubernetes-native AI platforms. [Kubeflow](https://www.kubeflow.org/docs/started/introduction/) and [Open Data Hub](https://opendatahub.io/docs/getting-started-with-open-data-hub/) are optimized for platform teams that want a modular, scalable AI foundation on Kubernetes. Atlas is not there today, and it does not need to be there to matter. Its stronger wedge is: broader than a single local AI app, easier to self-host than a full Kubernetes stack, and more configurable than a polished SaaS-first builder.

That position is defensible if Atlas behaves like the control plane for small teams, labs, consultants, and regulated internal groups that want a serious self-hosted AI environment without immediately taking on a Kubernetes program. The main competitive lesson from this scan is that Atlas wins on composability and scope, but the market rewards products that hide that complexity behind curated entrypoints. The strategic implication is to invest next in packaging, defaults, onboarding, and integration quality more than in raw service-count expansion.

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
- `services/*/service.yml`: manifest inventory evidence for service count, category spread, virtual manifests, and the recurring SOURCE contract referenced in section 2.
- `bootstrapper/tracks.yml`: current first-class track registry and its limits relative to roadmap verticals.
- `services/kong/README.md`, `services/open-webui/README.md`, `services/supabase/README.md`, `services/prometheus/README.md`, `services/grafana/README.md`: concrete evidence for root-entrypoint behavior, fragmented auth, future SSO work, and current-versus-future observability scope.

Task 3 external competitor notes (official sources checked July 2, 2026):

- Local AI workbenches and launcher surfaces: [Open WebUI docs](https://docs.openwebui.com/), [Ollama docs](https://docs.ollama.com/api/introduction), [Ollama product site](https://ollama.com/), [LM Studio developer docs](https://lmstudio.ai/docs/developer/core/server), [AnythingLLM docs](https://docs.useanything.com/), [Jan GitHub repo](https://github.com/janhq/jan), [Pinokio product site](https://desktop.pinokio.co/).
- Agent-builder platforms: [Dify key concepts](https://docs.dify.ai/en/learn/key-concepts), [Dify cloud quick start](https://docs.dify.ai/en/quick-start), [Dify self-host deploy overview](https://docs.dify.ai/en/self-host/deploy/overview), [Dify plugins docs](https://docs.dify.ai/en/cloud/use-dify/workspace/plugins), [Flowise docs](https://docs.flowiseai.com/), [Langflow docs](https://docs.langflow.org/).
- RAG and framework products: [RAGFlow docs](https://ragflow.io/docs/), [RAGFlow GitHub repo](https://github.com/infiniflow/ragflow), [LlamaIndex framework docs](https://developers.llamaindex.ai/python/framework/), [Haystack docs](https://haystack.deepset.ai/).
- Coding-agent, observability, ML, and data layers: [OpenHands docs](https://docs.openhands.dev/overview/introduction), [MLflow docs](https://mlflow.org/docs/latest/), [Langfuse docs](https://langfuse.com/docs), [OpenMetadata docs](https://docs.open-metadata.org/v1.13.x), [Dagster docs](https://docs.dagster.io/), [Superset docs](https://superset.apache.org/user-docs/intro/).
- Kubernetes-based AI platforms: [Kubeflow introduction](https://www.kubeflow.org/docs/started/introduction/), [Open Data Hub getting started](https://opendatahub.io/docs/getting-started-with-open-data-hub/).
