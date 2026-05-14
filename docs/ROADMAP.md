# GenAI Vanilla Stack Roadmap

This document outlines future development plans and enhancements for the GenAI Vanilla Stack.

## Current status

The stack now orchestrates 30+ services across AI inference, workflow automation, data science, document processing, speech, and the Supabase ecosystem. Architectural milestones to date:
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

**Enterprise identity management (Keycloak)**
- Advanced user management
- Single sign-on (SSO) capabilities
- Role-based access control
- Integration with external identity providers

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

**Real-time audio/video (LiveKit)**
- Video conferencing capabilities
- Real-time collaboration features
- Audio/video streaming integration
- Multi-user AI interactions

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
