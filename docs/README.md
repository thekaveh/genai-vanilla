# GenAI Vanilla Stack Documentation

Documentation index for the GenAI Vanilla Stack.

## Documentation structure

### Quick Start guides
- [Interactive Setup Wizard](quick-start/interactive-setup-wizard.md) — step-by-step guided configuration
- [Troubleshooting](quick-start/troubleshooting.md) — common issues and solutions

### Service documentation
- [Backend API](../services/backend/README.md) — always-on adaptive FastAPI service
- [Open WebUI](../services/open-webui/README.md) — main chat UI
- [LiteLLM Gateway](../services/litellm/README.md) — always-on OpenAI-compatible front door for every LLM provider
- [Ollama (LiteLLM upstream)](../services/ollama/README.md) — local LLM engine modes (container CPU/GPU, localhost, external, none)
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
- [OpenClaw (AI Agent)](../services/openclaw/README.md) — AI agent for messaging platforms
- [Hermes Agent](../services/hermes/README.md) — programmable AI agent runtime (Nous Research)
- [Ray](../services/ray/README.md) — distributed compute substrate (head + workers, opt-in via `RAY_SOURCE`)

### Deployment guides
- [SOURCE Configuration](deployment/source-configuration.md) — SOURCE-based deployment, including GPU variants
- [Ports and Routes](deployment/ports-and-routes.md) — canonical port offsets, direct URLs, and Kong routes
- [Using as a Submodule](deployment/submodule-usage.md) — embedding the stack inside another project
- [Expected Startup Warnings](deployment/expected-startup-warnings.md) — known-benign log lines on `./start.sh`

## Related documentation

- [Main README](../README.md) — project overview and quick start
- [ROADMAP](ROADMAP.md) — future development plans
- [CHANGELOG](CHANGELOG.md) — release history and completed features

## Getting help

If you can't find what you're looking for:

1. Check the [Troubleshooting Guide](quick-start/troubleshooting.md)
2. Search through the service-specific documentation
3. Open an issue on GitHub if you need additional help

## Contributing to documentation

- Found a typo or error? Open a PR.
- Missing information? Open an issue.

## Maintainer checks

Run local documentation drift checks before committing docs changes:

```bash
python scripts/check-docs-drift.py
```
