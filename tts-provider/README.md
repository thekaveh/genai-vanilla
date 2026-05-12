# TTS Provider Service

Pluggable text-to-speech layer. All backends expose an OpenAI-compatible
`/v1/audio/speech` endpoint so Open WebUI, n8n, and the backend API can use
them interchangeably.

## Available backends

| `TTS_PROVIDER_SOURCE` | Engine | License | Runs on |
|---|---|---|---|
| `speaches-container-cpu` | Speaches (Kokoro + Piper) | MIT | Linux + macOS Docker, CPU |
| `speaches-container-gpu` | Speaches (CUDA build) | MIT | NVIDIA |
| `chatterbox-container-gpu` | Resemble AI Chatterbox | MIT | NVIDIA (≥8 GB) |
| `chatterbox-localhost` | Chatterbox natively | MIT | macOS MPS / Linux (any) |
| `disabled` | none | — | — |

The default for fresh installs is **`speaches-container-cpu`** — works on
every platform with no localhost setup, downloads a small Kokoro model
(~90 MB) on first request.

For voice cloning (5-second zero-shot), pick a Chatterbox variant. For pure
container-only setups on NVIDIA, `chatterbox-container-gpu`. For Apple
Silicon where MPS gives ~10× speedup over the Docker CPU path, install
Chatterbox natively and use `chatterbox-localhost` — see
[localhost/README.md](localhost/README.md).

## Quick start

Speaches (default — already enabled in `.env.example`):

```bash
./start.sh
# wait for the speaches container to come healthy (~60s on first run)
curl http://localhost:63026/v1/audio/speech \
  -X POST -H "Content-Type: application/json" \
  -d '{"model":"hexgrad/Kokoro-82M","input":"hello","voice":"af_heart"}' \
  --output speech.wav
```

Chatterbox (voice cloning, GPU required):

```bash
./start.sh --tts-provider-source chatterbox-container-gpu
```

Chatterbox on host (macOS native):

```bash
# Terminal 1
pip install chatterbox-tts-api
chatterbox-tts-api --host 0.0.0.0 --port 63023

# Terminal 2
./start.sh --tts-provider-source chatterbox-localhost
```

Disable:

```bash
./start.sh --tts-provider-source disabled
```

## How Open WebUI is wired

The bootstrapper sets these env vars on the open-web-ui container based on
the chosen source:

- `AUDIO_TTS_ENGINE=openai`
- `AUDIO_TTS_OPENAI_API_BASE_URL=${TTS_ENDPOINT}/v1`
- `AUDIO_TTS_MODEL=hexgrad/Kokoro-82M` (Speaches) or `ResembleAI/chatterbox` (Chatterbox)
- `AUDIO_TTS_VOICE=af_heart` or `default`

You can override the model / voice in the Open WebUI admin panel after
startup — Audio settings.

## Full configuration reference

See [docs/services/tts-provider.md](../docs/services/tts-provider.md).

## References

- [Speaches](https://github.com/speaches-ai/speaches) — bundled Kokoro + Piper + Faster-Whisper
- [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
- [Chatterbox upstream](https://github.com/resemble-ai/chatterbox)
- [chatterbox-tts-api server](https://github.com/travisvn/chatterbox-tts-api)
- [OpenAI Audio API spec](https://platform.openai.com/docs/guides/text-to-speech)
