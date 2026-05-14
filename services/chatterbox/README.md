# services/chatterbox — Resemble AI voice-cloning TTS (GPU)

MIT-licensed, 5-second zero-shot voice cloning. One of the engines
selectable through `TTS_PROVIDER_SOURCE` (owned by
[`services/tts-provider/`](../tts-provider/)).

## Containers

| Container | Role | Image var |
|---|---|---|
| `chatterbox` | GPU TTS engine, OpenAI-compatible `/v1/audio/speech` + voice-clone routes | `CHATTERBOX_IMAGE` |

This manifest has **no `sources:` block** — its activation is driven
externally by `TTS_PROVIDER_SOURCE`. The bootstrapper's
`_generate_tts_provider_config` writes `CHATTERBOX_SCALE` based on the
selected TTS source (1 when `chatterbox-container-gpu`, else 0).

The `chatterbox-localhost` option of `TTS_PROVIDER_SOURCE` runs Chatterbox
**outside** the stack (the user's own install) — no container is started
in that case.

## See also

- [`docs/services/tts-provider.md`](../../docs/services/tts-provider.md) — full TTS-engine matrix and configuration.
- [`services/tts-provider/`](../tts-provider/) — the virtual service that owns `TTS_PROVIDER_SOURCE`.
