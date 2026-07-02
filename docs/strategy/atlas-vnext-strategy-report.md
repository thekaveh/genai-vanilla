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

Atlas should adopt a **phased hybrid** MCP strategy: start with a small curated package of high-value MCP servers, let the MCP-native consumers talk to those servers directly, add an aggregator only once Atlas has enough servers and per-consumer policy needs to justify it, and avoid one-MCP-server-per-service cargo culting.

### 5.1 What Current Sources Actually Confirm

The current official MCP landscape is materially better than the repo's earlier assumptions, but it is also more uneven than "just add an MCP gateway everywhere."

- The current [Model Context Protocol specification](https://modelcontextprotocol.io/specification/2025-06-18) defines MCP as an open protocol between hosts, clients, and servers with a strong emphasis on consent, authorization, and tool safety. That matters because Atlas is not choosing a mere adapter format; it is choosing an execution surface that can reach databases, files, and internal APIs.
- [Open WebUI now natively supports MCP Streamable HTTP starting in v0.6.31](https://docs.openwebui.com/features/extensibility/mcp/). Its own docs also say to use [mcpo](https://github.com/open-webui/mcpo) only when the target server is not directly consumable over HTTP or when an OpenAPI surface is the more practical client contract ([Open WebUI MCP FAQ](https://docs.openwebui.com/faq/), [mcpo docs](https://docs.openwebui.com/features/extensibility/plugin/tools/openapi-servers/mcp/)). That means Atlas no longer needs an OpenAPI bridge just to give chat access to a well-behaved HTTP MCP server.
- [LiteLLM now ships an MCP gateway](https://docs.litellm.ai/docs/mcp) with a fixed endpoint, support for Streamable HTTP, SSE, and stdio, per-key/team/org permissions, and even [OpenAPI-to-MCP conversion](https://docs.litellm.ai/docs/mcp_openapi). This is verified current support, not roadmap. It makes LiteLLM a real MCP consumer and policy surface, but it does not automatically make LiteLLM the best Atlas-wide MCP control plane.
- [Hermes Agent is currently both a strong MCP client and a verified MCP server](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-hermes-agent). Its current CLI docs include `hermes mcp serve`, and the [Codex app-server runtime docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime) explicitly say Hermes "registers itself as an MCP server" so Codex can call back into Hermes tools. Atlas should still treat Hermes as a **consumer-first** integration by default, because Atlas primarily wants Hermes to use Atlas tools rather than expose Hermes itself as a shared tool surface unless there is a concrete reason to do so. The old ["Hermes as MCP server" issue](https://github.com/NousResearch/hermes-agent/issues/342) is closed and should no longer be treated as pending future work.
- [MetaMCP](https://docs.metamcp.com/en) is a genuine aggregator layer, not just a transport shim. Its docs verify [namespaces](https://docs.metamcp.com/en/concepts/namespaces), [public endpoints that can expose SSE, Streamable HTTP, and OpenAPI](https://docs.metamcp.com/en/concepts/endpoints), and a documented [Open WebUI integration path](https://docs.metamcp.com/en/integrations/open-web-ui). That makes it the strongest fit when Atlas needs one curated surface with per-consumer scoping.
- [Docker MCP Gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/) is also real and open source, but Docker's docs position the managed AI Governance path as invite-only and frame the gateway around dynamically launching MCP server containers from Docker-managed profiles and catalogs. Its official tooling and repo are excellent for broad connector catalogs and Docker-centered lifecycle control, but that is a worse default fit for Atlas' mostly internal, already-composed services.
- [Docling MCP](https://github.com/docling-project/docling-mcp) is now especially relevant for Atlas because v2 added remote mode and `streamable-http`, so it can front an existing Docling service instead of forcing Atlas to co-locate conversion models with every MCP process.

The practical consequence is straightforward: Atlas should not choose between "pure sidecars" and "always-on aggregator" as a religion. It should use direct sidecars where the value is immediate, then introduce aggregation when the number of servers and policy splits make it worthwhile.

### 5.2 MCP Target / Consumer Matrix

| Atlas service | MCP role | Recommendation | Rationale |
|---|---|---|---|
| Supabase / Postgres | Target | **Phase 1 curated server** | High-value structured data surface; Atlas already centralizes product state in Postgres and the roadmap already expects a Postgres MCP path. |
| Neo4j | Target | **Phase 1 curated server** | Graph queries are highly agent-friendly and Hermes/Open WebUI benefit from a graph-native tool more than from bespoke HTTP glue. |
| Weaviate | Target | **Phase 2 curated server** | Valuable, but lower priority than Postgres/Neo4j/SearXNG because Atlas already has non-MCP retrieval paths and community MCP quality should be evaluated before pinning. |
| SearXNG | Target | **Phase 1 curated server** | Clean web-search tool surface with obvious cross-consumer value and low architectural risk. |
| MinIO | Target | **Phase 2 curated server** | Good fit through an S3-shaped MCP server, but the write/delete blast radius is larger, so it should wait for scoped credentials and clearer policy. |
| n8n | Both, but defer | **Phase 2 target/consumer** | Atlas research suggests useful MCP-trigger and workflow-as-tool patterns, but Atlas does not need them to justify the initial architecture; treat as a later expansion. |
| Backend | Both, but mostly target | **Phase 2 custom Atlas MCP server** | A thin first-party MCP wrapper around LangMem and Atlas-specific routes is better than exposing the full backend surface ad hoc. |
| Docling | Target | **Early specialist addition** | Verified current [Docling MCP](https://github.com/docling-project/docling-mcp) remote mode makes document conversion a strong high-signal tool for agents without duplicate model loading. |
| Open WebUI | Consumer | **Use as direct MCP client** | Verified current native Streamable HTTP support means Atlas should connect Open WebUI directly to curated MCP servers or a later aggregator, not force mcpo in front of every server. |
| Hermes | Both (consumer-first) | **Use as direct MCP client by default; expose Hermes-as-server only when a concrete callback/tool-sharing need exists** | Verified current Hermes MCP support includes both client capability and server capability (`hermes mcp serve`, plus Hermes registering itself as an MCP server in the Codex runtime docs), but Atlas' primary value is Hermes consuming Atlas tools rather than making Hermes another shared platform server by default. |
| OpenClaw | Consumer (inferred, not re-verified externally in this pass) | **Treat as a later consumer** | Atlas' internal research says OpenClaw has MCP CLI / external-server support, but the initial decision does not need that path to be live. |
| LiteLLM | Consumer and optional policy gateway | **Consume MCP; do not make it the sole Atlas aggregator yet** | Verified current MCP support is real, but Atlas should avoid coupling every tool-governance concern to its already-critical LLM gateway on day one. |
| Ollama | Neither practical target nor priority consumer | **Do not MCP-wrap** | Ollama is already the model-serving layer; adding MCP around it would be circular and adds little user value. |
| Kong | Infra proxy, not MCP target | **Proxy selected MCP HTTP routes later; do not turn Kong into the MCP brain** | Kong is useful for stable aliases and auth fronts, but Atlas should keep MCP tool semantics in MCP-aware components, not in the HTTP gateway itself. |
| STT / TTS providers | Usually non-target | **Do not wrap current providers in MCP** | Atlas already reaches these services through OpenAI-compatible HTTP. MCP only becomes interesting when a provider's native value is MCP-first, such as the repo's Voicebox research. |
| Virtual services (`cloud-providers`, `globals`, provider virtual manifests) | Neither | **Do not MCP-wrap** | These are configuration surfaces, not runtime tool surfaces. |

### 5.3 Recommended Architecture

The best answer is not "aggregator" or "service-by-service sidecars" in isolation. It is:

1. **Phase 1: curated package, no heavyweight aggregator**
   Stand up a small set of MCP servers with the clearest cross-stack payoff:
   `Postgres`, `Neo4j`, `SearXNG`, and then `Docling MCP` as the first specialist expansion. Keep them as explicit, reviewable services rather than auto-spawning a server for every Atlas service.

2. **Connect native consumers directly first**
   Let Open WebUI and Hermes talk to those MCP servers directly over Streamable HTTP where possible. Let LiteLLM consume them only where Atlas explicitly wants model-facing tool access under LiteLLM policy. This keeps the first rollout simple and proves real demand before Atlas adds another control plane.

3. **Add an aggregator when Atlas crosses the "policy and namespacing" threshold**
   Once Atlas has roughly four or more internal MCP servers, or once chat, agents, and automation need different tool visibility, add **MetaMCP** in front of the curated set. MetaMCP is the best fit for that step because it combines namespaces, public endpoints, and OpenAPI exposure in one place. At that point Atlas can expose one namespace to Open WebUI, a narrower one to Hermes, and a more controlled one to automation clients.

4. **Use `mcpo` as a translator, not as the architecture center**
   `mcpo` is still useful when Atlas needs OpenAPI for a consumer that is not MCP-native, or when a desired MCP server is stdio-only. It should be treated as an edge adapter, not as the long-term Atlas MCP control plane.

5. **Reserve Docker MCP Gateway for a different problem**
   Docker MCP Gateway becomes attractive if Atlas later wants a large SaaS/vendor connector catalog with Docker-managed lifecycle and catalog distribution. That is a legitimate future path, but it is not the right default for Atlas' internal-service-first topology today.

### 5.4 Bottom-Line Decision

Atlas should **not** do one-MCP-server-per-service, should **not** default to Docker MCP Gateway, and should **not** force every tool through `mcpo`. Atlas should use a **phased hybrid**: a curated package of high-value MCP servers now, direct native consumption first, and MetaMCP later when namespacing, policy, and endpoint consolidation become worth the extra operational layer.

## 6. Kong Root Dashboard Recommendation

Yes: the **Kong root** should become an Atlas product entrypoint. But the first version should be a lightweight **service directory** and **health dashboard**, not a replacement for Grafana, Supabase Studio, or the setup wizard.

### 6.1 Why The Root Should Change

Today, Atlas' own route docs and Kong README both say that the bare `localhost` root falls through to Supabase Studio ([ports-and-routes](../deployment/ports-and-routes.md), [Kong README](../../services/kong/README.md)). That is useful for operators who already know Atlas, but it is the wrong first impression for a multi-service platform. The front door currently lands on one subsystem's admin console instead of on Atlas itself.

Atlas' biggest onboarding weakness is not lack of services; it is lack of orientation. A root dashboard solves that directly by answering the first-run questions users actually have:

- What is running right now?
- Which URLs should I use?
- Which services are intentionally disabled by the current track?
- Which credentials or auth modes apply?
- What should I open first?

### 6.2 Minimum Viable Dashboard

The minimum viable dashboard should stay narrow and operationally boring:

- **Service directory:** one row per active service showing display name, category, current SOURCE, Kong URL, direct URL, and a short auth note.
- **Health dashboard:** clear `healthy / degraded / disabled` status, derived from the same resolved SOURCE state and lightweight reachability checks Atlas already uses for routing. This should be an orientation surface, not a Grafana clone.
- **Track context:** show the active track and which services are disabled by track policy versus manually disabled by the operator.
- **Common actions:** prominent launch links for the highest-traffic surfaces such as Open WebUI, LiteLLM, n8n, JupyterHub, Supabase Studio, and any enabled observability pages.
- **Warnings:** disabled dependencies, localhost-mode services that are unreachable, missing `--setup-hosts` state, and services whose route exists but whose upstream is degraded.
- **Docs links:** quick links to the route table, troubleshooting, and the quick-start flow so the dashboard helps users recover rather than merely report failure.

### 6.3 What The First Version Should Explicitly Not Be

The first version should **not** try to become:

- a replacement for Grafana metrics and alerts
- a replacement for Supabase Studio or LiteLLM admin surfaces
- a control plane for editing SOURCE values
- a second setup wizard
- a giant SPA with its own persistence model

Atlas already has several specialist UIs. The root page should be the map, not every destination at once.

### 6.4 Product Recommendation

Atlas should move the root route to an Atlas-branded landing page and keep Supabase Studio on `studio.localhost`. The first implementation should be a small, generated dashboard built from the same topology, route, and auth metadata Atlas already maintains, so it stays consistent with the rest of the stack instead of becoming a second, drifting inventory.

In short: **use the Kong root as the Atlas entrypoint, and make v1 a service directory plus health dashboard.** That is the smallest change that meaningfully improves onboarding, navigation, and day-two usability without overreaching into a new control plane.

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

Task 4 MCP and dashboard notes (official/current sources checked July 2, 2026):

- MCP protocol baseline: [Model Context Protocol specification, version 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18).
- MetaMCP current capabilities: [docs home](https://docs.metamcp.com/en), [namespaces](https://docs.metamcp.com/en/concepts/namespaces), [endpoints](https://docs.metamcp.com/en/concepts/endpoints), [Open WebUI integration](https://docs.metamcp.com/en/integrations/open-web-ui), and the [official GitHub repo](https://github.com/metatool-ai/metamcp).
- Docker MCP Gateway current capabilities: [Docker docs](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/) and the [official GitHub repo](https://github.com/docker/mcp-gateway).
- Open WebUI current MCP position: [native MCP docs](https://docs.openwebui.com/features/extensibility/mcp/), [mcpo docs](https://docs.openwebui.com/features/extensibility/plugin/tools/openapi-servers/mcp/), [tools overview](https://docs.openwebui.com/features/extensibility/plugin/tools/), [FAQ](https://docs.openwebui.com/faq/), and the [mcpo repo](https://github.com/open-webui/mcpo).
- LiteLLM current MCP position: [MCP overview](https://docs.litellm.ai/docs/mcp), [usage](https://docs.litellm.ai/docs/mcp_usage), [permission management](https://docs.litellm.ai/docs/mcp_control), [deployment guide](https://docs.litellm.ai/docs/mcp_deployment), [OpenAPI-to-MCP](https://docs.litellm.ai/docs/mcp_openapi).
- Hermes current MCP position: the bundled-skill / CLI reference showing [`hermes mcp serve`](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-hermes-agent), the [Codex app-server runtime docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime) showing Hermes "registers itself as an MCP server", the broader [feature docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp), the [usage guide](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes), the [closed issue #342](https://github.com/NousResearch/hermes-agent/issues/342), and the [official Hermes repo](https://github.com/NousResearch/hermes-agent).
- Docling MCP current capabilities: the [official Docling MCP repo](https://github.com/docling-project/docling-mcp) and [docling-serve releases](https://github.com/DS4SD/docling-serve/releases) for current bundled versions.
- Atlas-internal evidence used for the Kong-root recommendation: [ports-and-routes](../deployment/ports-and-routes.md), [Kong README](../../services/kong/README.md), [Open WebUI README](../../services/open-webui/README.md), [LiteLLM README](../../services/litellm/README.md), [Hermes README](../../services/hermes/README.md), and the current [ROADMAP](../ROADMAP.md).
