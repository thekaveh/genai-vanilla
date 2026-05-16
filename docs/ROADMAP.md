# GenAI Vanilla Stack Roadmap

This document outlines future development plans and enhancements for the GenAI Vanilla Stack.

## Current status

The stack now orchestrates 30+ services across AI inference, workflow automation, data science, document processing, speech, and the Supabase ecosystem. An additional 30 candidate services are tracked across the Tier 1/2/3 sections below, including labelled sub-sections for the **3D / game-generation**, **financial / trading-AI**, and **RAG-enhancement** strategic tracks. Architectural milestones to date:
- Dynamic Kong API Gateway configuration
- Python cross-platform bootstrapping with CLI SOURCE overrides
- Service integration spanning Ollama, ComfyUI, n8n, Open WebUI, SearxNG, Supabase, Neo4j, OpenClaw, Weaviate, JupyterHub, and more

## Development roadmap

### Completed

**JupyterHub data science IDE**
- Interactive Jupyter Lab environment
- Pre-configured AI/ML libraries (Ollama, LangChain, LlamaIndex, Transformers)
- Sample notebooks for all service integrations
- Persistent workspace with Docker volumes

**Speech-to-Text layer (pluggable)**
- OpenAI-compatible `/v1/audio/transcriptions` across all backends
- Speaches (Faster-Whisper) — CPU-friendly default, multilingual
- NVIDIA Parakeet-TDT — CC-BY-4.0 SOTA for English/EU langs
- whisper.cpp — first-class Apple Silicon (Metal + Core ML / ANE)
- Parakeet-MLX — alternative macOS-native option
- Integration with Open WebUI for voice chat

**Text-to-Speech layer (pluggable)**
- OpenAI-compatible `/v1/audio/speech` across all backends
- Speaches (Kokoro + Piper voices) — CPU-friendly default
- Chatterbox (Resemble AI, MIT) — 5-sec zero-shot voice cloning, 23 langs
- Previously shipped with XTTS v2 (CPML / non-commercial) — retired
  2026-05 after the openedai-speech upstream archived its image

**Document processing service (Docling)**
- Document processing with IBM Docling
- PDF, DOCX, PPTX, HTML, image parsing
- Table extraction (DocLayNet + TableFormer)
- RAG-ready chunking with structure awareness
- GPU acceleration (4.3x speedup for tables)

**Unified LLM gateway (LiteLLM)**
- Always-on OpenAI-compatible front door for every LLM provider. Pinned image: `ghcr.io/berriai/litellm:v1.83.14-stable.patch.2`. Listens on port 63012.
- Wizard model: locked LiteLLM tile + selectable LLM Engine (single-select Ollama upstream: `ollama-container-cpu/gpu`, `ollama-localhost`, `ollama-external`, `none`) + three multi-enable Cloud tiles (OpenAI, Anthropic, OpenRouter).
- Bootstrapper auto-generates `LITELLM_MASTER_KEY` on first start and refuses to start when no upstream is configured (engine=none + all cloud disabled).
- Persistence: dedicated `litellm` database on the existing Supabase Postgres (Prisma migrations run automatically). Redis used for response cache + rate-limit state.
- Consumers (Backend, Open WebUI, n8n, JupyterHub, Local Deep Researcher, OpenClaw Gateway, Weaviate) all read `LITELLM_BASE_URL` + `LITELLM_API_KEY`. Documented backup option: Portkey AI Gateway.

**LangMem persistent memory**
- Automated fact extraction from conversations via Ollama LLM
- Semantic memory recall via Weaviate with pgvector fallback
- Memory consolidation and deduplication (nightly via n8n)
- Open WebUI tool for manual memory management (remember, recall, forget)
- Auto-extraction filter for conversations
- Embedded in Backend service (no separate container)
- Dual vector backend: Weaviate preferred, pgvector fallback

**MinIO object storage (artifact tier)**
- S3-compatible artifact-tier storage server (Go, AGPL-v3). Pinned to `minio/minio:RELEASE.2025-09-07T16-13-09Z` (most recent stable tag on Docker Hub; the GitHub-only service-account-CVE release `RELEASE.2025-10-15T17-29-55Z` is not yet available as a Docker image — bump the pin when a fixed image lands upstream).
- Five pre-provisioned buckets — `comfyui`, `backend`, `n8n`, `jupyter`, `docling` — each with a scoped service-account credential surfaced as `MINIO_<NAME>_ACCESS_KEY` / `MINIO_<NAME>_SECRET_KEY` in `.env`.
- Admin console at `http://localhost:63031`; S3 API at `http://localhost:63030` (host) / `http://minio:9000` (internal).
- Complements Supabase Storage rather than replacing it. Per-consumer wiring (ComfyUI, Backend, n8n, JupyterHub, Doc Processor) ships in dedicated follow-up PRs — credentials and bucket names are in `.env` from day one for opt-in by env-only change.

---

### Tier 1: high-priority candidates

**Enhanced vector search (Weaviate optimization)**
- Multi-model embedding support
- Advanced query capabilities
- Performance optimizations for large datasets
- Better integration with research workflows

**Python migration completion**
- Complete migration from Bash to Python for all scripts
- Cross-platform compatibility
- Dependency management with UV
- Improved error handling and logging

_Delivered — see "Completed" section below for the LiteLLM gateway entry._

**Per-service configuration modularization** — ✅ delivered (Phases A–E, May 2026)
- Compose: 1,425-line monolithic `docker-compose.yml` → 55-line thin `include:`-shell that pulls in `services/<name>/compose.yml` fragments (one per service family — supabase, redis, minio, neo4j, litellm, ollama, weaviate, comfyui, n8n, open-webui, backend, searxng, jupyterhub, parakeet, speaches, chatterbox, docling, openclaw, hermes, local-deep-researcher, kong, plus virtual cloud-providers, tts-provider, and globals manifests).
- Manifests: `services/<name>/service.yml` is the single source of truth for env vars (with auto_managed/secret flags), source variants, image refs, and dependencies. JSON-schema-validated. Bootstrapper runtime data lives under per-manifest `runtime_sc:`/`runtime_adaptive:`/`runtime_deps:` blocks; `bootstrapper/services/sc_synthesizer.py` reassembles the dict that `ConfigParser.load_yaml_config()` returns.
- Safety nets: `bootstrapper/services/manifest_validator.py` (cross-manifest checks), `tools/validate_fragments.py` CLI lint with `--check-env-example`, and `tests/test_fragment_equivalence.py` (golden `rendered_config_baseline.yml` diff — byte-equivalence proven across the 36-container stack).
- Locality: every service's source code, init scripts, build context, and config files live under `services/<name>/<subdir>/`. Repo top-level is just `bootstrapper/`, `docs/`, `services/`, plus standard files.

**Monitoring stack (Prometheus + Grafana)**
- Service metrics: request rates, latency percentiles, container health
- Service performance dashboards
- Resource usage visualization
- Alerting for service issues

**Enhanced security features**
- Service-to-service authentication
- API rate limiting enhancements
- Audit logging capabilities
- Security hardening guides

**MCP gateway (`mcpo` + MetaMCP)**
- Model Context Protocol gateway: aggregates self-hosted MCP servers into a unified, namespaced tool surface for every LLM consumer in the stack
- Two-part deployment — **`mcpo`** (from the Open WebUI org, MIT) wraps any MCP server as an OpenAPI endpoint; **MetaMCP** (MIT, metatool-ai/metamcp) adds namespace-based aggregation/RBAC once more than 2–3 MCP servers are wired up
- Open WebUI already speaks MCP natively as of v0.6.31; `mcpo` is the lowest-friction first deployment
- Exposes existing stack capabilities (Postgres, Neo4j, Weaviate, SearXNG, ComfyUI, n8n workflows, OpenBB Platform, NautilusTrader) as MCP tools without bespoke per-consumer glue

**Stack integration points:**

Depends on (services the MCP gateway would consume):
- **Backend MCP servers** wrapping Postgres / Weaviate / Neo4j / SearXNG / ComfyUI / n8n / domain endpoints
- **Kong API Gateway** — exposes the MCP gateway via an `mcp.localhost` route
- **Supabase (PostgreSQL)** — MetaMCP namespace and auth persistence (when MetaMCP is added)

Consumed by (services that would call the MCP gateway):
- **Open WebUI** — native MCP client (v0.6.31+)
- **Hermes** — agent tool surface
- **Backend (FastAPI)** — programmatic tool invocation from application code
- **n8n** — workflow nodes invoking MCP tools
- **OpenClaw** — messaging-platform agents reuse the same tool catalog
- **Local Deep Researcher** — research workflows tap MCP-exposed sources

**Langfuse — LLM observability and evaluation**
- Open-source LLM tracing, prompt management, dataset, and evaluation platform (MIT)
- LiteLLM ships a **native Langfuse callback** — zero-glue integration of every gateway-routed call (consumers automatically gain traces)
- Closes the LLM-specific observability gap that Prometheus + Grafana (infra metrics) does not address: prompt versioning, prompt-level cost/latency attribution, eval scoring, conversation replay
- Self-hosted footprint reuses the stack's Postgres + Redis + MinIO; adds ClickHouse for high-volume trace events

**Stack integration points:**

Depends on (services Langfuse would consume):
- **Supabase (PostgreSQL)** — control-plane metadata
- **ClickHouse** — high-volume trace event store (added alongside)
- **Redis** — queueing and rate-limit state
- **MinIO** — large-payload offload (optional)

Consumed by (services that would call Langfuse):
- **LiteLLM gateway** — primary callback emitter; all routed traffic gets traced
- **Hermes** — agent traces with tool-call spans
- **Backend (FastAPI)** — application-level traces
- **n8n** — workflow LLM-node tracing
- **Open WebUI** — chat-session traces
- **Local Deep Researcher** — multi-step research trace timelines

**Infisical — secrets management**
- Open-source secrets manager (API + UI) with versioning, rotation, audit logs, and per-environment scoping
- Removes the current pattern of every service reading credentials directly from `.env`; secrets are fetched at runtime (or injected at container start via the Infisical agent)
- Critical preparation step before the stack adopts use-cases that hold third-party credentials at scale: exchange API keys (financial / trading track), signed model-download URLs (3D track), tenant-scoped API tokens (RAG SaaS variants)
- Self-hosted footprint reuses the existing Supabase Postgres and Redis

**Stack integration points:**

Depends on (services Infisical would consume):
- **Supabase (PostgreSQL)** — secret and version storage
- **Redis** — caching and session state

Consumed by (services that would call Infisical):
- **All `.env`-reading services** — Backend, n8n, Hermes, OpenClaw, LiteLLM, Weaviate, Neo4j integrations, ComfyUI, JupyterHub, and the trading- / 3D-track candidates — via the Infisical agent / SDK injection pattern at container start
- **Bootstrapper** — `.env` generation can pull live values from Infisical instead of hard-coding them in `.env.example`

---

### Tier 2: planned candidates

**LangFlow (AI workflow & agent builder)**
- Low-code visual builder for AI agents and RAG pipelines
- Python-native extensibility aligned with the AI/ML ecosystem
- Complements n8n: LangFlow for deep AI pipelines, n8n for system orchestration
- MIT licensed, 147k+ GitHub stars, backed by DataStax

**Stack integration points:**

Depends on (services LangFlow would consume):
- **Ollama** — local LLM inference for model nodes
- **Weaviate** — vector store for RAG retrieval pipelines
- **Supabase (PostgreSQL)** — flow persistence and metadata storage
- **Redis** — caching and session state
- **SearxNG** — web search tool for AI agents

Consumed by (services that would call LangFlow):
- **n8n** — orchestrates business logic around LangFlow AI endpoints
- **Backend (FastAPI)** — invokes LangFlow flows as API calls
- **JupyterHub** — notebook-based experimentation with LangFlow APIs
- **Open WebUI** — potential frontend for LangFlow-powered agents

**LightRAG (graph-enhanced RAG framework)**
- Graph + vector hybrid retrieval framework combining knowledge graph extraction with semantic search
- 52-85% comprehensiveness gains over traditional vector-only RAG (EMNLP 2025, peer-reviewed)
- Dual retrieval: vector similarity search + graph traversal of entity relationships
- 5 query modes: naive, local, global, hybrid, mix
- 32.8k GitHub stars, backed by academic research (HKUDS)

**Stack integration points:**

Depends on (services LightRAG would consume):
- **Neo4j** — knowledge graph storage for entity-relationship retrieval (already deployed)
- **Ollama** — LLM inference for entity extraction during indexing and query generation (already deployed)
- **Weaviate** — vector embeddings for semantic retrieval (already deployed)
- **Docling** — document parsing and structured extraction (already deployed, substitutes for RAG-Anything)
- **Supabase (PostgreSQL)** — optional all-in-one storage backend (already deployed)
- **OpenSearch** — optional unified storage backend (candidate)
- **TEI (Text Embeddings Inference)** — preferred dedicated embedding + rerank backend (candidate; see Tier 2)

Consumed by (services that would call LightRAG):
- **Backend (FastAPI)** — graph-enhanced RAG API for research and document Q&A
- **n8n** — RAG-powered workflows with graph context
- **LangFlow** — retrieval component in AI pipelines
- **JupyterHub** — notebook-based experimentation with graph RAG
- **Open WebUI** — knowledge-grounded chat with structural understanding

**RAG-Anything (multimodal document processing for RAG)**
- All-in-one multimodal RAG framework handling text, images, tables, equations, charts, and multimedia
- Built by the same team as LightRAG (HKUDS), designed as its multimodal preprocessor
- Unified knowledge entity processing across all document modalities
- Complements Docling: Docling excels at structured document parsing (PDF tables, layout analysis), RAG-Anything excels at multimodal knowledge entity extraction for graph construction

**Stack integration points:**

Depends on (services RAG-Anything would consume):
- **Ollama** — LLM inference for multimodal entity extraction (already deployed)

Consumed by (services that would call RAG-Anything):
- **LightRAG** — primary consumer for multimodal document ingestion into knowledge graphs
- **Backend (FastAPI)** — multimodal document processing API

**TEI (Text Embeddings Inference) + reranker mode**
- HuggingFace's official high-performance embedding and reranking inference server (Apache-2.0); Rust/CUDA core, OpenAI-compatible `/embeddings` route plus a dedicated `/rerank` route
- Offloads bulk embedding traffic from LiteLLM (whose strength is chat completions, not high-throughput embedding pipelines)
- Adds a reranking layer (BGE-rerank, mxbai-rerank, Cohere-rerank-style) — typical +20–30% retrieval recall when chained after vector search
- Single GPU container; multiple instances can sit behind LiteLLM for model-specific routing

**Stack integration points:**

Depends on (services TEI would consume):
- None at runtime (model weights cached in a named volume; downloaded on first start)

Consumed by (services that would call TEI):
- **LiteLLM gateway** — TEI registered as a model upstream so existing consumers reach it via the unified API
- **LightRAG** — embedding generation during indexing, reranker stage after graph + vector retrieval
- **Weaviate** — alternative external vectorizer to the bundled multi2vec-clip module
- **Backend (FastAPI)** — direct calls for tight loops (chunk + embed pipelines)
- **n8n** — embedding step in RAG workflows
- **Mem0 / Letta** — embedding backend for agent-memory writes

**SilverBullet — server-first markdown personal knowledge management**
- Server-hosted markdown PKM (MIT); notes are plain `.md` files on disk with a Lua-scriptable query and automation layer
- Different shape from Obsidian / Logseq (client-centric) and AppFlowy / AFFiNE (database-backed) — files-on-disk is what RAG ingestion wants
- Becomes the authored-content surface in a personal-RAG workflow: human-curated notes flow directly into LightRAG / Weaviate / OpenSearch indexes

**Stack integration points:**

Depends on (services SilverBullet would consume):
- None at runtime (filesystem volume only)

Consumed by (services that would call SilverBullet):
- **LightRAG** — ingestion source for entity-graph construction over authored notes
- **Weaviate** — alternative vector ingestion target (semantic search across notes)
- **Backend (FastAPI)** — read / search / edit-note APIs exposed via Kong route
- **Open WebUI** — knowledge tools can cite SilverBullet pages

**Karakeep — AI-native bookmark, note, and image hoarder**
- Self-hosted personal-RAG capture surface (formerly Hoarder, MIT); auto-tagging via Ollama, OCR'd image search, browser extension and mobile apps
- Complements SilverBullet — Karakeep is *captured* content (links, articles, screenshots), SilverBullet is *authored* content. Both feed the same downstream RAG indexes.
- Roadmapped embedding and RAG features upstream; today's value is a MeiliSearch-indexed, AI-tagged personal corpus

**Stack integration points:**

Depends on (services Karakeep would consume):
- **Ollama** — auto-tagging and summarization model calls (built-in)
- **MeiliSearch** — internal full-text index (bundled by Karakeep)

Consumed by (services that would call Karakeep):
- **Backend (FastAPI)** — query saved items as a RAG retrieval source
- **LightRAG** — ingestion of bookmark archives into the entity graph
- **Weaviate** — semantic search over captured content
- **n8n** — capture-trigger workflows (e.g. "RSS item → Karakeep")

**Crawl4AI — LLM-friendly web crawler**
- Apache-2.0 Playwright-based crawler purpose-built for LLM ingestion: clean Markdown output, structured extraction strategies, sitemap traversal, JavaScript-rendered page support
- Apache-2.0 license is intentional — Firecrawl-self-hosted (AGPL-3.0) is incompatible with this stack's permissive boilerplate posture
- Fills the web-ingestion gap for both RAG (article corpora) and trading-AI (filings / news / sentiment scrape) use-cases
- Lighter than running a full Browserless cluster for one-shot scrapes; pair them when both batch crawl and persistent sessions are needed

**Stack integration points:**

Depends on (services Crawl4AI would consume):
- None at runtime (bundled Chromium)
- Optional **MinIO** — large-output offload bucket

Consumed by (services that would call Crawl4AI):
- **Hermes** — web-fetch tool for agents
- **n8n** — HTTP node invokes crawl jobs as workflow steps
- **Backend (FastAPI)** — programmatic ingest endpoints
- **LightRAG** — bulk ingestion source for fresh web content
- **Local Deep Researcher** — supplements SearXNG metasearch with deep page extraction

**GROBID — scholarly PDF extraction**
- Apache-2.0 machine-learning PDF parser specializing in scholarly / research documents (citation extraction, header / section structure, bibliography normalization, table-of-figures)
- Complements Docling: Docling is general-purpose structured parsing (DocLayNet + TableFormer); GROBID is scholarly-specific (TEI XML output, citation graphs, DOI / PubMed enrichment)
- Critical for research-RAG and financial-research-RAG (analyst reports, 10-K / 10-Q filings, earnings transcripts) where citation lineage matters

**Stack integration points:**

Depends on (services GROBID would consume):
- None at runtime

Consumed by (services that would call GROBID):
- **Backend (FastAPI)** — scholarly-PDF ingestion endpoints
- **LightRAG** — extracted citations feed the entity graph naturally
- **n8n** — batch document-processing workflows
- **JupyterHub** — research-notebook citation workflows

**Apache Tika — broad-format text and metadata extraction**
- Apache-2.0 content analysis toolkit supporting 1000+ formats (Office docs, email, archives, audio / video metadata, source code, structured data)
- Pre-Docling fallback for the long tail of formats Docling does not target (mailbox archives, legacy Office, multimedia metadata)
- Standalone server mode exposes a REST endpoint suitable for direct consumption by n8n / backend
- Pairs naturally with Stirling-PDF (PDF preprocessing) and GROBID (scholarly PDF) to cover the full ingestion-format matrix

**Stack integration points:**

Depends on (services Apache Tika would consume):
- None at runtime (JVM only)

Consumed by (services that would call Apache Tika):
- **Backend (FastAPI)** — generic file-extraction route
- **n8n** — format-detection and extraction nodes in ingestion workflows
- **LightRAG / Weaviate** — upstream of indexing for non-Docling formats

**Stirling-PDF — PDF preprocessing toolkit**
- Self-hosted PDF manipulation suite (MIT): split / merge / rotate / sign / redact / OCR-via-Tesseract, plus a web UI for ad-hoc operations
- Sits *before* Docling and GROBID in the ingestion pipeline — clean up malformed / scanned / multi-document PDFs so structured parsers can do their job
- Closes the "user uploads a weird PDF" gap without burdening Docling

**Stack integration points:**

Depends on (services Stirling-PDF would consume):
- None at runtime

Consumed by (services that would call Stirling-PDF):
- **Backend (FastAPI)** — preprocessing route called before handing off to Docling / GROBID
- **n8n** — preprocessing step in document-ingest workflows
- **Open WebUI** — user-uploaded-PDF preprocessing before chat-with-PDF flows

**Mem0 — external agent memory layer**
- Open-source agent-memory framework (Apache-2.0) providing per-user, per-agent persistent memory with automatic extraction, deduplication, and recall
- Different scope from the existing **LangMem** (which is embedded in the backend service and Open-WebUI-centric): Mem0 is an external service usable across Hermes, OpenClaw, and other agent runtimes uniformly
- Reuses the existing Weaviate (vector) and Supabase Postgres — no new datastore

**Stack integration points:**

Depends on (services Mem0 would consume):
- **Weaviate** — vector backend for memory recall
- **Supabase (PostgreSQL)** — structured memory metadata
- **LiteLLM gateway** — extraction-LLM calls during memory writes
- **TEI** — preferred embedding backend (or LiteLLM-routed embeddings as fallback)

Consumed by (services that would call Mem0):
- **Hermes** — primary consumer; replaces the file-based `/opt/data` memory with structured recall
- **OpenClaw** — per-channel-user memory across messaging platforms
- **Backend (FastAPI)** — multi-tenant memory for external API clients
- **Open WebUI** — alternative memory backend to LangMem

**whisperX / faster-whisper-server — diarization and word-level timestamps**
- Adds speaker diarization (pyannote.audio) and forced-alignment word-level timestamps on top of Whisper-style STT
- Parakeet and Speaches handle transcription; neither does diarization — adding whisperX unlocks meeting / podcast / earnings-call RAG with per-speaker turn attribution
- Optional companion or replacement depending on `STT_PROVIDER_SOURCE` choice

**Stack integration points:**

Depends on (services whisperX would consume):
- Bundled Faster-Whisper plus pyannote models; no runtime service dependencies

Consumed by (services that would call whisperX):
- **Backend (FastAPI)** — long-form audio transcription endpoint with speaker turns
- **n8n** — audio-ingest workflows (recordings → diarized transcripts → RAG)
- **LightRAG** — transcripts feed the entity graph with speaker-as-entity edges
- **Local Deep Researcher** — research from podcast / earnings-call audio sources

**Browserless v2 — persistent headless-Chrome sessions**
- Headless Chrome managed via Playwright / Puppeteer WebSocket endpoints; sits one layer below Crawl4AI
- **Different role from Crawl4AI**: Browserless gives long-lived authenticated browser sessions for *agentic* browsing (form fill, multi-step login flows, broker dashboards, paywalled research portals); Crawl4AI does one-shot scraping
- **Licensing flag:** Browserless v2 is SSPL-1.0 — review against deployment posture before adoption; consider Playwright-server (Apache-2.0) as an alternative

**Stack integration points:**

Depends on (services Browserless would consume):
- None at runtime (bundled Chromium)

Consumed by (services that would call Browserless):
- **Hermes** — agentic browsing tool (e.g. `browser-use` SDK as a Hermes skill)
- **Backend (FastAPI)** — automated portal-scrape and form-submit routes
- **n8n** — multi-step browser-automation workflow nodes
- **Crawl4AI** — falls back to Browserless when a target needs persistent session handling

**Alternative vector database (Qdrant)**
- Qdrant as alternative to Weaviate
- Comparative performance analysis
- Migration tools between vector databases
- User choice in vector database backend

**Enhanced n8n integration**
- Pre-built AI workflow templates
- Better integration with vector databases
- Advanced data processing workflows
- Custom node development

**Hermes Agent (programmable AI agent for chat & messaging)** ✓ **shipped**

Lives in [docs/services/hermes.md](services/hermes.md). Shipped as the
`hermes` service (`nousresearch/hermes-agent:latest` — upstream publishes
only `latest` + per-commit `sha-<digest>` tags, no semver; production
pins via `HERMES_IMAGE=nousresearch/hermes-agent:sha-...`) plus
`hermes-init` companion. Registered in the LiteLLM model catalog as
`hermes-agent`, so every consumer (Open-WebUI, n8n, backend, jupyterhub,
openclaw) sees it in the model dropdown automatically. Dashboard exposed
at `http://hermes.localhost:63002`.

Consumes (when enabled, via the LiteLLM gateway and `hermes-init`'s
config.yaml rendering):
- **LiteLLM gateway** — required; Hermes reasons over `http://litellm:4000/v1`
- **ComfyUI** — image generation invoked as a tool from agent personas (auto-wired via skill-override file)
- **TTS provider (Speaches / Chatterbox)** — speech output for voice-enabled responses (`TTS_ENDPOINT`)
- **STT provider (Speaches / Parakeet / whisper.cpp)** — speech input for voice-driven conversations (`STT_ENDPOINT`)
- **SearXNG** — web search tool (no API key required)

Consumed by:
- **Open WebUI** — primary chat surface; `hermes-agent` appears in the model dropdown via LiteLLM
- **OpenClaw** — bridges Hermes agents to WhatsApp / Telegram / Discord channels
- **Backend (FastAPI)** — programmatic agent invocation from application code
- **n8n** — agent-driven automation workflows

Correction to the prior Tier-2 sketch: Hermes is **file-based**, not
Postgres-backed. The earlier line claiming Supabase as a Hermes dependency
was wrong — Hermes persists everything under `/opt/data` (the `hermes-data`
named volume). Supabase is not in Hermes's dependency set.

**Alternative TTS/STT engines (already explored)**
- Piper — shipped via Speaches's bundled CPU-friendly path
- Voice cloning — shipped via Chatterbox (`chatterbox-container-gpu` /
  `chatterbox-localhost`)
- Streaming audio — Speaches and Chatterbox both expose chunked output
- Future candidates: Orpheus-TTS (streaming, GPU-only), SenseVoice (50+
  langs with emotion labels), Higgs Audio v2

---

### Tier 3: future candidates

Tier 3 is organized into four named sub-sections so the use-case tracks are scannable at a glance: **General-purpose** (horizontal candidates), **3D / game-generation track**, **Financial / trading-AI track**, and **Real-time / collaboration**.

#### General-purpose

**Apache Airflow integration**
- Workflow orchestration
- Data pipeline management
- Scheduled AI processing jobs
- Complex workflow dependencies

**MeiliSearch (lightweight full-text search)**
- Fast full-text search capabilities
- Rust-based, lightweight single binary (<1 GB RAM)
- Typo-tolerant, sub-50ms search responses out of the box
- Hybrid search (keyword + semantic) with tunable semantic ratio
- MIT licensed, 57k+ GitHub stars
- Best suited for application-level search on small-to-medium datasets

**OpenSearch (search, analytics & RAG platform)**
- Distributed search and analytics suite (Apache 2.0 licensed Elasticsearch fork)
- Full-text search, observability, security analytics (SIEM), and OpenSearch Dashboards (Kibana equivalent)
- RAG capabilities: native text chunking with configurable overlap, ingest pipelines (chunk -> embed -> index), Reciprocal Rank Fusion for hybrid search, ML Commons for internal model hosting
- Vector search via k-NN plugin (HNSW, IVF, Lucene) supporting up to 16,000 dimensions and billions of documents
- Multiple quantization options (binary 32x, scalar 50-85%, product up to 90% compression)
- Backed by AWS / Linux Foundation, 12.7k+ GitHub stars
- Heavier footprint than MeiliSearch (8-16+ GB RAM, JVM tuning required) in exchange for deeper RAG and analytics capabilities

**Stack integration points:**

Depends on (services OpenSearch would consume):
- **Supabase (PostgreSQL)** — content sync for indexing via CDC or batch jobs
- **Redis** — query result caching
- **Ollama** — embedding generation for vector indexing

Consumed by (services that would call OpenSearch):
- **Backend (FastAPI)** — full-text and hybrid search API for research results and documents
- **n8n** — search workflows, log analysis pipelines, alerting
- **JupyterHub** — data exploration and analytics notebooks
- **Open WebUI** — search across conversation history and knowledge bases
- **Local Deep Researcher** — search internal knowledge alongside web results
- **LangFlow** — retrieval component in RAG pipelines
- **OpenSearch Dashboards** — standalone UI for search analytics and visualization

**InvokeAI — Stable Diffusion canvas / inpainting workflow**
- Image-generation UI (Apache-2.0) focused on canvas, inpainting, and creative editing — genuinely complementary to ComfyUI's graph / batch model rather than a duplicate
- ComfyUI remains the existing default for parametric / batch generation; InvokeAI fills the canvas-editor gap for artist-driven workflows
- Don't adopt A1111 (Automatic1111): the project has stagnated relative to ComfyUI, Forge, and InvokeAI as of 2026

**Stack integration points:**

Depends on (services InvokeAI would consume):
- Optional **MinIO** — model and output bucket

Consumed by (services that would call InvokeAI):
- **Backend (FastAPI)** — alternative image-gen route alongside ComfyUI
- **Open WebUI** — second image-generation provider in the model picker
- **n8n** — canvas / inpaint workflow nodes
- **Hermes** — image-editing tool for agent personas

**vLLM — high-throughput GPU inference**
- High-performance LLM inference engine (Apache-2.0); PagedAttention scheduler, OpenAI-compatible REST surface, multi-tenant batching
- Parallel option to Ollama behind LiteLLM: Ollama for low-friction local serving, vLLM for production-grade GPU throughput
- Registered as another LiteLLM upstream — no consumer-side changes; consumers continue to call LiteLLM as usual

**Stack integration points:**

Depends on (services vLLM would consume):
- None at runtime (model weights cached in a named volume)

Consumed by (services that would call vLLM):
- **LiteLLM gateway** — vLLM appears as another routed-model upstream
- All existing LiteLLM consumers indirectly (Backend, Open WebUI, Hermes, n8n, JupyterHub, Local Deep Researcher, OpenClaw)

**Letta (MemGPT) — heavyweight stateful agent memory**
- Open-source MemGPT framework (Apache-2.0); agents reason over their own memory hierarchy (core, archival, recall) rather than receiving a passive recall snippet
- Heavier alternative to Mem0 for agents that need to manage their own memory state across long-running interactions
- Pair-or-pick decision rather than additive: if Mem0 (Tier 2) lands, treat Letta as the upgrade path for the subset of agents that need stateful memory management

**Stack integration points:**

Depends on (services Letta would consume):
- **Supabase (PostgreSQL)** — memory persistence
- **Weaviate** — vector recall backend
- **LiteLLM gateway** — model calls for memory operations
- **TEI** — preferred embedding backend

Consumed by (services that would call Letta):
- **Hermes** — stateful-agent variant for long-running personas
- **Backend (FastAPI)** — agents that need to plan over their memory

**Windmill — code-first workflow engine**
- Open-source workflow engine (AGPL-3.0) executing TypeScript / Python / Bash / Go / SQL scripts as composable jobs with a visual flow editor on top
- Complements n8n rather than replacing it: n8n excels at low-code system orchestration; Windmill excels at code-native ML / data pipelines (training jobs, evals, periodic backtests, scheduled ingestion)
- Self-host trade-off: AGPL license requires attention if the stack is redistributed; consider Activepieces (MIT) or Trigger.dev as alternatives

**Stack integration points:**

Depends on (services Windmill would consume):
- **Supabase (PostgreSQL)** — job metadata and run history
- **MinIO** — large input / output artifacts

Consumed by (services that would call Windmill):
- **Backend (FastAPI)** — schedules data-pipeline and eval jobs
- **n8n** — invokes Windmill code-heavy steps from low-code flows
- **JupyterHub** — exports notebooks as Windmill jobs
- **Hermes** — agents trigger backtests / evals as Windmill runs (financial track)

**AudioCraft / MusicGen — audio and music generation**
- Meta's open-source audio generation suite (MIT for code; model licenses vary — MusicGen weights are CC-BY-NC for non-commercial use; AudioGen and EnCodec have more permissive options) — text-to-music, text-to-sound-effect, conditional generation
- Closes the audio-generation gap in the media category (the stack has speech and image generation but no music / SFX synthesis)
- Useful adjacent to ComfyUI / Hermes for content-creator workflows; also pairs with the 3D track (procedural game audio)

**Stack integration points:**

Depends on (services AudioCraft would consume):
- Optional **MinIO** — generated-audio bucket

Consumed by (services that would call AudioCraft):
- **Backend (FastAPI)** — audio-gen endpoint
- **Open WebUI** — extension for inline music / SFX generation
- **n8n** — content-pipeline workflows
- **Hermes** — content-creator agent personas
- **Godot / Blender** (3D track) — procedural background music and sound effects

**Paperless-ngx — OCR'd document archive**
- Self-hosted document management (GPL-3.0): receives scanned / imported PDFs, runs OCR, auto-classifies into tagged correspondents / types, and exposes a searchable full-text index
- Long-term archival layer distinct from Docling (which parses on demand) and Stirling-PDF (which manipulates): Paperless is the durable retained-document store with metadata
- Ingestion source for personal / business RAG; useful adjacent to Karakeep (web captures) for a complete personal-corpus index

**Stack integration points:**

Depends on (services Paperless-ngx would consume):
- **Supabase (PostgreSQL)** — document metadata
- **Redis** — task queue
- Bundled Tesseract OCR; can be replaced or augmented by Docling + Stirling-PDF

Consumed by (services that would call Paperless-ngx):
- **Backend (FastAPI)** — search and retrieve archived documents as a RAG retrieval source
- **LightRAG / Weaviate** — ingestion of the archive into entity graph / vector index
- **n8n** — document-routing workflows (e.g. inbox → Paperless → tag → notify)

**Enterprise identity management (Keycloak or Authentik)**
- Advanced user management
- Single sign-on (SSO) capabilities across stack UIs (Open WebUI, Supabase Studio, Grafana, LangFlow, n8n, JupyterHub)
- Role-based access control
- Integration with external identity providers (OIDC, SAML, LDAP)
- Trade-off: **Keycloak** is enterprise-feature-complete (legacy SAML flows, fine-grained RBAC); **Authentik** is the lighter OSS-first alternative (modern UI, Python-extensible, simpler operations). Pick Authentik for greenfield deployments and Keycloak when integrating with enterprise IdPs that demand legacy protocols.

**Cloud deployment enhancements**
- AWS ECS Fargate optimization
- Kubernetes deployment manifests
- Auto-scaling capabilities
- Multi-region deployment support

**DevOps enhancements**
- CI/CD pipeline templates
- Automated testing frameworks
- Deployment automation
- Infrastructure as Code (IaC) templates

**Additional model integrations**
- Support for larger language models
- Multi-modal model support
- Specialized model integrations
- Custom model deployment pipelines

**Experimental features**
- Newer model integrations as they stabilize
- Experimental workflow patterns
- Advanced RAG techniques
- Novel application patterns

**Federation & interoperability**
- Multi-stack federation
- Standardized APIs
- Cross-platform compatibility
- Open source ecosystem integration

#### 3D / game-generation track

This track composes a full pipeline: **ComfyUI** (concept image, exists) → **Hunyuan3D-2 / TRELLIS** (image-to-3D mesh) → **Blender headless** (scene assembly and render) → **Godot headless** (game runtime). **NerfStudio** runs in parallel for real-scene capture. **LightRAG** indexes the asset graph; **AudioCraft / MusicGen** provides procedural audio.

**Blender (headless + Python API)**
- Long-established open-source 3D suite (GPL-2.0+); headless mode plus the `bpy` Python API make Blender scriptable as a backend service for rendering, mesh manipulation, scene assembly, and asset format conversion (FBX, GLB, USD, OBJ)
- The mature foundation for the 3D / game-generation track: ComfyUI generates concept images or textures, image-to-3D models (Hunyuan3D-2 / TRELLIS) produce meshes, Blender assembles them into scenes and exports to game-engine-friendly formats
- Single GPU container handles both production rendering and AI-assisted asset cleanup

**Stack integration points:**

Depends on (services Blender would consume):
- **MinIO** — texture and exported-asset bucket
- **ComfyUI** — upstream texture / concept-image generation

Consumed by (services that would call Blender):
- **Backend (FastAPI)** — scene-assembly and render-job routes
- **n8n** — asset-pipeline workflows
- **Hermes** — 3D-asset agent personas
- **Godot** (and external game engines like Unreal) — downstream asset consumer

**Hunyuan3D-2 (Tencent) or TRELLIS (Microsoft) — image-to-3D generation**
- State-of-the-art image-to-3D mesh generation (2025 / 2026). Hunyuan3D-2 is more textured-mesh focused; TRELLIS is broader (mesh, Gaussian splatting, radiance field outputs from a single image)
- Slots between ComfyUI and Blender in the 3D pipeline: image → mesh → scene assembly
- GPU-only; expect 12–24 GB VRAM for production-quality outputs

**Stack integration points:**

Depends on (services Hunyuan3D-2 / TRELLIS would consume):
- **ComfyUI** — upstream concept-image generation
- **MinIO** — output mesh bucket

Consumed by (services that would call the image-to-3D service):
- **Backend (FastAPI)** — text / image → 3D-asset API
- **Blender** — refines and re-meshes the generated outputs
- **Hermes** — 3D-generation tool for agents
- **n8n** — asset-pipeline workflows

**NerfStudio — neural-radiance-field and Gaussian-splatting reconstruction**
- Open-source 3D reconstruction toolkit (Apache-2.0): video or photo set → NeRF or 3D Gaussian Splatting scene
- Different shape from Hunyuan3D-2 / TRELLIS: NerfStudio reconstructs *existing* real-world scenes from images, where image-to-3D models *generate* new assets from concepts
- Combined value: ComfyUI generates concept → Hunyuan3D synthesizes new asset; NerfStudio captures real environments. Both feed Blender / Godot.

**Stack integration points:**

Depends on (services NerfStudio would consume):
- **MinIO** — capture-input and reconstructed-scene bucket

Consumed by (services that would call NerfStudio):
- **Backend (FastAPI)** — capture-ingest and reconstruction-status routes
- **Blender** — imports reconstructed scenes for refinement
- **Godot** — consumes reconstructed environments as game backdrops
- **n8n** — reconstruction-pipeline workflows

**Godot (headless server) — open-source game engine runtime**
- Open-source game engine (MIT) with a headless export mode usable as a server for running and testing AI-generated game scenes
- Provides the runtime half of the 3D / game-generation pipeline: Blender produces assets, Hunyuan3D-2 / NerfStudio contribute generated and reconstructed content, Godot runs the resulting game scene for automated testing or agent-driven play
- Lightweight by game-engine standards (single binary, small Docker image)

**Stack integration points:**

Depends on (services Godot would consume):
- **MinIO** — game-asset bucket
- **Blender** — primary asset upstream
- **Hunyuan3D-2 / NerfStudio** — additional asset upstreams

Consumed by (services that would call Godot):
- **Backend (FastAPI)** — scene-runtime API (load scene, capture screenshot, simulate input)
- **Hermes** — agents that play / test generated games as a tool
- **n8n** — automated game-test workflows

#### Financial / trading-AI track

This track composes a full pipeline: **OpenBB Platform** provides multi-provider financial data; **TimescaleDB** (Postgres extension on the existing Supabase Postgres) stores tick / OHLC history; **Redpanda** carries real-time exchange feeds; **NautilusTrader** runs backtests, paper-trade, and live execution; **Hermes** and **Backend** generate or tune strategies via **LiteLLM**; **Langfuse** observes LLM-driven decisions; **Infisical** holds exchange credentials.

**NautilusTrader (or Freqtrade) — algorithmic trading engine**
- High-performance Python / Rust open-source algorithmic-trading platform (LGPL-3.0); supports backtesting, paper trading, and live execution across crypto, FX, equities, and futures venues
- Alternative for crypto-only deployments: **Freqtrade** (GPL-3.0) — large community, simpler scope, Python-only
- LLM angle: backend / Hermes generate or tune strategies; Langfuse traces strategy-LLM interactions; Infisical-managed exchange API keys

**Stack integration points:**

Depends on (services NautilusTrader would consume):
- **TimescaleDB extension on Supabase Postgres** — backtest and live market-data store
- **Redpanda** — real-time market-data ingest
- **Infisical** — exchange API credentials
- **LiteLLM gateway** — strategy-tuning and signal-explanation calls

Consumed by (services that would call NautilusTrader):
- **Backend (FastAPI)** — strategy management and order-routing API
- **Hermes** — agent-driven strategy invocation
- **n8n / Windmill** — scheduled backtest and rebalance workflows
- **JupyterHub** — research notebooks
- **Langfuse** — strategy-LLM observability

**OpenBB Platform — open financial-data aggregator**
- Open-source financial-data layer (AGPL-3.0; commercial license available): unified Python and REST interface to equities, crypto, macro, news, fundamentals across many providers (yfinance, Alpha Vantage, Polygon, FRED, SEC filings, …)
- LLM-friendly schema; tool-perfect surface for trading agents — exactly the kind of capability the MCP gateway (Tier 1) is designed to expose to LiteLLM consumers

**Stack integration points:**

Depends on (services OpenBB would consume):
- **Infisical** — third-party-data-provider API keys
- **Redis** — response caching

Consumed by (services that would call OpenBB):
- **MCP gateway** — exposes OpenBB endpoints as MCP tools for all LLM consumers
- **Backend (FastAPI)** — direct integration for financial features
- **Hermes** — financial-data tool for trading-research agents
- **n8n** — data-ingest workflows
- **NautilusTrader** — fundamentals enrichment alongside live market feeds
- **JupyterHub** — research notebooks

**TimescaleDB extension — time-series on existing Postgres**
- Postgres extension (Apache-2.0 + Timescale License) adding hypertables, continuous aggregates, retention policies, and time-bucketed query operators
- Zero new container — enabled on the **existing Supabase Postgres** instance via `CREATE EXTENSION timescaledb`
- Provides the storage layer for tick / OHLC market data underpinning the trading-AI track; also useful for any time-series workload (Langfuse trace aggregates, IoT, observability rollups)

**Stack integration points:**

Depends on (services TimescaleDB would consume):
- **Supabase (PostgreSQL)** — same Postgres instance, extension-loaded

Consumed by (services that would call TimescaleDB):
- **NautilusTrader** — primary consumer; backtest and live market-data store
- **OpenBB Platform** — historical-data cache target
- **Backend (FastAPI)** — time-series query routes
- **JupyterHub** — research notebooks
- **Langfuse** — optional storage backend for trace event aggregates

**Redpanda — Kafka-compatible streaming broker**
- Single-binary Kafka-compatible streaming platform (BSL-1.1 / RCL); no ZooKeeper / KRaft hassle, dramatically lighter ops footprint than Apache Kafka
- Carries real-time market-data fan-out for the trading-AI track (one exchange WebSocket → multiple strategy consumers without re-subscribing)
- Also a general-purpose event-streaming layer for n8n event-driven workflows, observability event pipelines, and inter-service eventing as the stack scales

**Stack integration points:**

Depends on (services Redpanda would consume):
- None at runtime

Consumed by (services that would call Redpanda):
- **NautilusTrader** — live market-data subscriber
- **Backend (FastAPI)** — event-emitter for cross-service signals
- **n8n** — event-trigger nodes
- **Windmill** — event-driven job triggers
- **OpenBB Platform** — streaming-quote relay

#### Real-time / collaboration

**Real-time audio / video (LiveKit)**
- WebRTC server (Apache-2.0) bridging the existing STT and TTS layers into a real-time voice-agent pipeline rather than batch round-trips
- Video conferencing capabilities and multi-user AI interactions
- Audio / video streaming integration usable as transport for agent dashboards

**Stack integration points:**

Depends on (services LiveKit would consume):
- **STT provider (Parakeet / Speaches / whisper.cpp)** — speech input
- **TTS provider (Chatterbox / Speaches)** — speech output
- **LiteLLM gateway** — reasoning step between STT and TTS turns

Consumed by (services that would call LiveKit):
- **Hermes** — primary consumer; turns the agent into a voice-first surface
- **Backend (FastAPI)** — programmatic real-time session orchestration
- **Open WebUI** — potential voice-chat frontend extension

## Technology comparisons & decisions

### Search engine analysis
- **MeiliSearch vs OpenSearch**: lightweight application search vs full search/analytics/RAG platform
- **OpenSearch vs Elasticsearch**: Apache 2.0 fork vs AGPL/SSPL original; similar capabilities, OpenSearch avoids vendor lock-in
- **SearxNG vs OpenSearch/MeiliSearch**: external web metasearch vs internal content search (complementary, not competing)

### RAG frameworks
- **LightRAG vs OpenRAG**: graph-enhanced retrieval (new capability) vs pre-packaged platform (duplicates existing services)
- **LightRAG vs GraphRAG (Microsoft)**: flexible storage backends + academic benchmarks vs enterprise pipeline focus
- **Docling vs RAG-Anything**: structured document parsing (tables, layout) vs multimodal knowledge entity extraction (complementary)
- **RAGFlow**: alternative worth tracking for deep document understanding and citation grounding (77.6k stars)

### Authentication solutions
- **Keycloak vs Supabase Auth**: enterprise features vs simplicity
- **Self-hosted vs cloud**: control vs convenience

### Vector database options
- **pgvector vs Weaviate vs Qdrant**: SQL integration vs specialized features vs performance
- **Single vs multi-vendor**: simplicity vs flexibility

### AI workflow & agent builders
- **n8n vs LangFlow**: general automation with AI add-ons vs AI-native pipeline builder
- **Complementary use**: n8n for system orchestration, LangFlow for deep AI pipelines

### Container orchestration
- **Docker Compose vs Kubernetes**: development vs production scaling
- **Local vs cloud**: resource efficiency vs unlimited scaling

### LLM observability
- **Langfuse vs Helicone vs Phoenix (Arize)**: Langfuse is the actively-developed choice with a native LiteLLM callback; Helicone entered maintenance mode in early 2026; Phoenix is stronger for offline eval than in-production tracing
- **LLM observability vs infra metrics**: Langfuse covers prompts / traces / evals / cost attribution; Prometheus + Grafana covers container and host metrics. Both belong in the stack — they don't substitute.

### Agent memory
- **LangMem (existing, in-backend) vs Mem0 (external, light) vs Letta / MemGPT (external, stateful)**: LangMem is Open-WebUI-centric and embedded; Mem0 is the multi-agent external default; Letta is the upgrade for agents that need to reason over their own memory hierarchy
- **Complementary, not competing**: a deployment can hold all three for different consumers (backend uses LangMem; Hermes / OpenClaw use Mem0; long-running Hermes personas optionally use Letta)

### Image-generation UIs
- **ComfyUI (existing) vs InvokeAI vs A1111 / Automatic1111**: ComfyUI for graph and batch generation; InvokeAI for canvas and inpainting; A1111 is stagnant and not recommended in 2026
- **Forge** is a reasonable A1111-compatible fork if user preference demands the A1111 UX, but InvokeAI is the better complement to ComfyUI for an AI stack

### MCP gateway
- **`mcpo` vs MetaMCP vs IBM ContextForge**: `mcpo` is the lowest-friction MCP→OpenAPI wrapper (from the Open WebUI org); MetaMCP adds namespace and RBAC aggregation; IBM ContextForge has the broadest transport support
- **Recommended path**: start with `mcpo` (Open WebUI v0.6.31+ already speaks MCP); add MetaMCP when more than 2–3 MCP servers warrant aggregated, namespaced routing

### Personal-knowledge surfaces
- **SilverBullet vs Karakeep vs Paperless-ngx**: SilverBullet for authored markdown notes (files on disk); Karakeep for captured / AI-tagged web content; Paperless-ngx for OCR'd document archive. All three feed the same downstream RAG indexes — pick by capture mode, not as alternatives.
- **Skip for the AI-stack lens**: Logseq, Trilium, AppFlowy, AFFiNE — client-centric or database-backed designs that don't expose files to RAG ingestion as cleanly

### Code-first vs low-code workflows
- **n8n (existing) vs Windmill**: n8n for low-code system orchestration; Windmill for code-native ML / data pipelines (training, evals, scheduled backtests). They complement rather than substitute.
- **Activepieces (MIT) and Trigger.dev** are alternatives to Windmill when AGPL is a deployment concern

### Secrets management
- **`.env` (current) vs Infisical vs HashiCorp Vault vs Vaultwarden**: `.env` is the current baseline; Infisical adds rotation, audit, and per-environment scoping with reasonable operational cost; Vault is overkill for this stack's scale; Vaultwarden is a password vault (wrong layer entirely)

### Embedding inference
- **LiteLLM-routed (current) vs TEI (dedicated)**: LiteLLM is fine for chat completions and ad-hoc embedding calls; TEI is the right layer once embedding throughput becomes dominant (bulk RAG indexing, reranking pipelines). Register TEI as a LiteLLM upstream so consumer code does not change.
- **Reranking** is unique to TEI within the stack — neither Weaviate's bundled multi2vec-clip nor LiteLLM provide a `/rerank` endpoint today

### Image-to-3D models
- **Hunyuan3D-2 (Tencent) vs TRELLIS (Microsoft) vs InstantMesh**: Hunyuan3D-2 leans textured-mesh; TRELLIS produces mesh, Gaussian splatting, and radiance fields from a single image; InstantMesh is faster but lower fidelity. Pick TRELLIS for breadth, Hunyuan3D-2 for textured-mesh quality.
- **NerfStudio is orthogonal**: reconstruction from real captures rather than generation from concept, and runs in parallel rather than competing

### Trading engines
- **NautilusTrader vs Freqtrade vs OctoBot**: NautilusTrader is Python / Rust, multi-asset (crypto, FX, equities, futures), with paper and live execution; Freqtrade is crypto-only with a larger community and simpler scope; OctoBot is similar in scope to Freqtrade
- **For this stack**: NautilusTrader is the default candidate because the multi-asset surface matches the broader AI-app framing; Freqtrade is a fine fit when crypto-only is the explicit goal

### Time-series storage
- **TimescaleDB extension (on existing Postgres) vs standalone QuestDB / InfluxDB**: TimescaleDB is the zero-new-container option (extension on Supabase Postgres) and the recommended default; QuestDB / InfluxDB are worth considering only if write throughput exceeds Postgres + TimescaleDB headroom

### Considered and rejected

The following candidates were evaluated and explicitly *not* recommended at this time. Recording them prevents the same suggestions from cycling back into roadmap discussions.

- **A1111 (Automatic1111) / Forge as a default SD UI** — stagnant or fork-only as of 2026 relative to ComfyUI and InvokeAI. ComfyUI remains the existing default; InvokeAI fills the canvas / inpaint gap.
- **Firecrawl self-hosted** — AGPL-3.0 license contaminates the stack's permissive boilerplate posture. Crawl4AI (Apache-2.0) is the choice for web crawling.
- **Helicone** — entered maintenance mode in early 2026; Langfuse is the actively-developed equivalent with native LiteLLM callback support.
- **Vaultwarden as a secrets manager** — Vaultwarden is a Bitwarden-compatible *password* vault, not a secrets manager. Infisical (or HashiCorp Vault for enterprise scenarios) is the right layer.
- **Logseq / Trilium / AppFlowy / AFFiNE as "Obsidian-as-a-service"** — all client-centric or 5+ container database-backed stacks. For an AI stack the value is files RAG can read; SilverBullet's files-on-disk model is the right fit, with Karakeep and Paperless-ngx covering capture and archive.
- **Phoenix (Arize) as the primary LLM observability backend** — strong for offline eval but Langfuse's LiteLLM-callback integration and richer prompt management make it the better in-production fit.
- **"LiteRAG"** — not a deployable framework. The canonical project the name evokes is **LightRAG (HKUDS)**; see the Tier 2 entry.
- **Sourcegraph self-hosted** — heavyweight code-intelligence platform out of scope for the stack's AI-application focus.
- **A standalone JupyterHub alternative (Marimo-only)** — JupyterHub already ships; Marimo as a *complement* is possible but not on the Tier 1/2/3 path today.
- **Mailpit / Mailhog as a roadmap item** — useful for development but too narrow to warrant Tier 1/2/3 placement; can be added ad-hoc when an email-capture use-case actually lands.

## Implementation strategy

### Development principles

1. **Backward compatibility**: new features should not break existing deployments
2. **Opt-in features**: capabilities are added as optional integrations
3. **Documentation**: every feature ships with reference and quick-start docs
4. **Testing coverage**: automated testing for new capabilities
5. **Community driven**: feature priorities reflect user feedback

### Release schedule

- **Monthly releases**: bug fixes and minor enhancements
- **Quarterly releases**: feature additions
- **Annual releases**: architecture improvements and breaking changes

### Feature development process

1. **Community feedback**: gather requirements from users
2. **Design documents**: technical specifications
3. **Implementation**: development with automated testing
4. **Beta testing**: community testing phase
5. **Documentation**: reference and example docs
6. **Release**: stable release with migration guides

## Community & ecosystem

### Open source contributions

- **Plugin system**: allow community-developed service integrations
- **Template library**: community-contributed templates and workflows
- **Documentation improvements**: community-driven documentation enhancements
- **Testing & validation**: community testing on various platforms

### Integration partnerships

- **AI model providers**: partnerships with model hosting services
- **Cloud providers**: deployment guides and templates
- **Enterprise vendors**: integration with enterprise tools and platforms

## Long-term vision

**Ecosystem platform**
- Grow from a development stack into a multi-tenant deployment platform
- Support for plugin architectures and third-party integrations
- Marketplace for AI workflows and components

**AI-first operations**
- AI-powered stack management and optimization
- Predictive scaling and resource management
- Automated troubleshooting and self-healing capabilities

**Universal integration**
- Standard APIs for AI service integration
- Protocol standardization across AI tools
- Cross-platform and cross-stack compatibility

**Foundation for vertical AI applications**
- **3D and game generation** — host the full pipeline end-to-end: text or image → 3D mesh (Hunyuan3D-2 / TRELLIS) → scene assembly (Blender headless) → real-scene capture (NerfStudio) → runtime (Godot headless), with **LightRAG** indexing the asset graph and **AudioCraft / MusicGen** providing procedural audio
- **Financial / trading AI** — **LiteLLM** + **Hermes** agents over **OpenBB Platform** data, **TimescaleDB**-backed market history on the existing Supabase Postgres, **NautilusTrader** for backtest and execution, **Redpanda** for streaming fan-out, **Langfuse** for trace and eval, **Infisical**-managed exchange credentials, **MCP gateway** exposing the trading toolset to every LLM consumer
- **RAG specializations** — compose domain-tuned RAG pipelines (legal, academic, financial-research, personal-knowledge) from **TEI** + **LightRAG** + **GROBID** / **Apache Tika** / **Docling** / **whisperX**, with the appropriate ingestion surface (**Karakeep** for captures, **SilverBullet** for authored notes, **Paperless-ngx** for OCR'd archives, **Crawl4AI** + **Browserless** for the open web)

---

## Contributing to the roadmap

Community input on roadmap priorities is welcome:

- **Vote on features**: GitHub discussions for feature voting
- **Suggest features**: submit feature requests via GitHub issues
- **Contribute code**: help implement roadmap features
- **Improve documentation**: help document new capabilities

**Join the conversation**: [GitHub Discussions](https://github.com/thekaveh/genai-vanilla/discussions)

---

*This roadmap is a living document and will be updated regularly based on community feedback and technological developments.*
