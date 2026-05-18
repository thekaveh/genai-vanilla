## Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/hermes/service.yml`. Re-run `python -m bootstrapper.docs.regen hermes` after manifest changes.

### Current — Upstream (this service depends on)

| Service | Type | Mechanism | Failure mode |
|---|---|---|---|
| litellm | required | `http://litellm:<port>` | Hermes preflight fails (LLM provider required); container exits. |
| chatterbox | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| comfyui | adaptive | `COMFYUI_INTERNAL_URL=${COMFYUI_ENDPOINT}` | Capability block omitted from config.yaml; Hermes runs without it. |
| comfyui | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| parakeet | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| searxng | adaptive | `SEARXNG_INTERNAL_URL=http://searxng:8080` | Capability block omitted from config.yaml; Hermes runs without it. |
| searxng | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| speaches | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| llm_provider | adaptive | `LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}` | Hermes preflight fails (LLM provider required); container exits. |
| stt_provider | adaptive | `STT_INTERNAL_URL=${STT_ENDPOINT}` | Capability block omitted from config.yaml; Hermes runs without it. |
| tts_provider | adaptive | `TTS_INTERNAL_URL=${TTS_ENDPOINT}` | Capability block omitted from config.yaml; Hermes runs without it. |

### Current — Downstream (services that depend on this)

| Service | Type | Mechanism |
|---|---|---|
| kong | required | kong declares hermes in depends_on.required |
| litellm | optional | litellm registers hermes as a consumer (doc_extras.diagram.extra_consumers escape hatch) |
| open-webui | required | open-webui declares hermes in depends_on.required |

### Architecture diagram

![hermes architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
