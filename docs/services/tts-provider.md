# TTS Provider Service

High-performance text-to-speech service using XTTS v2 with OpenAI-compatible API.

## Overview

The TTS Provider service offers production-ready text-to-speech generation with:

- **Multiple Backend Support**: GPU (NVIDIA CUDA) and Native (any platform)
- **SOTA Quality**: XTTS v2 model with natural voice synthesis
- **OpenAI-Compatible**: Drop-in replacement for OpenAI TTS API (`/v1/audio/speech`)
- **Voice Cloning**: Zero-shot voice cloning with 6-second samples
- **16 Languages**: Multilingual support
- **6 Voices**: OpenAI-compatible voices (alloy, echo, fable, onyx, nova, shimmer)
- **Dual Models**: tts-1 (Piper/fast) and tts-1-hd (XTTS v2/quality)

## Quick Start

### GPU Users (NVIDIA CUDA)

**Step 1: Configure source**

Edit `.env`:
```bash
TTS_PROVIDER_SOURCE=xtts-container-gpu
```

**Step 2: Start the stack**
```bash
./start.sh
```

**Note:**
- TTS is **disabled by default** - you must explicitly enable it
- First run downloads models (~2GB) and may take 10-15 minutes
- Subsequent runs are instant
- Alternative: `./start.sh --tts-provider-source xtts-container-gpu` for temporary enable

### Any Platform Users (Native Execution)

**Step 1: Clone openedai-speech**
```bash
cd tts-provider/localhost
git clone https://github.com/matatonic/openedai-speech.git
```

**Note:** openedai-speech is not available as a PyPI package, so it must be cloned from GitHub.

**Step 2: Install dependencies**
```bash
uv sync
```

**Step 3: Start TTS server on host (in separate terminal)**
```bash
uv run server.py
```

**Step 4: Start the stack with TTS enabled**
```bash
./start.sh --tts-provider-source xtts-localhost
```

**Note:**
- First run downloads models (~2GB) and may take 10-15 minutes
- Subsequent runs are instant
- Alternative: Edit `.env` and set `TTS_PROVIDER_SOURCE=xtts-localhost` for permanent enable

### Disable TTS

```bash
TTS_PROVIDER_SOURCE=disabled
```

## Using TTS in Open WebUI

Once the TTS service is running, configure Open WebUI to use it:

### Step 1: Access Admin Settings

1. Navigate to Open WebUI at `http://localhost:<OPEN_WEB_UI_PORT>`
2. Go to **Admin Panel** → **Settings** → **Audio**

### Step 2: Configure TTS Provider

Configure the following settings:

| Setting | Value |
|---------|-------|
| **TTS Engine** | `OpenAI` |
| **API Base URL** | `http://host.docker.internal:10400` |
| **API Key** | Leave blank (not required for local service) |
| **Model** | `tts-1-hd` (or `tts-1` for faster/lower quality) |
| **Voice** | Choose from alloy, echo, fable, onyx, nova, shimmer |

**Note:** The engine is set to "OpenAI" because XTTS v2 implements an OpenAI-compatible API (`/v1/audio/speech`).

### Step 3: Use the Text-to-Speech Feature

1. Open any chat window in Open WebUI
2. Select a message or type text
3. Click the **speaker icon** to hear the text spoken
4. The audio will be generated using your configured voice and model

### User Settings (Optional)

Individual users can also configure TTS preferences:
- Go to **User Settings** → **Audio**
- Choose **TTS Engine**: Default (uses admin settings) or Web API (browser-based)

---

## Test the API

```bash
curl -X POST http://localhost:10400/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "Hello, this is a test of the XTTS v2 text-to-speech system.",
    "voice": "alloy",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output speech.mp3
```

Play the audio:
```bash
# macOS
afplay speech.mp3

# Linux
mpg123 speech.mp3

# Windows
start speech.mp3
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TTS_PROVIDER_SOURCE` | Service source (xtts-container-gpu, xtts-localhost, disabled) | `disabled` |
| `TTS_PROVIDER_PORT` | External port | `10400` |
| `XTTS_MODEL` | Default model | `tts-1-hd` |

### GPU-Specific (NVIDIA Docker)

| Variable | Description | Default |
|----------|-------------|---------|
| `XTTS_GPU_IMAGE` | Docker image | `ghcr.io/matatonic/openedai-speech:latest` |
| `NVIDIA_VISIBLE_DEVICES` | GPU devices | `all` |

### Localhost-Specific

| Variable | Description | Default |
|----------|-------------|---------|
| `XTTS_LOCALHOST_URL` | Local service URL | `http://host.docker.internal:10400` |

## API Reference

### POST /v1/audio/speech

OpenAI-compatible text-to-speech endpoint.

**Request:**

```bash
curl -X POST http://localhost:10400/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "The text to synthesize into audio.",
    "voice": "alloy",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output output.mp3
```

**Parameters:**

- `model` (required): Model identifier (`tts-1` or `tts-1-hd`)
- `input` (required): Text to synthesize (max 4096 characters)
- `voice` (required): Voice name (alloy, echo, fable, onyx, nova, shimmer)
- `response_format` (optional): Output format (`mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`) - default: `mp3`
- `speed` (optional): Playback speed (0.25 to 4.0) - default: `1.0`

**Response:**

Binary audio file in the requested format.

### GET /v1/models

List available models.

**Request:**

```bash
curl http://localhost:10400/v1/models
```

**Response:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "tts-1",
      "object": "model",
      "created": 1699000000,
      "owned_by": "openai"
    },
    {
      "id": "tts-1-hd",
      "object": "model",
      "created": 1699000000,
      "owned_by": "openai"
    }
  ]
}
```

## Model Selection

### tts-1-hd (XTTS v2 - Recommended)

```bash
XTTS_MODEL=tts-1-hd
```

- **Backend**: Coqui XTTS v2
- **Quality**: High-quality, natural speech
- **Speed**: ~0.3-0.5x real-time (GPU)
- **Languages**: 16 languages
- **Voice Cloning**: Supported
- **Size**: ~2GB
- **Recommended**: Yes (default)

### tts-1 (Piper TTS - Fast)

```bash
XTTS_MODEL=tts-1
```

- **Backend**: Piper TTS
- **Quality**: Good quality, efficient
- **Speed**: Very fast, CPU-friendly
- **Languages**: English (primary)
- **Voice Cloning**: Not supported
- **Size**: ~200MB
- **Recommended**: For low-resource environments

## Voice Selection

### Available Voices

| Voice | Description | Gender | Characteristics |
|-------|-------------|--------|-----------------|
| **alloy** | Neutral, balanced | Neutral | Versatile, professional |
| **echo** | Clear male voice | Male | Crisp, authoritative |
| **fable** | British accent | Male | Narrative, storytelling |
| **onyx** | Deep male voice | Male | Rich, commanding |
| **nova** | Energetic female | Female | Bright, engaging |
| **shimmer** | Soft female voice | Female | Gentle, warm |

### Usage Example

```python
import requests

voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

for voice in voices:
    response = requests.post(
        "http://localhost:10400/v1/audio/speech",
        json={
            "model": "tts-1-hd",
            "input": f"This is the {voice} voice speaking.",
            "voice": voice
        }
    )

    with open(f"sample_{voice}.mp3", "wb") as f:
        f.write(response.content)
```

## Voice Cloning

XTTS v2 (`tts-1-hd` model) supports zero-shot voice cloning with just 6 seconds of reference audio.

**Note:** Voice cloning requires using openedai-speech advanced features. See the [openedai-speech documentation](https://github.com/matatonic/openedai-speech) for voice cloning setup.

## Supported Languages (XTTS v2)

English (en), Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt), Polish (pl), Turkish (tr), Russian (ru), Dutch (nl), Czech (cs), Arabic (ar), Chinese (zh-cn), Japanese (ja), Hungarian (hu), Korean (ko)

## Performance

### GPU Backend (NVIDIA)

| Hardware | Speed | Memory | Example |
|----------|-------|--------|---------|
| RTX 3060 | 0.5x RT | ~4GB VRAM | 60s audio → 30s generation |
| RTX 4090 | 0.3x RT | ~4GB VRAM | 60s audio → 18s generation |
| A100 | 0.2x RT | ~4GB VRAM | 60s audio → 12s generation |

### Localhost Backend (Any Platform)

| Hardware | Speed | Memory | Example |
|----------|-------|--------|---------|
| CPU (Intel i7) | 2-5x RT | ~8GB RAM | 60s audio → 2-5 minutes |
| Mac M1/M2 | 0.8x RT | ~8GB RAM | 60s audio → 48s generation |
| GPU (CUDA native) | 0.3-0.5x RT | ~4GB VRAM | 60s audio → 18-30s generation |

*RT = Real-time (1x = same duration as audio)*

## Integration

### Open WebUI

Text-to-speech automatically uses TTS endpoint if available (see configuration above).

### n8n Workflows

Use HTTP Request node:

```
POST http://xtts-gpu:8000/v1/audio/speech
Content-Type: application/json

{
  "model": "tts-1-hd",
  "input": "{{ $json.text }}",
  "voice": "alloy"
}
```

### JupyterHub Notebooks

```python
import requests
from IPython.display import Audio

def text_to_speech(text, voice="alloy", model="tts-1-hd"):
    """Generate speech from text"""
    response = requests.post(
        "http://xtts-gpu:8000/v1/audio/speech",
        json={
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3"
        }
    )

    if response.status_code == 200:
        with open("output.mp3", "wb") as f:
            f.write(response.content)
        return Audio("output.mp3")
    else:
        raise Exception(f"TTS failed: {response.text}")

# Use it
text_to_speech("Hello from JupyterHub!", voice="nova")
```

### Backend API

The backend service automatically exposes TTS endpoints if available.

## Troubleshooting

### Dependency Conflicts

**Problem**: `ImportError: cannot import name 'BeamSearchScorer' from 'transformers'`

**Cause**: Newer versions of transformers (4.43+) moved `BeamSearchScorer`, breaking XTTS v2 compatibility.

**Solution**:
```bash
cd tts-provider/localhost
uv sync  # Reinstalls correct version (4.40.2-4.43.0)

# If issue persists:
uv pip install "transformers==4.42.4" --force-reinstall
```

**Problem**: Numpy version conflicts during `uv sync`

**Cause**: TTS library requires numpy <2.0

**Solution**:
```bash
# pyproject.toml already pins numpy to 1.22.0-2.0 range
uv sync  # Handles version resolution automatically
```

### Model Download Fails

**Problem**: First startup fails to download models

**Solution**:
1. Check Hugging Face Hub access
2. Set `HUGGING_FACE_HUB_TOKEN` if needed
3. Verify disk space (~5GB required)

**Note**: The server automatically accepts Coqui TOS by setting `COQUI_TOS_AGREED=1`. Model downloads happen on the **first API request**, not at server startup.

### Slow Generation

**Problem**: Speech generation slower than expected

**Solution**:
- **GPU Docker**: Check CUDA drivers (`nvidia-smi`)
- **GPU Docker**: Verify GPU access in container (`docker exec genai-xtts-gpu nvidia-smi`)
- **Localhost**: Install GPU-enabled PyTorch for acceleration
- **Memory**: Ensure sufficient RAM/VRAM available

### Audio Quality Issues

**Problem**: Generated audio sounds robotic or low quality

**Solution**:
- Use `tts-1-hd` model instead of `tts-1`
- Try different voices (nova and shimmer are often highest quality)
- Adjust speed (0.9-1.1 range for most natural results)
- Ensure input text has proper punctuation

### Port Already in Use

**Problem**: Port 10400 is already occupied

**Solution**:
```bash
# Change port in .env
TTS_PROVIDER_PORT=10401

# Restart the stack
./stop.sh
./start.sh
```

### Container Won't Start

**Problem**: xtts-gpu fails to start

**Solution**:
1. Check logs: `docker logs genai-xtts-gpu`
2. Verify SOURCE setting matches your hardware
3. Ensure Docker has NVIDIA runtime configured
4. Check GPU availability: `nvidia-smi`

## Architecture

### Directory Structure

```
tts-provider/
├── gpu/
│   ├── Dockerfile              # NVIDIA GPU Docker setup
│   └── requirements.txt        # Dependencies (reference only)
├── localhost/
│   ├── server.py              # Native host server wrapper
│   ├── pyproject.toml         # UV dependencies (pinned versions)
│   ├── requirements.txt       # Alternative pip format
│   ├── openedai-speech/       # Cloned from GitHub (git ignored)
│   └── README.md              # Localhost setup guide
└── README.md                  # Quick start guide
```

### TTS Stack Architecture

```
┌─────────────────────────────────────────┐
│  Open WebUI / n8n / JupyterHub          │  (OpenAI API clients)
└───────────────┬─────────────────────────┘
                │ POST /v1/audio/speech
┌───────────────▼─────────────────────────┐
│         openedai-speech                  │  (API compatibility wrapper)
│  - Translates OpenAI API → Coqui TTS    │
│  - Provides /v1/audio/speech endpoint   │
│  - Manages voice mappings               │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│         Coqui XTTS v2                    │  (Actual TTS engine)
│  - Multi-language support (16 langs)    │
│  - Voice cloning (6s samples)           │
│  - GPU/CPU acceleration                 │
└─────────────────────────────────────────┘
```

**Key Points:**
- openedai-speech is NOT a PyPI package - must be cloned from GitHub
- Both GPU and localhost modes use the same openedai-speech wrapper
- GPU mode: Pre-built Docker image (`ghcr.io/matatonic/openedai-speech:latest`)
- Localhost mode: Clone repo + run with Python (`uv run server.py`)
- The wrapper makes Coqui XTTS v2 compatible with OpenAI's TTS API format

## Source Modes

### xtts-container-gpu

Runs XTTS v2 in Docker container with NVIDIA GPU acceleration.

**Best for**: NVIDIA GPU users (RTX 3060+, A100, etc.)

**Resources**: ~4GB VRAM, CUDA 11.8+

**Setup**: Automatic via docker-compose with GPU runtime

### xtts-localhost

Runs XTTS v2 natively on host machine.

**Best for**: Any platform (Mac/Linux/Windows), development, custom setups

**Resources**: 8GB RAM (CPU) or 4GB VRAM (GPU)

**Setup**: Manual - clone openedai-speech, install dependencies, then run `uv run server.py`

### disabled

No TTS service (default).

**Best for**: When text-to-speech is not needed

**Impact**: Voice features unavailable in Open WebUI and other services

## Dependencies

### Required

- None (TTS is optional for all services)

### Optional (Can Use TTS)

- **open-web-ui**: Text-to-speech output for chat messages
- **n8n**: Audio generation workflows
- **backend**: Proxy TTS API endpoints
- **jupyterhub**: Notebooks with TTS capabilities

## Comparison with Other TTS Solutions

| Feature | XTTS v2 (ours) | ElevenLabs API | OpenAI TTS |
|---------|----------------|----------------|------------|
| **Quality** | High | Very High | High |
| **Speed (GPU)** | 0.3-0.5x RT | API latency | API latency |
| **Cost** | Free (self-hosted) | $0.30/1K chars | $15/1M chars |
| **Privacy** | Full (local) | No (cloud) | No (cloud) |
| **Voice Cloning** | Yes (6s samples) | Yes (paid) | No |
| **Languages** | 16 | 29 | 50+ |
| **API** | OpenAI-compatible | Proprietary | OpenAI |
| **Offline** | Yes | No | No |

## Future Extensions

This service uses the openedai-speech platform which supports:

- **Additional Models**: StyleTTS2, Bark, Parler-TTS
- **Advanced Cloning**: Multi-speaker, emotion control
- **Streaming**: Real-time audio streaming

See [openedai-speech roadmap](https://github.com/matatonic/openedai-speech) for planned features.

## References

- [openedai-speech GitHub](https://github.com/matatonic/openedai-speech)
- [Coqui TTS Documentation](https://github.com/coqui-ai/TTS)
- [XTTS v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
- [OpenAI Audio API](https://platform.openai.com/docs/guides/text-to-speech)
- [XTTS v2 Paper](https://arxiv.org/abs/2406.04904)
