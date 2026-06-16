# Atlas Documentation

Documentation index for the Atlas.

## 1. Documentation structure

### 1.1 Quick Start guides
- [Interactive Setup Wizard](quick-start/interactive-setup-wizard.md) — step-by-step guided configuration
- [Troubleshooting](quick-start/troubleshooting.md) — common issues and solutions across the full stack
- [Startup Troubleshooting](TROUBLESHOOTING.md) — quick fixes for first-launch errors (sudo recovery, Airflow ResolutionImpossible, n8n restart-loops); linked from `start.sh`'s own error output

### 1.2 Service documentation
- [Backend API](../services/backend/README.md) — always-on adaptive FastAPI service
- [Open WebUI](../services/open-webui/README.md) — main chat UI
- [LiteLLM Gateway](../services/litellm/README.md) — always-on OpenAI-compatible front door for every LLM provider
- [Ollama (LiteLLM upstream)](../services/ollama/README.md) — local LLM engine modes (container CPU/GPU, localhost, none)
- [ComfyUI](../services/comfyui/README.md) — image generation workflows
- [Weaviate](../services/weaviate/README.md) — vector database
- [MinIO](../services/minio/README.md) — S3-compatible artifact-tier object storage
- [n8n](../services/n8n/README.md) — workflow automation
- [SearxNG](../services/searxng/README.md) — privacy metasearch
- [Redis](../services/redis/README.md) — cache/queue infrastructure
- [Local Deep Researcher](../services/local-deep-researcher/README.md) — research/orchestration service
- [Multi2Vec CLIP](../services/multi2vec-clip/README.md) — multimodal vectorization
- [STT Provider (Speech-to-Text)](../services/stt-provider/README.md) — pluggable: Speaches (Faster-Whisper, default), Parakeet-TDT, whisper.cpp
- [TTS Provider (Text-to-Speech)](../services/tts-provider/README.md) — pluggable: Speaches (Kokoro/Piper, default), Chatterbox (voice cloning)
- [Document Processor (Docling)](../services/doc-processor/README.md) — document processing
- [Supabase Ecosystem](../services/supabase/README.md) — database, auth, and storage services
- [Neo4j (Graph Database)](../services/neo4j/README.md) — graph database service
- [Kong (API Gateway)](../services/kong/README.md) — dynamic API gateway configuration
- [JupyterHub (Data Science IDE)](../services/jupyterhub/README.md) — interactive Jupyter Lab environment
- [LightRAG](../services/lightrag/README.md) — graph-augmented RAG server with WebUI + multimodal ingestion
- [OpenClaw (AI Agent)](../services/openclaw/README.md) — AI agent for messaging platforms
- [Hermes Agent](../services/hermes/README.md) — programmable AI agent runtime (Nous Research)
- [Ray](../services/ray/README.md) — distributed compute substrate (head + workers, opt-in via `RAY_SOURCE`)
- [Prometheus](../services/prometheus/README.md) — observability scraper + TSDB with bundled node-exporter and cAdvisor (opt-in via `PROMETHEUS_SOURCE`)
- [Grafana](../services/grafana/README.md) — observability dashboards + unified alerting on top of Prometheus (opt-in via `GRAFANA_SOURCE`)
- [Apache Spark](../services/spark/README.md) — standalone Spark cluster (5-container family: master + workers + history + Spark Connect gRPC sidecar + minio/mc bucket init) for batch / SQL / DataFrame workloads (opt-in via `SPARK_SOURCE`)
- [Apache Zeppelin](../services/zeppelin/README.md) — Spark-first notebook UI; Spark interpreter pre-configured, JDBC interpreter requires a one-time UI setup (opt-in via `ZEPPELIN_SOURCE`; gated on Spark)
- [Apache Airflow](../services/airflow/README.md) — code-defined DAG orchestrator (webserver + scheduler + dag-processor + init) with LiteLLM-wired LLM operators (opt-in via `AIRFLOW_SOURCE`)
- [TEI Reranker](../services/tei-reranker/README.md) — Cross-encoder reranker (default `mxbai-rerank-base-v1`) for RAG quality lift

### 1.3 Deployment guides
- [SOURCE Configuration](deployment/source-configuration.md) — SOURCE-based deployment, including GPU variants
- [Ports and Routes](deployment/ports-and-routes.md) — canonical port offsets, direct URLs, and Kong routes
- [Using as a Submodule](deployment/submodule-usage.md) — embedding the stack inside another project
- [Expected Startup Warnings](deployment/expected-startup-warnings.md) — known-benign log lines on `./start.sh`

### 1.4 Contributors
- [Adding a service runbook](CONTRIBUTING-services.md) — six-decision walkthrough + the regen + lint chain
- [Security policy](../SECURITY.md) — threat tiers, supported versions, responsible-disclosure address

### 1.5 Architecture diagrams
- [Diagrams README](diagrams/README.md) — top-level diagram update workflow + the per-service auto-generation chain
- The top-level diagram itself lives at [diagrams/architecture.svg](diagrams/architecture.svg) (embedded in the project README) and [diagrams/architecture.html](diagrams/architecture.html) (standalone view)

### 1.6 Cross-service research (Phase B corpus)
- [Research corpus guide](research/README.md) — layout, authoring rules, and the schema the validator enforces
- [Integration matrix](research/integration-matrix.md) — auto-generated index linking every service to its candidate integrations
- [Per-service rows](research/rows/) — missing-pair integrations, candidate new services, per-service feature gaps
- [Candidate one-pagers](research/candidates/) — design notes per candidate service

### 1.7 Feature-track plans and specs
- [superpowers/plans](superpowers/plans/) + [superpowers/specs](superpowers/specs/) — point-in-time implementation plans and specs for the larger 2026-05/06 feature tracks (consult when archaeology on a past track is needed; CHANGELOG entries link the relevant ones)

## 2. Related documentation

- [Main README](../README.md) — project overview and quick start
- [ROADMAP](ROADMAP.md) — future development plans
- [CHANGELOG](CHANGELOG.md) — release history and completed features

## 3. Getting help

If you can't find what you're looking for:

1. Check the [Troubleshooting Guide](quick-start/troubleshooting.md)
2. Search through the service-specific documentation
3. Open an issue on GitHub if you need additional help

## 4. Contributing to documentation

- Found a typo or error? Open a PR.
- Missing information? Open an issue.

## 5. Maintainer checks

Run local documentation drift checks before committing docs changes:

```bash
python scripts/check-docs-drift.py
```
