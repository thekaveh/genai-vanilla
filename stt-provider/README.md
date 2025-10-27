# STT Provider - Speech-to-Text Service

OpenAI-compatible Speech-to-Text API using NVIDIA Parakeet-TDT models.

## ⚠️ Important: MLX Docker Limitation

**MLX cannot run in Docker containers.** MLX requires native macOS with Metal GPU support.

- **Mac users**: Use `STT_PROVIDER_SOURCE=parakeet-localhost` and run MLX natively
- **GPU users**: Use `STT_PROVIDER_SOURCE=parakeet-container-gpu` for Docker NVIDIA

## Overview

This service provides high-performance speech-to-text transcription with support for:

- **Localhost backend** - For Mac MLX (Metal) or Linux (CPU/custom GPU), run natively on host
- **GPU Docker backend** - For NVIDIA GPUs with CUDA acceleration in containers
- **25+ languages** - Multilingual support (Parakeet-TDT v3)
- **Word-level timestamps** - Precise timestamp information
- **OpenAI-compatible API** - Drop-in replacement for Whisper API

## Architecture

```
stt-provider/
├── mlx/              # Apple Silicon MLX implementation
│   ├── api_server.py # OpenAI-compatible FastAPI server
│   └── requirements.txt # Dependencies (includes parakeet-mlx)
├── gpu/              # NVIDIA GPU implementation (Docker)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── transcribe.py
└── shared/           # Common utilities
    ├── api_server.py # FastAPI REST server template
    └── utils.py

Note: The MLX server uses the official parakeet-mlx library as its backend.
```

## Performance

### MLX (Apple Silicon)
- **Speed**: 300x real-time on M2 Ultra
- **Memory**: ~2GB RAM
- **Example**: 3-hour podcast → 1 minute transcription

### GPU (NVIDIA)
- **Speed**: 3380x real-time on A100
- **Memory**: ~2GB VRAM (minimum)
- **Example**: 1 hour audio → 1 second transcription

## Quick Start (Mac Users)

**Step 1: Install dependencies**
```bash
pip install -r stt-provider/mlx/requirements.txt
```

**Step 2: Start STT server (in separate terminal)**
```bash
cd stt-provider
python -m uvicorn mlx.api_server:app --host 0.0.0.0 --port 63022
```

**Note:** Port 63022 is the default (base_port + 22). It auto-adjusts if you use `--base-port` flag.

**Step 3: Start the stack with STT enabled (in another terminal)**
```bash
./start.sh --stt-provider-source parakeet-localhost
```

**Note:**
- STT is **disabled by default** - you must explicitly enable it with `--stt-provider-source parakeet-localhost`
- First run downloads the model (~1.2GB) and takes 5-10 minutes
- Subsequent runs are instant
- Alternative: Edit `.env` and set `STT_PROVIDER_SOURCE=parakeet-localhost` for permanent enable

---

## Backend Options

### 1. Localhost Backend (Mac or Linux Native)

**For Mac users with MLX:**
```bash
# Install dependencies
pip install -r mlx/requirements.txt

# Run STT server on host
cd stt-provider
python -m uvicorn mlx.api_server:app --host 0.0.0.0 --port 63022

# Configure .env (already set by default)
STT_PROVIDER_SOURCE=parakeet-localhost
STT_PROVIDER_PORT=63022  # Auto-updates with --base-port flag
```

### 2. GPU Docker Backend (NVIDIA)

**For GPU users:**
```bash
# Configure .env
STT_PROVIDER_SOURCE=parakeet-container-gpu

# Start with docker
./start.sh
```

### 3. Disabled

```bash
STT_PROVIDER_SOURCE=disabled
```

## API Endpoints

### OpenAI-Compatible Endpoint

```bash
POST /v1/audio/transcriptions

# Example
curl -X POST http://localhost:63022/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=parakeet-tdt-0.6b-v3" \
  -F "language=en" \
  -F "response_format=json"
```

### Advanced Endpoint

```bash
POST /v1/audio/transcriptions/advanced

# Example with timestamps
curl -X POST http://localhost:63022/v1/audio/transcriptions/advanced \
  -F "file=@audio.mp3" \
  -F "return_timestamps=true" \
  -F "word_timestamps=true"
```

### Health Check

```bash
GET /health

# Example
curl http://localhost:63022/health
```

## Supported Audio Formats

- WAV (.wav)
- FLAC (.flac)
- MP3 (.mp3)
- M4A (.m4a)
- OGG (.ogg)
- OPUS (.opus)

## Supported Languages (v3)

English, Spanish, French, German, Italian, Portuguese, Polish, Dutch, Russian, Ukrainian, Czech, Slovak, Croatian, Slovenian, Estonian, Latvian, Lithuanian, Romanian, Bulgarian, Greek, Hungarian, Finnish, Swedish, Danish, Norwegian

## Model Selection

```bash
# v3 (multilingual, 25 languages) - Default
PARAKEET_MODEL=nvidia/parakeet-tdt-0.6b-v3

# v2 (English-only, slightly faster)
PARAKEET_MODEL=nvidia/parakeet-tdt-0.6b-v2
```

## Development

### Building GPU Container

```bash
docker build -f stt-provider/gpu/Dockerfile -t parakeet-gpu .
```

### Running Locally

**Mac (MLX):**
```bash
# Install dependencies
pip install -r mlx/requirements.txt

# Set model (optional, defaults to v3)
export PARAKEET_MODEL=mlx-community/parakeet-tdt-0.6b-v3

# Run server
cd stt-provider
python -m uvicorn mlx.api_server:app --host 0.0.0.0 --port 63022
```

**GPU (NVIDIA - requires Docker):**
```bash
# Use the stack's Docker setup
./start.sh --stt-provider-source parakeet-container-gpu
```

## Integration

### Open WebUI

Configure voice input to use STT endpoint:

```
STT_ENDPOINT=http://parakeet:8000
```

### n8n Workflows

Use HTTP Request node:

```
POST http://parakeet:8000/v1/audio/transcriptions
```

### JupyterHub Notebooks

```python
import requests

with open("audio.mp3", "rb") as f:
    response = requests.post(
        "http://parakeet:8000/v1/audio/transcriptions",
        files={"file": f},
        data={"response_format": "json"}
    )

print(response.json()["text"])
```

## Troubleshooting

### Model Download Issues

Models are downloaded automatically on first run. If download fails:

1. Check Hugging Face Hub access
2. Set `HUGGING_FACE_HUB_TOKEN` if needed
3. Check disk space (~3GB required)

### Performance Issues

- **MLX**: Ensure Metal acceleration is enabled
- **GPU**: Verify CUDA drivers and GPU visibility
- **Memory**: Reduce audio length or increase available RAM/VRAM

### Audio Format Issues

Convert unsupported formats:

```bash
ffmpeg -i input.m4a -ar 16000 output.wav
```

## References

- [NVIDIA Parakeet-TDT v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [NVIDIA Parakeet-TDT v2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
