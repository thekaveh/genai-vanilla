# XTTS v2 TTS Server - Localhost Mode

Run openedai-speech TTS server natively on your host machine (any platform).

## Quick Start

### 1. Clone openedai-speech

```bash
cd tts-provider/localhost
git clone https://github.com/matatonic/openedai-speech.git
```

**Note:** openedai-speech is not available as a PyPI package, so it must be cloned from GitHub.

### 2. Install Dependencies

```bash
uv sync
```

This installs all required dependencies (fastapi, uvicorn, piper-tts, TTS/XTTS v2, torch, etc.)

**For GPU acceleration (NVIDIA CUDA):**
```bash
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. Start the Server

```bash
uv run server.py
```

The server will start on `http://0.0.0.0:63023` by default (base_port + 23).

**First run:** Downloads models (~1-2GB). Please be patient (5-10 minutes).
**Subsequent runs:** Instant startup.

### 4. Test the API

```bash
curl -X POST http://localhost:63023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "tts-1-hd", "input": "Hello world!", "voice": "alloy"}' \
  --output speech.mp3
```

## Configuration

Set environment variables before running:

```bash
export TTS_PROVIDER_PORT=63023          # Server port (auto-adjusts with --base-port flag)
export PRELOAD_MODEL=tts-1-hd           # Model to preload (tts-1 or tts-1-hd)
export TTS_HOME=./voices                # Voice files directory
export HF_HOME=~/.cache/huggingface     # HuggingFace cache
```

## Available Models

- **tts-1**: Piper TTS (fast, CPU-friendly, lower quality)
- **tts-1-hd**: XTTS v2 (high quality, GPU-accelerated, voice cloning)

## Available Voices

OpenAI-compatible voices:
- **alloy** - Neutral, balanced
- **echo** - Male, clear
- **fable** - British accent
- **onyx** - Deep male
- **nova** - Female, energetic
- **shimmer** - Soft female

## Voice Cloning

XTTS v2 supports zero-shot voice cloning with 6 second samples. See main documentation for details.

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
export TTS_PROVIDER_PORT=63099  # Use any available port
uv run server.py

# Update .env to match
XTTS_LOCALHOST_URL=http://host.docker.internal:63099
```

**GPU not detected:**
```bash
# Install CUDA-enabled PyTorch
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Model download fails:**
```bash
# Set HuggingFace token if needed
export HF_TOKEN=your_token_here
uv run server.py
```

### Dependency Version Issues

**Problem**: `ImportError: cannot import name 'BeamSearchScorer' from 'transformers'`

**Cause**: Newer versions of transformers (4.43+) moved `BeamSearchScorer`, breaking XTTS v2 compatibility.

**Solution**:
```bash
# Our pyproject.toml pins transformers to 4.40.2-4.43.0
uv sync  # Reinstalls correct version

# If issue persists:
uv pip install "transformers==4.42.4" --force-reinstall
```

**Problem**: Numpy version conflicts during installation

**Cause**: TTS library requires numpy <2.0, but some dependencies try to install numpy 2.x

**Solution**:
```bash
# Our pyproject.toml pins numpy to 1.22.0-2.0 range
uv sync  # Handles version resolution automatically
```

## Performance

- **CPU**: ~2-5x real-time (slow but works)
- **GPU**: ~0.3-0.5x real-time (fast, recommended)
- **Model size**: ~2GB for XTTS v2, ~200MB for Piper

## Technical Details

### Automatic TOS Acceptance

The server automatically accepts Coqui TTS license terms by setting `COQUI_TOS_AGREED=1`. This prevents interactive prompts during model downloads.

**By using this service, you agree to the [Coqui Public Model License (CPML)](https://coqui.ai/cpml).**

### Model Download Behavior

- **Server startup**: Fast (no model downloads)
- **First API request**: Downloads XTTS v2 model (~1-2GB, takes 5-10 minutes)
- **Subsequent requests**: Instant (models cached in `~/.cache/huggingface/`)

The server starts quickly, but the first TTS generation request will trigger the model download.

### Why openedai-speech?

openedai-speech is a compatibility wrapper that:
- **Provides**: OpenAI `/v1/audio/speech` API format
- **Uses**: Coqui XTTS v2 as the backend TTS engine
- **Enables**: Seamless integration with Open WebUI and other OpenAI-compatible clients

```
TTS Stack Architecture:
┌─────────────────────┐
│   Open WebUI        │  (expects OpenAI API)
└──────────┬──────────┘
           │ POST /v1/audio/speech
┌──────────▼──────────┐
│  openedai-speech    │  (wrapper/adapter)
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Coqui XTTS v2      │  (TTS engine)
└─────────────────────┘
```

Both GPU Docker and localhost modes use openedai-speech for API compatibility.

## Integration with GenAI Stack

When using `TTS_PROVIDER_SOURCE=xtts-localhost`, ensure this server is running:

```bash
# Terminal 1: Start TTS server
cd tts-provider/localhost
git clone https://github.com/matatonic/openedai-speech.git  # First time only
uv sync  # First time only (or after updates)
uv run server.py

# Terminal 2: Start the stack
./start.sh --tts-provider-source xtts-localhost
```

**Note:** The git clone and uv sync commands only need to be run once during initial setup.

## References

- [openedai-speech GitHub](https://github.com/matatonic/openedai-speech)
- [Coqui TTS Documentation](https://github.com/coqui-ai/TTS)
- [XTTS v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
