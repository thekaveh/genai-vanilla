# TTS Provider Service

High-performance text-to-speech service using XTTS v2 with OpenAI-compatible API via openedai-speech.

## Overview

The TTS Provider service offers production-ready text-to-speech capabilities with:

- **Multiple Backend Support**: GPU (NVIDIA CUDA in Docker) and Native (any platform)
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI TTS API
- **High Quality**: XTTS v2 model with natural voice synthesis
- **Voice Cloning**: Zero-shot voice cloning with 6-second samples
- **16 Languages**: Multilingual support
- **Multiple Voices**: 6 OpenAI-compatible voices (alloy, echo, fable, onyx, nova, shimmer)
- **Dual Models**: tts-1 (Piper/fast) and tts-1-hd (XTTS v2/quality)

## Quick Start

### GPU Users (NVIDIA CUDA)

**Edit `.env`:**
```bash
TTS_PROVIDER_SOURCE=xtts-container-gpu
```

**Start the stack:**
```bash
./start.sh
```

### Any Platform (Localhost)

**Step 1: Clone openedai-speech**
```bash
cd tts-provider/localhost
git clone https://github.com/matatonic/openedai-speech.git
```

**Step 2: Install dependencies**
```bash
uv sync
```

**Step 3: Start TTS server (separate terminal)**
```bash
uv run server.py
```

**Step 4: Start the stack**
```bash
./start.sh --tts-provider-source xtts-localhost
```

### Disable TTS

```bash
TTS_PROVIDER_SOURCE=disabled
```

## Test the API

```bash
curl -X POST http://localhost:63023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "tts-1-hd", "input": "Hello world!", "voice": "alloy"}' \
  --output speech.mp3
```

**Note:** First API request downloads XTTS v2 models (~1-2GB, takes 5-10 minutes). Subsequent requests are instant.

## Quick Tips

- **Dependencies fixed**: Run `uv sync` to install correct versions (transformers 4.40.2-4.43.0, numpy <2.0)
- **TOS auto-accepted**: Server automatically accepts Coqui license (`COQUI_TOS_AGREED=1`)
- **Model downloads**: Happen on first API request, not server startup
- **Troubleshooting**: See [localhost README](localhost/README.md#troubleshooting) for dependency issues

## Configuration

See [docs/services/tts-provider.md](../docs/services/tts-provider.md) for comprehensive documentation.

## References

- [openedai-speech GitHub](https://github.com/matatonic/openedai-speech)
- [Coqui TTS GitHub](https://github.com/coqui-ai/TTS)
- [XTTS v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
- [OpenAI Audio API](https://platform.openai.com/docs/guides/text-to-speech)
