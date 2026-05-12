# GenAI Vanilla Stack Documentation

Documentation index for the GenAI Vanilla Stack.

## Documentation structure

### Quick Start guides
- [Interactive Setup Wizard](quick-start/interactive-setup-wizard.md) — step-by-step guided configuration
- [Troubleshooting](quick-start/troubleshooting.md) — common issues and solutions

### Service documentation
- [Backend API](services/backend.md) — always-on adaptive FastAPI service
- [Open WebUI](services/open-webui.md) — main chat UI
- [LiteLLM Gateway](services/litellm.md) — always-on OpenAI-compatible front door for every LLM provider
- [Ollama (LiteLLM upstream)](services/ollama.md) — local LLM engine modes (container CPU/GPU, localhost, external, none)
- [ComfyUI](services/comfyui.md) — image generation workflows
- [Weaviate](services/weaviate.md) — vector database
- [n8n](services/n8n.md) — workflow automation
- [SearxNG](services/searxng.md) — privacy metasearch
- [Redis](services/redis.md) — cache/queue infrastructure
- [Local Deep Researcher](services/local-deep-researcher.md) — research/orchestration service
- [Multi2Vec CLIP](services/multi2vec-clip.md) — multimodal vectorization
- [STT Provider (Speech-to-Text)](services/stt-provider.md) — pluggable: Speaches (Faster-Whisper, default), Parakeet-TDT, whisper.cpp
- [TTS Provider (Text-to-Speech)](services/tts-provider.md) — pluggable: Speaches (Kokoro/Piper, default), Chatterbox (voice cloning)
- [Document Processor (Docling)](services/doc-processor.md) — document processing
- [Supabase Ecosystem](services/supabase.md) — database, auth, and storage services
- [Neo4j (Graph Database)](services/neo4j.md) — graph database service
- [Kong (API Gateway)](services/kong.md) — dynamic API gateway configuration
- [JupyterHub (Data Science IDE)](services/jupyterhub.md) — interactive Jupyter Lab environment
- [OpenClaw (AI Agent)](services/openclaw.md) — AI agent for messaging platforms
- [Hermes Agent](services/hermes.md) — programmable AI agent runtime (Nous Research)

### Deployment guides
- [SOURCE Configuration](deployment/source-configuration.md) — SOURCE-based deployment, including GPU variants
- [Ports and Routes](deployment/ports-and-routes.md) — canonical port offsets, direct URLs, and Kong routes
- [Using as a Submodule](deployment/submodule-usage.md) — embedding the stack inside another project

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
python docs/scripts/check-docs-drift.py
```
