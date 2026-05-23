## Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/hermes/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen hermes` after manifest changes.

### Current — Upstream (this service calls)

| Service | Category |
|---|---|
| litellm ↔ | llm |
| comfyui | media |
| searxng | media |
| stt-provider | media |
| tts-provider | media |

### Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |
| litellm ↔ | llm |
| n8n | agents |
| openclaw | agents |
| backend | apps |
| jupyterhub | apps |
| open-webui | apps |

### Architecture diagram

![hermes architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
