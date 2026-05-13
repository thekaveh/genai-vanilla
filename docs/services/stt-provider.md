# STT Provider

Pluggable speech-to-text layer. All backends speak the OpenAI
`/v1/audio/transcriptions` protocol.

## Source matrix

| `STT_PROVIDER_SOURCE` | Engine | Container image | License | Hardware |
|---|---|---|---|---|
| `speaches-container-cpu` (default) | Speaches → Faster-Whisper | `ghcr.io/speaches-ai/speaches:0.9.0-rc.3-cpu` | MIT | Linux + macOS Docker, CPU |
| `speaches-container-gpu` | Speaches → Faster-Whisper | `ghcr.io/speaches-ai/speaches:0.9.0-rc.3-cuda` | MIT | NVIDIA |
| `parakeet-container-gpu` | NVIDIA Parakeet-TDT (NeMo) | (built from `stt-provider/gpu/Dockerfile`) | CC-BY-4.0 | NVIDIA |
| `parakeet-localhost` | Parakeet-MLX (Mac) or native Parakeet | — | NVIDIA Open Model | macOS MLX / Linux |
| `whisper-cpp-localhost` | whisper.cpp | — (`brew install whisper-cpp`) | MIT | macOS Metal+ANE / Linux |
| `disabled` | — | — | — | — |

Speaches shares its container with the TTS provider when both are speaches —
one running instance, two endpoints. If TTS picks one variant and STT picks
the other (e.g. cpu vs gpu), GPU wins and the bootstrapper prints a notice.

## Engine comparison

| | Speaches (Faster-Whisper distil-large-v3) | Parakeet-TDT v3 | whisper.cpp (large-v3) |
|---|---|---|---|
| English WER (LibriSpeech test-clean) | ~3.5% | ~3.0% | ~3.8% |
| Multilingual | 99 langs | 25 EN/EU langs | 99 langs |
| Realtime factor on Apple Silicon | ~0.3× CPU container | ~0.003× MLX | ~0.1× Metal+CoreML |
| Realtime factor on NVIDIA | ~0.05× (RTX 4090) | ~0.0003× (A100) | ~0.05× (CUDA) |
| Word-level timestamps | ✅ | ✅ | ✅ |
| Streaming | partial (chunked) | ✅ (TDT) | ✅ |

Speaches is the default because Faster-Whisper-distil-large-v3 has the best
"works on every platform out of the box" profile. Parakeet remains the
SOTA-quality NVIDIA choice. whisper.cpp is the best macOS-native path.

## Quick start

The default already runs:

```bash
./start.sh
curl -X POST http://localhost:63026/v1/audio/transcriptions \
  -F file=@sample.wav -F model=whisper-1
# expect: {"text":"..."}
```

NVIDIA SOTA (Parakeet):

```bash
./start.sh --stt-provider-source parakeet-container-gpu
```

macOS native — fastest path for Apple Silicon:

```bash
# Option A: whisper.cpp (Metal + Core ML / ANE)
brew install whisper-cpp
bash $(brew --prefix)/share/whisper-cpp/models/download-ggml-model.sh large-v3
whisper-server --host 0.0.0.0 --port 63025 \
  --model "$(brew --prefix)/share/whisper-cpp/models/ggml-large-v3.bin" \
  --inference-path /v1/audio/transcriptions &

./start.sh --stt-provider-source whisper-cpp-localhost

# Option B: Parakeet-MLX (highest quality on EN/EU, MLX-native)
pip install -r stt-provider/mlx/requirements.txt
cd stt-provider && python -m uvicorn mlx.api_server:app --host 0.0.0.0 --port 63022 &
./start.sh --stt-provider-source parakeet-localhost
```

See [stt-provider/whisper-cpp/README.md](../../services/parakeet/provider/whisper-cpp/README.md)
for the whisper.cpp walkthrough and Linux build instructions, or
[stt-provider/mlx/README.md](../../services/parakeet/provider/mlx/README.md) for Parakeet-MLX.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `STT_PROVIDER_SOURCE` | `speaches-container-cpu` | Engine selector. |
| `STT_PROVIDER_PORT` | `63022` | Wizard display port; bootstrapper rewrites to match the active container. |
| `STT_ENDPOINT` | (auto) | Internal URL containers reach STT on. |
| `STT_PROVIDER_SCALE` | (auto) | 1 when any container variant is active. |
| `SPEACHES_STT_MODEL` | `Systran/faster-distil-whisper-large-v3` | HuggingFace repo of the active model. Faster-Whisper accepts any whisper-format checkpoint. |
| `PARAKEET_MODEL` | `nvidia/parakeet-tdt-0.6b-v3` | Or `…-v2` for English-only (slightly faster). |
| `PARAKEET_GPU_IMAGE` | `nvcr.io/nvidia/pytorch:25.01-py3` | Base for the Parakeet GPU Dockerfile. |
| `PARAKEET_LOCALHOST_URL` | `http://host.docker.internal:63022` | Where the container reaches a host-side Parakeet server. |
| `WHISPER_CPP_LOCALHOST_URL` | `http://host.docker.internal:63025` | Where the container reaches a host-side whisper.cpp server. |
| `HUGGING_FACE_HUB_TOKEN` | (empty) | For gated models. |

## OpenAI-compatible API

Every engine implements the same call shape:

```http
POST http://<endpoint>/v1/audio/transcriptions
Content-Type: multipart/form-data

file=<binary audio>
model=whisper-1
language=en               (optional)
response_format=json      (optional: json, text, srt, verbose_json, vtt)
```

The `model` field is largely ignored — every engine returns whatever
checkpoint is loaded. Pass `whisper-1` for maximum compatibility with the
OpenAI client library.

## Open WebUI integration

The bootstrapper writes:

- `AUDIO_STT_ENGINE=openai`
- `AUDIO_STT_OPENAI_API_BASE_URL=${STT_ENDPOINT}/v1`
- `AUDIO_STT_OPENAI_API_KEY=sk-unused`
- `AUDIO_STT_MODEL=whisper-1`

Open WebUI's microphone button starts working as soon as the STT service is
healthy.

## Supported audio formats

WAV (.wav), FLAC (.flac), MP3 (.mp3), M4A (.m4a), OGG (.ogg), OPUS (.opus),
WEBM (.webm). Internally everything resamples to 16 kHz mono before
inference.

## Troubleshooting

**`speaches` container fails its healthcheck** — `docker logs
<project>-speaches`. First request triggers a model download (~466 MB for
distil-large-v3); the healthcheck `start_period` is 120 s but slow networks
may need more time.

**Open WebUI mic button does nothing** — verify the env vars:

```bash
docker exec <project>-open-web-ui env | grep AUDIO_STT
```

If empty, `STT_PROVIDER_SOURCE` is `disabled`.

**Parakeet GPU container OOMs** — needs ~2 GB VRAM minimum. Try the
`int8` compute type (`PARAKEET_GPU_COMPUTE_TYPE=int8`) or switch to
`speaches-container-gpu` (smaller footprint).

**whisper.cpp not detected as localhost** — make sure it's serving the
`/v1/audio/transcriptions` path (use `--inference-path`).

## References

- [Speaches](https://github.com/speaches-ai/speaches)
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)
- [Parakeet-TDT v3 model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [Parakeet-MLX](https://github.com/senstella/parakeet-mlx)
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- [OpenAI Whisper API spec](https://platform.openai.com/docs/guides/speech-to-text)
