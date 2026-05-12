# Chatterbox TTS — localhost mode

Run [Resemble AI Chatterbox](https://github.com/resemble-ai/chatterbox) natively
on your host machine and have the stack reach it via `host.docker.internal`.

This is the recommended TTS path when you want **zero-shot voice cloning**
(5-second reference audio) without using a GPU container — Chatterbox runs on
macOS MPS (Apple Silicon) and Linux CPU/MPS/CUDA.

## Why localhost instead of container

- **macOS users**: Chatterbox uses MPS for acceleration; that doesn't work
  through Docker Desktop. Running natively is ~10× faster.
- **Limited GPU**: the container variant (`chatterbox-container-gpu`) needs
  ≥8 GB VRAM. The localhost variant can fall back to CPU if MPS / CUDA isn't
  available (slow but functional).
- **Voice management**: keeping voice samples on the host makes them easier
  to manage than mounting volumes into the container.

If you just want a TTS service that works out of the box on any platform with
no setup, use `TTS_PROVIDER_SOURCE=speaches-container-cpu` instead — Speaches
gives you Kokoro voices without any localhost setup, just zero voice cloning.

## Install

```bash
# Pick whichever Python tool you prefer; the examples use uv. Python 3.10+ required.
pip install chatterbox-tts chatterbox-tts-api
```

That installs:
- `chatterbox-tts` — the model + inference library (PyTorch under the hood)
- `chatterbox-tts-api` — an OpenAI-compatible HTTP server wrapper

First start downloads the Chatterbox model from HuggingFace (~2 GB). Cached
under `~/.cache/huggingface/` afterwards.

## Run the server

```bash
# Default port matches CHATTERBOX_LOCALHOST_URL in .env (63023).
# Change it with --port if 63023 is taken; remember to update .env to match.
chatterbox-tts-api --host 0.0.0.0 --port 63023
```

Then in another terminal, point the stack at it:

```bash
./start.sh --tts-provider-source chatterbox-localhost
```

Optional: change the host URL in `.env`:

```bash
CHATTERBOX_LOCALHOST_URL=http://host.docker.internal:63023
```

## Verify

```bash
curl -X POST http://localhost:63023/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"model":"ResembleAI/chatterbox","input":"hello world","voice":"default"}' \
  --output /tmp/test.wav
file /tmp/test.wav   # expect: RIFF (little-endian) data, WAVE audio
```

## Voice cloning

Drop a 5-second reference WAV anywhere on disk, then pass it via the API:

```bash
curl -X POST http://localhost:63023/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "ResembleAI/chatterbox",
    "input": "Synthesize me in this voice please.",
    "voice": "default",
    "reference_audio": "/absolute/path/to/sample.wav"
  }' \
  --output cloned.wav
```

Chatterbox is licensed MIT, so the resulting audio is yours to use commercially.

## Performance reference

| Hardware | Approx. realtime factor (lower is faster) |
|---|---|
| M2 Pro, MPS | 0.4–0.6× (faster than realtime) |
| M2 Pro, CPU only | 4–6× |
| NVIDIA RTX 4090 | 0.1× |

## Troubleshooting

**MPS not detected on macOS** — `chatterbox-tts` will print `Using CPU`.
Reinstall PyTorch with MPS support: `pip install --upgrade --force-reinstall torch torchaudio`.

**Port already in use** — pick a different port:

```bash
chatterbox-tts-api --host 0.0.0.0 --port 63041
# then in .env:
CHATTERBOX_LOCALHOST_URL=http://host.docker.internal:63041
```

**First request times out** — the model downloads on first call (~2 GB).
Pre-warm by running the curl test above with `--max-time 600`.

## References

- [Chatterbox upstream](https://github.com/resemble-ai/chatterbox)
- [chatterbox-tts-api server](https://github.com/travisvn/chatterbox-tts-api)
- [Chatterbox model card](https://huggingface.co/ResembleAI/chatterbox)

## Historical note

This directory previously hosted a server.py wrapper for openedai-speech /
XTTS v2. That stack was retired in this release because the upstream image
(`ghcr.io/matatonic/openedai-speech`) was archived on 2026-01-04 and XTTS-v2
weights are CPML / non-commercial. `git log -- tts-provider/localhost/` has
the old setup if you need to compare configurations.
