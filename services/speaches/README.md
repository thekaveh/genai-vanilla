# services/speaches — Unified TTS + STT (OpenAI-compatible)

One container, **two roles** — exposes both
`/v1/audio/transcriptions` (STT, Faster-Whisper) and
`/v1/audio/speech` (TTS, Kokoro + Piper voices) on a single port.

## Containers

| Container | Role | Image var |
|---|---|---|
| `speaches` | Faster-Whisper STT + Kokoro/Piper TTS, OpenAI-compatible | `SPEACHES_IMAGE` |

> The CUDA build tag lives in the env var `SPEACHES_GPU_IMAGE` for now;
> it is documented but **not yet wired to a separate `images:` entry**.
> The CPU image is what the compose fragment pulls today; GPU mode is
> selected by the `speaches-container-gpu` source variant in the
> bootstrapper, not by image-var swap. Tracking promotion to a real
> per-profile image binding under the speaches GPU work item.

This manifest has **no `sources:` block**. Activation is multi-input —
driven by `STT_PROVIDER_SOURCE` **or** `TTS_PROVIDER_SOURCE`:

- `STT_PROVIDER_SOURCE=speaches-container-cpu` (default) — speaches runs.
- `STT_PROVIDER_SOURCE=speaches-container-gpu` — speaches runs in GPU mode.
- `TTS_PROVIDER_SOURCE=speaches-container-cpu` — same container handles TTS.
- `TTS_PROVIDER_SOURCE=speaches-container-gpu` — GPU mode.

When both STT and TTS pick a `speaches-*` option, the bootstrapper
**dedupes to one running container** (one endpoint serves both roles).
The logic lives in
`bootstrapper/services/service_config.py::_generate_stt_provider_config`
and `_generate_tts_provider_config`, which together write
`SPEACHES_SCALE`.

## See also

- [`docs/services/tts-provider.md`](../../docs/services/tts-provider.md) — full TTS matrix.
- [`docs/services/stt-provider.md`](../../docs/services/stt-provider.md) — full STT matrix.
- [`services/parakeet/`](../parakeet/) — owns `STT_PROVIDER_SOURCE`.
- [`services/tts-provider/`](../tts-provider/) — virtual service that owns `TTS_PROVIDER_SOURCE`.
