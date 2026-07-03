# Atlas vNext GitHub Issues And Project Design

## 1. Goal

Turn the Atlas vNext strategy report into a durable GitHub planning system so the work is not lost after the report is read once.

The GitHub system should:

- Create one actionable GitHub issue per Build Now work item.
- Create epic issues for the larger themes named by the user: Atlas Root Dashboard, MCP Package, Observability, Ingestion, and Async Jobs.
- Capture Build Next, Build Later, watchlist, and deferred/rejected candidates as backlog or decision issues so they remain searchable and intentionally triaged.
- Use a GitHub Project as the prioritization board over the issues.
- Keep the active working surface focused on Build Now while preserving every vNext candidate, watchlist item, and explicit defer/reject decision from the report.

Primary source:

- [Atlas vNext Strategy Report](../../strategy/atlas-vnext-strategy-report.md)

## 2. Operating Model

Use a two-layer model:

1. **Complete capture:** every candidate or explicit roadmap decision in the report becomes a GitHub issue.
2. **Phased activation:** only Build Now implementation issues and their epics enter the active Project lanes immediately.

This avoids the two failure modes:

- Important ideas disappearing into a Markdown report that nobody revisits.
- The Project board becoming noisy with 40+ items that are not ready to build.

## 3. Project

Create one GitHub Project:

- **Title:** `Atlas vNext Roadmap`
- **Owner:** `thekaveh`
- **Repository:** `thekaveh/atlas`
- **Purpose:** prioritize, sequence, and track the vNext issue set derived from the strategy report.

Suggested views:

- **Roadmap Board:** grouped by `Status`.
- **Wave Planning:** grouped by `Wave`.
- **Track Planning:** grouped by `Track`.
- **Risk Review:** grouped by `Risk`.
- **Epic View:** filtered to `type:epic`.

Suggested Project fields:

| Field | Type | Values |
| --- | --- | --- |
| Status | Single select | `Build Now`, `Ready`, `Backlog`, `Watchlist`, `Deferred`, `Rejected For Now`, `Blocked`, `Done` |
| Wave | Single select | `Build Now`, `Build Next`, `Build Later`, `Watchlist`, `Deferred`, `Rejected For Now`, `Already Shipped` |
| Track | Single select | `platform`, `mcp`, `observability`, `rag`, `async-jobs`, `data-ml`, `identity-security`, `creative-3d`, `trading`, `voice`, `infra`, `decision` |
| Effort | Single select | `small`, `medium`, `large`, `unknown` |
| Risk | Single select | `low`, `medium`, `high`, `unknown` |
| Priority | Single select | `P0`, `P1`, `P2`, `P3` |
| Type | Single select | `epic`, `implementation`, `evaluation`, `decision`, `watchlist` |
| Source | Text | Link to the report section and candidate research doc where applicable |

Initial Project status rules:

- Epic issues: `Build Now`
- Build Now implementation issues: `Build Now`
- Build Next issues: `Backlog`
- Build Later issues: `Backlog`
- Watchlist issues: `Watchlist`
- Deferred decisions: `Deferred`
- Rejected-for-now decisions: `Rejected For Now`
- Already-shipped notes: `Done` or omitted from the board unless an issue is needed for traceability

## 4. Labels

Keep labels simple and composable. Create missing labels before creating issues.

Core labels:

- `vnext`
- `type:epic`
- `type:implementation`
- `type:evaluation`
- `type:decision`
- `type:watchlist`

Wave labels:

- `wave:build-now`
- `wave:build-next`
- `wave:build-later`
- `wave:watchlist`
- `wave:deferred`
- `wave:rejected-for-now`
- `wave:already-shipped`

Track labels:

- `track:platform`
- `track:mcp`
- `track:observability`
- `track:rag`
- `track:async-jobs`
- `track:data-ml`
- `track:identity-security`
- `track:creative-3d`
- `track:trading`
- `track:voice`
- `track:infra`
- `track:decision`

Risk labels:

- `risk:low`
- `risk:medium`
- `risk:high`
- `risk:unknown`

Effort labels:

- `effort:small`
- `effort:medium`
- `effort:large`
- `effort:unknown`

Recommended extra labels:

- `epic:dashboard`
- `epic:mcp`
- `epic:observability`
- `epic:ingestion`
- `epic:async-jobs`

## 5. Standard Issue Body Template

Use this structure for implementation, evaluation, and watchlist issues:

```markdown
## Summary

<One paragraph describing what this issue should accomplish.>

## Source

- Report: <link to exact section>
- Candidate note: <link if one exists>

## Why

<Why this matters for Atlas, based on the report.>

## Scope

- <Concrete work item>
- <Concrete work item>

## Out Of Scope

- <Explicit non-goal>
- <Explicit non-goal>

## Dependencies

- <Existing Atlas service or prerequisite issue>

## Acceptance Criteria

- [ ] <Verifiable outcome>
- [ ] <Verifiable outcome>
- [ ] <Docs/tests/validation outcome>

## Validation

- [ ] `python scripts/check_doc_links.py`
- [ ] `python scripts/check-docs-drift.py`
- [ ] `cd bootstrapper && uv run pytest -q` where manifest/bootstrapper behavior changes
- [ ] Add or update targeted tests for changed code paths
```

Use this structure for deferred/rejected decision issues:

```markdown
## Decision

<Deferred / rejected-for-now decision.>

## Source

- Report: <link to exact section>

## Why Not Now

<Reason from the report.>

## Revisit Criteria

- [ ] <Condition that would justify reopening>
- [ ] <Required guardrail or prerequisite>

## Guardrails

- <What future workers must not do prematurely>
```

## 6. Epic Issues

### 6.1 Epic: Atlas Root Dashboard

- **Labels:** `vnext`, `type:epic`, `track:platform`, `risk:low`, `effort:medium`, `epic:dashboard`, `wave:build-now`
- **Project:** Status `Build Now`, Wave `Build Now`, Track `platform`, Priority `P0`
- **Source:** [Executive summary](../../strategy/atlas-vnext-strategy-report.md#1-executive-summary), [Kong root recommendation](../../strategy/atlas-vnext-strategy-report.md#6-kong-root-dashboard-recommendation), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Child issue exists for the Build Now root dashboard implementation.
- [ ] Dashboard issue links back to this epic.
- [ ] Epic body defines the minimum dashboard as service directory, health status, track context, common actions, warnings, and docs links.
- [ ] Epic body explicitly says v1 is not a Grafana replacement, setup wizard, SOURCE editor, or persistent control plane.

### 6.2 Epic: MCP Package

- **Labels:** `vnext`, `type:epic`, `track:mcp`, `risk:medium`, `effort:medium`, `epic:mcp`, `wave:build-now`
- **Project:** Status `Build Now`, Wave `Build Now`, Track `mcp`, Priority `P0`
- **Source:** [MCP bottom-line decision](../../strategy/atlas-vnext-strategy-report.md#54-bottom-line-decision), [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Child issue exists for the curated MCP package.
- [ ] Epic captures the phased hybrid decision: curated package first, direct native consumers first, MetaMCP later when policy/namespacing justify it.
- [ ] Epic body rejects one-MCP-server-per-service, Docker MCP Gateway as the default, and forcing every server through `mcpo`.
- [ ] Epic body identifies Postgres, Neo4j, SearXNG, and Docling MCP as first relevant targets.

### 6.3 Epic: Observability

- **Labels:** `vnext`, `type:epic`, `track:observability`, `risk:medium`, `effort:medium`, `epic:observability`, `wave:build-now`
- **Project:** Status `Build Now`, Wave `Build Now`, Track `observability`, Priority `P1`
- **Source:** [Current weaknesses](../../strategy/atlas-vnext-strategy-report.md#22-weaknesses), [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] Child issue exists for Langfuse gateway tracing.
- [ ] Backlog issue exists for OpenTelemetry Collector + Tempo + Loki.
- [ ] Decision issue exists for OpenLIT deferral.
- [ ] Epic explains the distinction between current Prometheus/Grafana infrastructure metrics and missing LLM traces/logs/cost attribution.

### 6.4 Epic: Ingestion

- **Labels:** `vnext`, `type:epic`, `track:rag`, `risk:medium`, `effort:medium`, `epic:ingestion`, `wave:build-now`
- **Project:** Status `Build Now`, Wave `Build Now`, Track `rag`, Priority `P1`
- **Source:** [RAG and content-ingestion track](../../strategy/atlas-vnext-strategy-report.md#83-rag-and-content-ingestion-track), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Child issues exist for Crawl4AI and Apache Tika.
- [ ] Related MCP issue includes Docling MCP as the first specialist MCP expansion.
- [ ] Watchlist/deferred issues exist for Browserless, Firecrawl, WhisperX, Verba, Neo4j LLM Knowledge Graph Builder, and Graphiti.
- [ ] Epic defines ingestion guardrails: disabled by default where risky, size/time/content-type limits, and provenance retention.

### 6.5 Epic: Async Jobs

- **Labels:** `vnext`, `type:epic`, `track:async-jobs`, `risk:medium`, `effort:small`, `epic:async-jobs`, `wave:build-now`
- **Project:** Status `Build Now`, Wave `Build Now`, Track `async-jobs`, Priority `P1`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now), [Reject/defer notes](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Acceptance criteria:

- [ ] Child issue exists for Celery + Flower worker tier.
- [ ] Decision issue exists for Supabase Edge Functions deferral.
- [ ] Epic explains that Atlas should establish one backend async-job pattern before adding alternate server-side execution surfaces.
- [ ] Epic identifies Redis and backend code sharing as required prerequisites.

## 7. Build Now Implementation Issues

### 7.1 Build Now: Atlas Root Dashboard

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:platform`, `risk:low`, `effort:medium`, `epic:dashboard`
- **Source:** [Kong root recommendation](../../strategy/atlas-vnext-strategy-report.md#6-kong-root-dashboard-recommendation), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Kong bare-root route serves an Atlas-branded entrypoint instead of falling through to Supabase Studio.
- [ ] Supabase Studio remains reachable through an explicit route, expected to be `studio.localhost` unless implementation discovers a better existing alias.
- [ ] Dashboard shows active service rows with display name, category, SOURCE, Kong URL, direct URL, and auth note.
- [ ] Dashboard shows `healthy`, `degraded`, or `disabled` status using resolved SOURCE state and lightweight reachability checks.
- [ ] Dashboard shows active track context and distinguishes disabled-by-track from manually disabled services.
- [ ] Dashboard links prominent surfaces such as Open WebUI, LiteLLM, n8n, JupyterHub, Supabase Studio, and enabled observability pages.
- [ ] Dashboard warns about missing hosts setup, unreachable localhost-mode services, disabled dependencies, and degraded upstreams.
- [ ] Docs and tests cover route behavior and dashboard generation.

### 7.2 Build Now: Curated MCP Package

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:mcp`, `risk:medium`, `effort:medium`, `epic:mcp`
- **Source:** [MCP architecture](../../strategy/atlas-vnext-strategy-report.md#53-recommended-architecture), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Atlas has a curated MCP package or service group for Postgres, Neo4j, and SearXNG MCP servers.
- [ ] Docling MCP is documented as the first specialist addition and either included behind a safe SOURCE value or split into a linked follow-up if implementation risk is high.
- [ ] Open WebUI and Hermes are documented as direct native MCP consumers where possible.
- [ ] LiteLLM MCP usage is only enabled where Atlas explicitly wants model-facing tool access under LiteLLM policy.
- [ ] The implementation does not add a generic one-server-per-service MCP pattern.
- [ ] MetaMCP, Docker MCP Gateway, and `mcpo` are documented as later/conditional tools, not default architecture.
- [ ] Docs include security, consent, namespace, and credential guardrails.

### 7.3 Build Now: Langfuse Gateway Tracing

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:observability`, `risk:medium`, `effort:medium`, `epic:observability`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Langfuse can be enabled as a SOURCE-configurable, disabled-by-default observability service.
- [ ] LiteLLM-routed calls emit traces to Langfuse first.
- [ ] Required backing services are documented, including Redis, MinIO/S3, Postgres, and current Langfuse ingestion/storage expectations.
- [ ] Cost, latency, model, prompt, and response metadata are visible for LiteLLM-routed calls where supported.
- [ ] Direct ComfyUI/Hermes/backend custom spans are explicitly out of scope for the first slice.
- [ ] Docs explain how Langfuse complements, rather than replaces, Prometheus and Grafana.

### 7.4 Build Now: Crawl4AI Extraction Path

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:rag`, `risk:medium`, `effort:small`, `epic:ingestion`
- **Source:** [RAG and content-ingestion track](../../strategy/atlas-vnext-strategy-report.md#83-rag-and-content-ingestion-track), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] `crawl4ai` is added as disabled-by-default service or integration.
- [ ] Local Deep Researcher can use Crawl4AI for full-page extraction behind one explicit env flag or SOURCE value.
- [ ] n8n has a documented path for invoking the extraction flow.
- [ ] Extracted content preserves source URL, retrieval timestamp, and provenance suitable for RAG audit.
- [ ] Resource limits, timeout limits, and content-type guardrails are documented.
- [ ] Firecrawl and Browserless remain deferred until Crawl4AI gaps are proven.

### 7.5 Build Now: Celery + Flower Worker Tier

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:async-jobs`, `risk:medium`, `effort:small`, `epic:async-jobs`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Backend has a Celery worker tier using existing Redis where appropriate.
- [ ] One long-running backend flow, preferably memory consolidation or research start, moves out of the FastAPI request loop.
- [ ] API returns job state or job id instead of blocking for the entire long-running operation.
- [ ] Flower is available as a dev/operator monitor and is disabled or protected appropriately by default.
- [ ] Retry, timeout, and failure-state behavior are documented.
- [ ] Tests cover the selected task dispatch and status path.

### 7.6 Build Now: Supavisor Transaction Pooler

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:infra`, `risk:medium`, `effort:medium`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Supavisor is added as an optional SOURCE-configurable service for Supabase Postgres pooling.
- [ ] Backend and n8n can be routed through Supavisor transaction mode first.
- [ ] PostgREST and Realtime stay direct unless session-mode behavior is intentionally proven.
- [ ] Docs identify which consumers use pooled versus direct Postgres connections.
- [ ] Rollback path is documented so operators can return to direct connections.
- [ ] Integration tests or compose validation cover the pooled configuration.

### 7.7 Build Now: Apache Tika Fallback Extractor

- **Labels:** `vnext`, `enhancement`, `type:implementation`, `wave:build-now`, `track:rag`, `risk:medium`, `effort:small`, `epic:ingestion`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [RAG and content-ingestion track](../../strategy/atlas-vnext-strategy-report.md#83-rag-and-content-ingestion-track), [Build Now](../../strategy/atlas-vnext-strategy-report.md#91-build-now)

Acceptance criteria:

- [ ] Tika is added disabled by default as a fallback extractor.
- [ ] Doc processor or backend calls Tika only when Docling returns unsupported-format or an equivalent explicit fallback condition.
- [ ] Supported long-tail formats are documented, including EML, MSG, RTF, ODT, ZIP, and obscure MIME types where applicable.
- [ ] Size, timeout, malware/resource, and content-type limits are documented.
- [ ] Extracted text preserves document provenance for RAG audit.
- [ ] Tests cover fallback selection without regressing the Docling-first path.

## 8. Build Next Backlog Issues

### 8.1 Build Next: SSO Pilot With Authentik First

- **Labels:** `vnext`, `type:evaluation`, `wave:build-next`, `track:identity-security`, `risk:high`, `effort:large`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] Authentik is evaluated as the first SSO pilot and Keycloak is documented as the heavier enterprise alternative.
- [ ] One non-critical route is protected with forward auth or OIDC before any broad migration.
- [ ] Open WebUI, JupyterHub, n8n, MinIO, Neo4j, Kong, and Supabase Auth implications are documented.
- [ ] The issue blocks full-stack auth migration until a route-level pilot passes.

### 8.2 Build Next: Secrets Manager With Infisical First

- **Labels:** `vnext`, `type:evaluation`, `wave:build-next`, `track:identity-security`, `risk:high`, `effort:medium`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] Infisical is evaluated as optional, disabled-by-default secrets manager.
- [ ] OpenBao is documented as the Vault-lineage watchlist option.
- [ ] Only new high-risk credentials move into the secrets manager first.
- [ ] Existing `.env` flows are not disrupted in the first slice.
- [ ] Bootstrapper env injection and service startup implications are documented.

### 8.3 Build Next: OpenTelemetry Collector + Tempo + Loki

- **Labels:** `vnext`, `type:implementation`, `wave:build-next`, `track:observability`, `risk:medium`, `effort:medium`, `epic:observability`
- **Source:** [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] OTel Collector is introduced as the vendor-neutral ingest point.
- [ ] Tempo is wired first for backend and LiteLLM traces.
- [ ] Loki log shipping is added only after trace ingestion is proven, with short default retention.
- [ ] Kong request IDs and trace correlation strategy are documented.
- [ ] Grafana integration is documented.

### 8.4 Build Next: MLflow Tracking And Artifact Store

- **Labels:** `vnext`, `type:implementation`, `wave:build-next`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] MLflow tracking URI is exposed to JupyterHub.
- [ ] MLflow uses MinIO-backed artifacts and Supabase/Postgres metadata where appropriate.
- [ ] A sample notebook logs an experiment and artifact.
- [ ] Model promotion automations are explicitly out of scope for the first slice.

### 8.5 Build Next: Open WebUI Pipelines

- **Labels:** `vnext`, `type:evaluation`, `wave:build-next`, `track:platform`, `risk:medium`, `effort:medium`
- **Source:** [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] One disabled-by-default pipeline is provided for tracing, redaction, or routing.
- [ ] The issue documents whether the pipeline sits before or behind LiteLLM.
- [ ] Langfuse integration is considered before adding a separate observability surface.
- [ ] OpenLIT remains deferred as a standalone UI.

### 8.6 Build Next: Neo4j LLM Knowledge Graph Builder

- **Labels:** `vnext`, `type:implementation`, `wave:build-next`, `track:rag`, `risk:medium`, `effort:medium`, `epic:ingestion`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] UI/backend pair is added disabled by default.
- [ ] It connects to existing Neo4j, LiteLLM, MinIO, and Docling where appropriate.
- [ ] A sample document-to-graph workflow is documented.
- [ ] Namespaces/labels prevent collisions with other Neo4j data.

### 8.7 Build Next: Verba RAG UI

- **Labels:** `vnext`, `type:implementation`, `wave:build-next`, `track:rag`, `risk:medium`, `effort:medium`, `epic:ingestion`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] Verba is added disabled by default.
- [ ] It uses an isolated/namespaced Weaviate collection.
- [ ] LiteLLM and optional Docling wiring are documented.
- [ ] A sample ingest/query path is documented.

### 8.8 Build Next: Label Studio Review Loop

- **Labels:** `vnext`, `type:implementation`, `wave:build-next`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Build Next](../../strategy/atlas-vnext-strategy-report.md#92-build-next)

Acceptance criteria:

- [ ] Label Studio is added disabled by default.
- [ ] Media storage uses MinIO/S3 where supported.
- [ ] A notebook shows export to Weaviate or MLflow.
- [ ] SSO/permissions dependency is documented before broad multi-user usage.

## 9. Build Later Backlog Issues

### 9.1 Build Later: Graphiti Temporal Graph Memory

- **Labels:** `vnext`, `type:evaluation`, `wave:build-later`, `track:rag`, `risk:medium`, `effort:small`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Later](../../strategy/atlas-vnext-strategy-report.md#93-build-later)

Acceptance criteria:

- [ ] Evaluate Graphiti as a backend-only experiment before exposing it to Hermes or OpenClaw.
- [ ] Define strict `group_id` namespacing.
- [ ] Document how it augments LangMem rather than replacing it.

### 9.2 Build Later: SigLIP 2 Vectorizer Upgrade Path

- **Labels:** `vnext`, `type:evaluation`, `wave:build-later`, `track:rag`, `risk:medium`, `effort:small`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Build Later](../../strategy/atlas-vnext-strategy-report.md#93-build-later)

Acceptance criteria:

- [ ] Add an opt-in image vectorizer value or migration plan.
- [ ] Document collection dimension and revectorization implications.
- [ ] Do not silently change existing vector dimensions.

### 9.3 Build Later: Iceberg + DuckDB With Lakekeeper Evaluation

- **Labels:** `vnext`, `type:evaluation`, `wave:build-later`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [vNext Top 20](../../strategy/atlas-vnext-strategy-report.md#7-vnext-top-20), [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Build Later](../../strategy/atlas-vnext-strategy-report.md#93-build-later)

Acceptance criteria:

- [ ] Create or document an `analytics` bucket over MinIO artifacts.
- [ ] Provide one notebook that writes and reads Iceberg tables through DuckDB.
- [ ] Evaluate Lakekeeper only if REST catalog write/concurrency needs are demonstrated.
- [ ] Do not add Trino or Superset before this foundation has real datasets.

### 9.4 Build Later: OpenBB + CCXT Financial Research Kit

- **Labels:** `vnext`, `type:implementation`, `wave:build-later`, `track:trading`, `risk:high`, `effort:medium`
- **Source:** [Trading / Financial-AI track](../../strategy/atlas-vnext-strategy-report.md#82-trading--financial-ai-track), [Build Later](../../strategy/atlas-vnext-strategy-report.md#93-build-later)

Acceptance criteria:

- [ ] Add notebook/backend library scaffolding for read-only market data.
- [ ] Add paper portfolio examples using JupyterHub, MinIO datasets, MLflow runs, and LiteLLM summaries where available.
- [ ] Explicitly block live exchange keys in the first slice.
- [ ] Document dependency on secrets management before exchange-key workflows.

### 9.5 Build Later: Blender MCP + glTF-Transform Asset Bridge

- **Labels:** `vnext`, `type:evaluation`, `wave:build-later`, `track:creative-3d`, `risk:high`, `effort:medium`, `track:mcp`
- **Source:** [3D / game-generation track](../../strategy/atlas-vnext-strategy-report.md#81-3d--game-generation-track), [Build Later](../../strategy/atlas-vnext-strategy-report.md#93-build-later)

Acceptance criteria:

- [ ] Add disabled localhost-only Blender MCP profile.
- [ ] Do not expose Blender MCP through Kong by default.
- [ ] Add containerized or documented glTF-Transform postprocess job for GLB inspection/optimization.
- [ ] Document code-execution risk and host-tool assumptions.

## 10. Watchlist Issues

Create these as watchlist issues, not active build tasks.

### 10.1 Watchlist: imgproxy Asset Thumbnailing

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:creative-3d`, `risk:medium`, `effort:small`
- **Source:** [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit after dashboard or asset-browser work lands.
- [ ] Define whether Atlas needs image thumbnailing, transformations, or media proxying.
- [ ] Confirm route/auth model before exposing image transformations.

### 10.2 Watchlist: NocoDB Human-In-The-Loop Queues

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:platform`, `risk:medium`, `effort:medium`
- **Source:** [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit after SSO and workflow cleanup are clearer.
- [ ] Identify a concrete human-review queue before adding the service.
- [ ] Avoid introducing a second admin database UI without a product workflow.

### 10.3 Watchlist: NeoDash Graph Dashboards

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:rag`, `risk:medium`, `effort:small`
- **Source:** [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit once Atlas has richer graph-native application data.
- [ ] Define whether NeoDash complements or duplicates the Atlas root dashboard.
- [ ] Ensure graph dashboard data is namespaced.

### 10.4 Watchlist: WhisperX Audio/Meeting Ingestion

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:rag`, `track:voice`, `risk:medium`, `effort:medium`
- **Source:** [RAG track later wave](../../strategy/atlas-vnext-strategy-report.md#83-rag-and-content-ingestion-track), [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit when meeting/audio ingestion becomes a named workflow.
- [ ] Document diarization, pyannote token/model terms, and resource implications.
- [ ] Define provenance model for audio-derived text.

### 10.5 Watchlist: Dagster Asset Orchestration

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit only after deciding how Dagster coexists with Airflow.
- [ ] Do not add a second scheduler with unclear ownership.
- [ ] Identify a concrete asset-lineage workflow first.

### 10.6 Watchlist: Trino Multi-User SQL

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit after Iceberg + DuckDB has real datasets.
- [ ] Confirm multi-user SQL demand over object storage.
- [ ] Define auth and catalog boundaries before adding.

### 10.7 Watchlist: Superset BI

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit after Trino/Iceberg or Postgres analytics schemas have useful datasets.
- [ ] SSO must be credible before adding broad BI surfaces.
- [ ] Document whether Superset complements or competes with Grafana/dashboard surfaces.

### 10.8 Watchlist: TimescaleDB Trading Data

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:trading`, `risk:high`, `effort:medium`
- **Source:** [Trading / Financial-AI track](../../strategy/atlas-vnext-strategy-report.md#82-trading--financial-ai-track), [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit as part of a later trading-data slice, not as standalone platform infrastructure.
- [ ] Define tick/order-book/time-series retention policies.
- [ ] Prefer isolated schemas and read-only/paper guardrails first.

### 10.9 Watchlist: OpenBao Secrets Alternative

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:identity-security`, `risk:high`, `effort:medium`
- **Source:** [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit if Infisical is insufficient or Vault-lineage compatibility becomes a requirement.
- [ ] Do not adopt before Atlas has a concrete secrets lifecycle and operator story.
- [ ] Document storage, unseal, backup, and bootstrap implications.

### 10.10 Watchlist: Lakekeeper Iceberg Catalog

- **Labels:** `vnext`, `type:watchlist`, `wave:watchlist`, `track:data-ml`, `risk:medium`, `effort:medium`
- **Source:** [Watchlist](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Revisit only if Iceberg + DuckDB proves catalog write/concurrency pressure.
- [ ] Compare against the simplest possible local catalog path.
- [ ] Do not add before MinIO analytics has real data.

## 11. Deferred And Rejected-For-Now Decision Issues

### 11.1 Deferred: Firecrawl

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:rag`, `risk:medium`, `effort:medium`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now), [Rejected/deferred candidates](../../strategy/atlas-vnext-strategy-report.md#103-rejected--deferred-candidates)

Revisit criteria:

- [ ] Crawl4AI leaves important extraction gaps.
- [ ] License and worker/Playwright footprint are acceptable for Atlas.
- [ ] Atlas needs Firecrawl-specific functionality that cannot be achieved through Crawl4AI plus existing services.

### 11.2 Deferred: Browserless

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:rag`, `risk:medium`, `effort:medium`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Crawl4AI cannot cover critical JavaScript-rendered workflows.
- [ ] Atlas accepts SSPL and Chromium memory cost for a named workflow.
- [ ] Resource limits and auth model are designed before exposure.

### 11.3 Deferred: Supabase Edge Functions

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:async-jobs`, `risk:medium`, `effort:medium`, `epic:async-jobs`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Backend, n8n, Celery, and Airflow do not cover a concrete server-side execution need.
- [ ] Atlas has an edge-specific use case.
- [ ] Deno function surface does not duplicate the established async-job pattern.

### 11.4 Deferred: OpenLIT

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:observability`, `risk:medium`, `effort:medium`, `epic:observability`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Langfuse plus OTel/Tempo/Loki fails to cover a named observability need.
- [ ] Atlas needs OpenLIT-specific functionality without adding UI overlap.
- [ ] Integration cost is lower than extending the planned observability stack.

### 11.5 Rejected For Now: Live Trading Services

- **Labels:** `vnext`, `type:decision`, `wave:rejected-for-now`, `track:trading`, `risk:high`, `effort:large`
- **Source:** [Trading / Financial-AI track](../../strategy/atlas-vnext-strategy-report.md#82-trading--financial-ai-track), [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Paper mode, secrets management, audit logs, and explicit operator risk controls are already shipped.
- [ ] Hummingbot, Freqtrade, and NautilusTrader are considered only as sandbox/paper services first.
- [ ] The project has clear disclaimers and no default live-trading behavior.

### 11.6 Deferred To Notebooks: FinRL And FinGPT

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:trading`, `risk:high`, `effort:medium`
- **Source:** [Trading / Financial-AI track](../../strategy/atlas-vnext-strategy-report.md#82-trading--financial-ai-track), [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Atlas has curated datasets, eval criteria, and paper-trading guardrails.
- [ ] These remain research notebook assets rather than production trading intelligence by default.
- [ ] No issue or PR presents them as push-button trading AI.

### 11.7 Deferred: Heavy 3D/Game Infrastructure

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:creative-3d`, `risk:high`, `effort:large`
- **Source:** [3D / game-generation track](../../strategy/atlas-vnext-strategy-report.md#81-3d--game-generation-track), [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Asset pipeline, thumbnails, glTF processing, and MCP safety posture are already real.
- [ ] Hunyuan3D, TRELLIS/TRELLIS.2, Nerfstudio, Unreal MCP, and LiveKit each have a concrete workflow and resource budget.
- [ ] Blender/Unreal-style editor automation is never exposed through Kong by default.

### 11.8 Deferred: Voicebox, OmniVoice, And Unmute

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:voice`, `risk:medium`, `effort:medium`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Atlas has a clearer realtime speech workflow.
- [ ] Integration path does not require Atlas to own an immature HTTP wrapper.
- [ ] Provider exposes the endpoint compatibility Atlas needs.

### 11.9 Deferred: Honcho

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:rag`, `risk:medium`, `effort:medium`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] LangMem and Graphiti are insufficient for a concrete memory workflow.
- [ ] AGPL posture and extra memory service weight are acceptable.
- [ ] Atlas has a clear memory ownership model.

### 11.10 Deferred: Redis Stack And RedisInsight

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:infra`, `risk:medium`, `effort:medium`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] A concrete Redis module or GUI workflow beats the image, license, and maintenance cost.
- [ ] It does not duplicate current Redis usage without product value.
- [ ] License and operational implications are documented.

### 11.11 Deferred: Perplexica And Vane

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:rag`, `risk:medium`, `effort:medium`
- **Source:** [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Atlas intentionally builds a distinct single-shot cited-answer surface.
- [ ] The candidate does not duplicate Open WebUI plus Local Deep Researcher.
- [ ] Route, auth, and data provenance are defined.

### 11.12 Deferred: Redpanda

- **Labels:** `vnext`, `type:decision`, `wave:deferred`, `track:data-ml`, `risk:medium`, `effort:large`
- **Source:** [Data / ML platform track](../../strategy/atlas-vnext-strategy-report.md#84-data--ml-platform-track), [Reject or defer](../../strategy/atlas-vnext-strategy-report.md#94-reject-or-defer-for-now)

Revisit criteria:

- [ ] Event streaming demand is proven by a concrete workflow.
- [ ] Kafka-compatible infrastructure is justified in a Docker Compose-first stack.
- [ ] Atlas has a retention, auth, and operator story for event streams.

### 11.13 Already Shipped: Prometheus Baseline

- **Labels:** `vnext`, `type:decision`, `wave:already-shipped`, `track:observability`, `risk:low`, `effort:small`
- **Source:** [Watchlist / already shipped](../../strategy/atlas-vnext-strategy-report.md#104-watchlist--already-shipped)

Acceptance criteria:

- [ ] Record that Prometheus is already shipped and not a vNext service-addition issue.
- [ ] Future observability work should target Langfuse, OTel Collector, Tempo, and Loki around the existing Prometheus/Grafana baseline.
- [ ] Close as done once the Project board has the observability epic and related active/backlog issues.

## 12. Creation Order

1. Create labels.
2. Create the Project.
3. Create epic issues.
4. Create Build Now implementation issues and link them to epics.
5. Create Build Next and Build Later backlog issues.
6. Create watchlist and deferred/rejected decision issues.
7. Add all issues to the Project.
8. Set Project fields according to wave, track, effort, risk, type, and priority.
9. Verify issue count and Project coverage against this spec.

Expected issue count:

- 5 epic issues
- 7 Build Now issues
- 8 Build Next issues
- 5 Build Later issues
- 10 watchlist issues
- 13 deferred/rejected/already-shipped decision issues
- **48 total issues**

## 13. Verification

Before considering the ticketing pass complete:

- [ ] `gh label list --limit 200` shows all required labels.
- [ ] `gh project list --owner thekaveh --format json` shows `Atlas vNext Roadmap`.
- [ ] `gh issue list --label vnext --limit 200` shows the expected issue count.
- [ ] Each Build Now issue has a report link, acceptance criteria, and at least one epic label where applicable.
- [ ] All Build Now issues are in Project status `Build Now`.
- [ ] Deferred/rejected issues are not in `Build Now`.
- [ ] `python scripts/check_doc_links.py` passes after this spec is committed.

## 14. Open Decisions

- Whether to use GitHub's sub-issues UI if available for the repository, or rely on issue body links and labels for epic relationships.
- Whether to create all 48 issues in one scripted pass or create epics plus Build Now manually first, then bulk-create the rest.
- Whether to keep the existing `LinguAI Kanban` project separate or migrate any relevant Atlas items from it later. The vNext board should be separate by default.
