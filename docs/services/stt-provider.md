# STT Provider Service

Speech-to-Text service using NVIDIA Parakeet-TDT models with OpenAI-compatible API.

## ⚠️ Important: MLX and Docker Compatibility

**MLX (Apple Silicon) requires native macOS execution and cannot run in Docker containers.**

### Why?
- MLX uses the Metal GPU framework which is macOS-only
- Docker containers on Mac run Linux, not macOS
- Linux containers cannot access Metal or install MLX Python wheels

### Solution for Mac Users
Mac users **must** use `STT_PROVIDER_SOURCE=parakeet-localhost` and run the STT server natively on macOS to leverage MLX/Metal acceleration.

---

## Overview

The STT Provider service offers high-performance speech-to-text transcription with:

- **Multiple Backend Support**: Localhost (Mac MLX or Linux CPU) and Docker (NVIDIA GPU)
- **SOTA Accuracy**: 6.05% WER on multilingual benchmarks (#1 on HuggingFace)
- **Ultra-Fast**: 300x real-time on Mac M2 Ultra, 3380x on NVIDIA A100
- **25+ Languages**: Multilingual support with automatic language detection
- **OpenAI-Compatible**: Drop-in replacement for Whisper API

## Quick Start

### Mac Users (Apple Silicon with MLX)

**Step 1: Install dependencies**
```bash
pip install -r stt-provider/mlx/requirements.txt
```

**Step 2: Start STT server on host (in separate terminal)**
```bash
cd stt-provider
python -m uvicorn mlx.api_server:app --host 0.0.0.0 --port 10300
```

**Step 3: Start the stack with STT enabled**
```bash
./start.sh --stt-provider-source parakeet-localhost
```

**Note:**
- STT is **disabled by default** - you must explicitly enable it
- First run downloads the model (~1.2GB) and may take 5-10 minutes
- Subsequent runs are instant
- Alternative: Edit `.env` and set `STT_PROVIDER_SOURCE=parakeet-localhost` for permanent enable

### GPU Users (NVIDIA CUDA)

**Edit `.env`:**
```bash
STT_PROVIDER_SOURCE=parakeet-container-gpu
```

**Start the stack:**
```bash
./start.sh
```

### Disable STT

```bash
STT_PROVIDER_SOURCE=disabled
```

## Using STT in Open WebUI

Once the STT service is running, configure Open WebUI to use it:

### Step 1: Access Admin Settings

1. Navigate to Open WebUI at `http://localhost:<OPEN_WEB_UI_PORT>`
2. Go to **Admin Panel** → **Settings** → **Audio**

### Step 2: Configure STT Provider

Configure the following settings:

| Setting | Value |
|---------|-------|
| **STT Engine** | `OpenAI` |
| **API Base URL** | `http://host.docker.internal:10300` |
| **API Key** | Leave blank (not required for local service) |
| **Model** | `parakeet-tdt-0.6b-v3` (optional, uses default if blank) |

**Note:** The engine is set to "OpenAI" because Parakeet implements an OpenAI-compatible API (`/v1/audio/transcriptions`).

### Step 3: Use the Microphone Feature

1. Open any chat window in Open WebUI
2. Click the **microphone icon** in the input area
3. A live audio waveform will appear while recording
4. Click the **tick icon (✓)** to save and transcribe the recording
5. Click the **'x' icon** to cancel
6. The transcribed text will automatically appear in the chat input box

### User Settings (Optional)

Individual users can also configure STT preferences:
- Go to **User Settings** → **Audio**
- Choose **STT Engine**: Default (uses admin settings) or Web API (browser-based)

---

## Test the API

```bash
curl -X POST http://localhost:10300/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "response_format=json"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STT_PROVIDER_SOURCE` | Service source (parakeet-localhost, parakeet-container-gpu, disabled) | `parakeet-localhost` |
| `STT_PROVIDER_PORT` | External port | `10300` |
| `PARAKEET_MODEL` | Model identifier | `nvidia/parakeet-tdt-0.6b-v3` |

### GPU-Specific (NVIDIA Docker)

| Variable | Description | Default |
|----------|-------------|---------|
| `PARAKEET_GPU_DEVICE` | Device type | `cuda` |
| `PARAKEET_GPU_COMPUTE_TYPE` | Precision (float16, float32, int8) | `float16` |
| `PARAKEET_GPU_IMAGE` | Docker base image | `nvcr.io/nvidia/pytorch:25.01-py3` |

### Localhost-Specific

| Variable | Description | Default |
|----------|-------------|---------|
| `PARAKEET_LOCALHOST_URL` | Local service URL | `http://host.docker.internal:10300` |

## API Reference

### POST /v1/audio/transcriptions

OpenAI-compatible transcription endpoint.

**Request:**

```bash
curl -X POST http://localhost:10300/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=parakeet-tdt-0.6b-v3" \
  -F "language=en" \
  -F "response_format=json"
```

**Parameters:**

- `file` (required): Audio file (.wav, .flac, .mp3, .m4a, .ogg, .opus)
- `model`: Model identifier (informational)
- `language`: Language code (optional, auto-detect if not provided)
- `prompt`: Context prompt (not used by Parakeet)
- `response_format`: `json`, `verbose_json`, or `text`
- `temperature`: Sampling temperature (0.0 = greedy decoding)

**Response:**

```json
{
  "text": "Transcribed text appears here."
}
```

### POST /v1/audio/transcriptions/advanced

Advanced endpoint with Parakeet-specific features.

**Request:**

```bash
curl -X POST http://localhost:10300/v1/audio/transcriptions/advanced \
  -F "file=@audio.mp3" \
  -F "return_timestamps=true" \
  -F "word_timestamps=true"
```

**Parameters:**

- `file` (required): Audio file
- `return_timestamps`: Include segment timestamps
- `word_timestamps`: Include word-level timestamps

**Response:**

```json
{
  "text": "Transcribed text appears here.",
  "language": "en",
  "duration": 123.45,
  "has_timestamps": true,
  "timestamps": [...]
}
```

### GET /health

Health check endpoint.

**Request:**

```bash
curl http://localhost:10300/health
```

**Response:**

```json
{
  "status": "healthy",
  "backend": "mlx",
  "device": "mps",
  "model": "nvidia/parakeet-tdt-0.6b-v3"
}
```

## Model Selection

### Parakeet-TDT v3 (Multilingual)

```bash
PARAKEET_MODEL=nvidia/parakeet-tdt-0.6b-v3
```

- **Languages**: 25 European languages
- **WER**: 6.05% average
- **Size**: 600M parameters
- **Recommended**: Yes (default)

### Parakeet-TDT v2 (English-only)

```bash
PARAKEET_MODEL=nvidia/parakeet-tdt-0.6b-v2
```

- **Languages**: English only
- **WER**: 6.05% on English
- **Size**: 600M parameters
- **Recommended**: For English-only use cases

## Supported Languages (v3)

English, Spanish, French, German, Italian, Portuguese, Polish, Dutch, Russian, Ukrainian, Czech, Slovak, Croatian, Slovenian, Estonian, Latvian, Lithuanian, Romanian, Bulgarian, Greek, Hungarian, Finnish, Swedish, Danish, Norwegian

## Performance

### MLX Backend (Apple Silicon)

| Hardware | Speed | Memory | Example |
|----------|-------|--------|---------|
| M1 | 100x RT | ~2GB | 1 hour → 36 seconds |
| M2 Ultra | 300x RT | ~2GB | 3 hours → 1 minute |
| M3 Max | 200x RT | ~2GB | 1 hour → 18 seconds |

### GPU Backend (NVIDIA)

| Hardware | Speed | Memory | Example |
|----------|-------|--------|---------|
| RTX 3060 | 500x RT | ~2GB VRAM | 1 hour → 7 seconds |
| RTX 4090 | 2000x RT | ~2GB VRAM | 1 hour → 2 seconds |
| A100 | 3380x RT | ~2GB VRAM | 1 hour → 1 second |

*RT = Real-time (1x = same duration as audio)*

## Integration

### Open WebUI

Voice input automatically uses STT endpoint if available.

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

### Backend API

The backend service automatically exposes STT endpoints if available.

## Troubleshooting

### Model Download Fails

**Problem**: First startup fails to download model

**Solution**:
1. Check Hugging Face Hub access
2. Set `HUGGING_FACE_HUB_TOKEN` if needed
3. Verify disk space (~3GB required)

### Slow Performance

**Problem**: Transcription slower than expected

**Solution**:
- **MLX**: Verify Metal acceleration is enabled (`PARAKEET_DEVICE=mps`)
- **GPU**: Check CUDA drivers (`nvidia-smi`)
- **Memory**: Ensure sufficient RAM/VRAM available

### Audio Format Errors

**Problem**: Unsupported audio format

**Solution**: Convert to supported format:

```bash
ffmpeg -i input.m4a -ar 16000 -ac 1 output.wav
```

### Container Won't Start

**Problem**: parakeet-mlx or parakeet-gpu fails to start

**Solution**:
1. Check logs: `docker logs genai-parakeet-mlx`
2. Verify SOURCE setting matches your hardware
3. Ensure Docker has sufficient resources allocated

## Architecture

```
stt-provider/
├── mlx/                    # Apple Silicon MLX implementation
│   ├── api_server.py      # OpenAI-compatible FastAPI server
│   └── requirements.txt   # Dependencies (includes parakeet-mlx)
├── gpu/                    # NVIDIA GPU implementation (Docker)
│   ├── Dockerfile         # CUDA optimized
│   ├── requirements.txt
│   └── transcribe.py      # NeMo transcription logic
└── shared/                 # Common utilities
    ├── api_server.py      # FastAPI REST server template
    └── utils.py           # Utilities

Note: The MLX server uses the official parakeet-mlx library as its backend.
```

## Source Modes

### parakeet-container-gpu

Runs Parakeet in Docker container with NVIDIA GPU acceleration.

**Best for**: NVIDIA GPU users (RTX 3060+, A100, etc.)

**Resources**: ~2GB VRAM, CUDA 12.4+

### parakeet-localhost

Connects to Parakeet running on host machine.

**Best for**: Custom installations, development

**Setup**: Run Parakeet locally on port 10300

### disabled

No STT service.

**Best for**: When speech-to-text is not needed

**Impact**: Voice features unavailable in Open WebUI and other services

## Dependencies

### Required

- None (STT is optional for all services)

### Optional (Can Use STT)

- **open-web-ui**: Voice input
- **n8n**: Audio transcription workflows
- **backend**: Proxy STT API endpoints
- **jupyterhub**: Notebooks with STT capabilities

## Future Extensions

This service uses an extensible architecture. Future additions planned:

- **Faster-Whisper**: Alternative model (MLX + GPU)
- **Voxtral**: Mistral's voice model (when Mac support arrives)
- **Canary**: NVIDIA's multilingual translation model

## References

- [NVIDIA Parakeet-TDT v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [NVIDIA Parakeet-TDT v2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)
- [NVIDIA NeMo Documentation](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/intro.html)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [HuggingFace Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)
