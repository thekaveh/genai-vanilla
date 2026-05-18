# TTS Provider

Pluggable text-to-speech layer. All backends speak the OpenAI
`/v1/audio/speech` protocol so Open WebUI, n8n, JupyterHub and the backend
API consume them uniformly.

## Source matrix

| `TTS_PROVIDER_SOURCE` | Engine | Container image | License | Hardware |
|---|---|---|---|---|
| `speaches-container-cpu` (default) | Speaches → Kokoro / Piper | `ghcr.io/speaches-ai/speaches:0.9.0-rc.3-cpu` | MIT | Linux + macOS Docker, CPU |
| `speaches-container-gpu` | Speaches → Kokoro / Piper | `ghcr.io/speaches-ai/speaches:0.9.0-rc.3-cuda` | MIT | NVIDIA |
| `chatterbox-container-gpu` | Resemble AI Chatterbox | `travisvn/chatterbox-tts-api:gpu` | MIT | NVIDIA (≥8 GB) |
| `chatterbox-localhost` | Resemble AI Chatterbox | — (git clone + `uv run main.py`) | MIT | macOS MPS / Linux |
| `disabled` | — | — | — | — |

Speaches dedupes when both `TTS_PROVIDER_SOURCE` and `STT_PROVIDER_SOURCE`
select a speaches variant: one container instance serves both endpoints. If
one source picks CPU and the other GPU, GPU wins and the bootstrapper
prints a one-line notice.

## Engine comparison

| | Speaches (Kokoro) | Speaches (Piper) | Chatterbox |
|---|---|---|---|
| Param count | 82 M | ~20 M | ~500 M |
| Quality | high | good | high + voice cloning |
| First-request load | ~90 MB | ~30 MB | ~2 GB |
| Voice cloning | ❌ | ❌ | ✅ 5-sec zero-shot |
| Languages | 8–9 | 30+ | 23 |
| Realtime factor on CPU | ~1× | ~0.3× | ~4×–6× (slow on CPU) |

Default is Speaches + Kokoro because it has the best quality-per-resource
ratio. Pick Chatterbox when you specifically need voice cloning.

## Quick start

The default already runs:

```bash
./start.sh
# wait ~60s for the speaches container to download Kokoro and become healthy
curl http://localhost:63026/v1/audio/speech \
  -X POST -H "Content-Type: application/json" \
  -d '{"model":"hexgrad/Kokoro-82M","input":"hello world","voice":"af_heart"}' \
  --output /tmp/hello.wav
file /tmp/hello.wav   # expect RIFF / WAVE audio
```

GPU acceleration (NVIDIA):

```bash
./start.sh --tts-provider-source speaches-container-gpu
```

Voice cloning via Chatterbox (NVIDIA):

```bash
./start.sh --tts-provider-source chatterbox-container-gpu
# wait for ~3min as Chatterbox pulls weights on first request
```

Voice cloning via Chatterbox (macOS native, MPS):

```bash
# Terminal 1 — no PyPI package, install from git:
git clone https://github.com/travisvn/chatterbox-tts-api
cd chatterbox-tts-api && uv sync
PORT=63027 uv run main.py

# Terminal 2
./start.sh --tts-provider-source chatterbox-localhost
```

See [the chatterbox-localhost README](../../../services/tts-provider/provider/localhost/README.md)
for the full Chatterbox-on-host walkthrough.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `TTS_PROVIDER_SOURCE` | `speaches-container-cpu` | The single dial that drives everything below. |
| `TTS_PROVIDER_PORT` | `63023` | Wizard display port; bootstrapper rewrites this to match the active container. |
| `TTS_ENDPOINT` | (auto) | Internal URL containers reach the TTS service on. Read by Open WebUI / n8n / backend / JupyterHub. |
| `TTS_PROVIDER_SCALE` | (auto) | 1 when any container variant is active, else 0. |
| `SPEACHES_IMAGE` | `ghcr.io/speaches-ai/speaches:0.9.0-rc.3-cpu` | Override to pin a different release. |
| `SPEACHES_GPU_IMAGE` | `ghcr.io/speaches-ai/speaches:0.9.0-rc.3-cuda` | CUDA build pin. |
| `SPEACHES_TTS_MODEL` | `hexgrad/Kokoro-82M` | HuggingFace repo of the active TTS model. |
| `SPEACHES_PORT` | `63026` | Speaches container external port. |
| `SPEACHES_SCALE` | (auto) | 1 when speaches is active. |
| `CHATTERBOX_IMAGE` | `travisvn/chatterbox-tts-api:gpu` | GPU build tag. No version-locked GPU tag yet — pin to a digest for production. |
| `CHATTERBOX_PORT` | `63027` | Chatterbox container external port. |
| `CHATTERBOX_LOCALHOST_URL` | `http://host.docker.internal:63027` | URL the stack reaches your host's chatterbox-tts-api on (matches CHATTERBOX_PORT for symmetry). |
| `SPEACHES_PRELOAD_MODELS` | (derived from SPEACHES_TTS_MODEL+SPEACHES_STT_MODEL) | Comma-separated list of HF model IDs Speaches downloads at startup. Skips the first-request cold-start. |

## OpenAI-compatible API

Speaches:

```http
POST http://speaches:8000/v1/audio/speech
Content-Type: application/json

{
  "model": "hexgrad/Kokoro-82M",
  "input": "Hello world",
  "voice": "af_heart",
  "response_format": "wav"
}
```

Kokoro voices include `af_heart`, `af_sky`, `am_adam`, `am_michael`,
`bf_emma`, `bm_george` (full list at the Kokoro model card). For Piper
voices use the model id `rhasspy/piper-voices` with `voice` set to a Piper
voice slug.

Chatterbox (registered/built-in voice — JSON):

```http
POST http://chatterbox:4123/v1/audio/speech
Content-Type: application/json

{
  "model": "chatterbox-tts-1",
  "input": "Hello world",
  "voice": "alloy"
}
```

Chatterbox voice cloning uses **multipart upload**, not a JSON
`reference_audio` field. Either pre-register a voice via `POST /voices`
and reference it by name, or inline-upload the reference WAV:

```bash
curl -X POST http://chatterbox:4123/v1/audio/speech \
  -F "input=Hello in this voice." \
  -F "model=chatterbox-tts-1" \
  -F "voice_file=@/host/path/to/sample.wav" \
  --output cloned.wav
```

See [the chatterbox-localhost README](../../../services/tts-provider/provider/localhost/README.md)
for the full voice-library workflow.

## Open WebUI integration

The bootstrapper writes these env vars on the open-web-ui container based
on the source you picked:

- `AUDIO_TTS_ENGINE=openai`
- `AUDIO_TTS_OPENAI_API_BASE_URL=${TTS_ENDPOINT}/v1`
- `AUDIO_TTS_OPENAI_API_KEY=sk-unused`
- `AUDIO_TTS_MODEL` = `hexgrad/Kokoro-82M` (Speaches) or `chatterbox-tts-1` (Chatterbox)
- `AUDIO_TTS_VOICE` = `af_heart` (Speaches) or `alloy` (Chatterbox)

Open WebUI admin → Settings → Audio lets you change voice / model
post-startup; the env vars are just defaults.

## Migration from XTTS

The previous TTS path used `xtts-container-gpu` / `xtts-localhost` against
`ghcr.io/matatonic/openedai-speech`. Both are gone:

- The image was **archived 2026-01-04** upstream.
- XTTS-v2 weights are CPML / non-commercial.

`bootstrapper/services/source_validator.py::_migrate_legacy_tts_stt_sources`
auto-rewrites old `.env` values on the next start:

| Old | New |
|---|---|
| `TTS_PROVIDER_SOURCE=xtts-container-gpu` | `speaches-container-gpu` |
| `TTS_PROVIDER_SOURCE=xtts-localhost` | `chatterbox-localhost` |

The legacy `XTTS_ENDPOINT` env var is also stripped from `.env` — the
unified replacement is `TTS_ENDPOINT`.

## Troubleshooting

**Speaches container stays unhealthy** — check `docker logs
<project>-speaches`. First start downloads models; allow up to 2 minutes.

**Chatterbox container OOMs** — needs ≥8 GB VRAM. Use Speaches instead, or
the localhost variant.

**No audio out of Open WebUI** — verify `AUDIO_TTS_OPENAI_API_BASE_URL` is
set (`docker exec <project>-open-web-ui env | grep AUDIO_TTS`). If empty,
your `TTS_PROVIDER_SOURCE` is `disabled`.

**Wrong voice playing** — the bootstrapper writes a default voice per
engine. Override in Open WebUI admin → Audio, or set
`OPEN_WEB_UI_TTS_VOICE` in `.env` directly.

## References

- [Speaches](https://github.com/speaches-ai/speaches)
- [Kokoro-82M model card](https://huggingface.co/hexgrad/Kokoro-82M)
- [Piper voices](https://github.com/OHF-Voice/piper1-gpl)
- [Chatterbox upstream](https://github.com/resemble-ai/chatterbox)
- [chatterbox-tts-api server](https://github.com/travisvn/chatterbox-tts-api)
- [OpenAI Audio API spec](https://platform.openai.com/docs/guides/text-to-speech)

## Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/tts-provider/service.yml`. Re-run `python -m bootstrapper.docs.regen tts-provider` after manifest changes.

### Current — Upstream (this service depends on)

| Service | Type | Mechanism | Failure mode |
|---|---|---|---|
| litellm | required | `http://litellm:<port>` | _unspecified_ |
| parakeet | required | `http://parakeet:<port>` | _unspecified_ |

### Current — Downstream (services that depend on this)

| Service | Type | Mechanism |
|---|---|---|
| kong | required | kong declares tts-provider in depends_on.required |
| hermes | optional | hermes lists chatterbox as optional dep |
| backend | optional | backend lists chatterbox as optional dep |
| jupyterhub | optional | jupyterhub lists chatterbox as optional dep |
| local-deep-researcher | optional | local-deep-researcher lists chatterbox as optional dep |
| open-webui | optional | open-webui lists chatterbox as optional dep |

### Architecture diagram

![tts-provider architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
