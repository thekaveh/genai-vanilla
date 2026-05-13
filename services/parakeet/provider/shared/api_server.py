"""
OpenAI-compatible Speech-to-Text API Server
Supports both MLX (Mac) and NVIDIA GPU (CUDA) backends
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import logging

# Import backend-specific transcriber
try:
    from transcribe import transcribe_audio
except ImportError as e:
    logging.error(f"Failed to import transcribe module: {e}")
    raise

app = FastAPI(
    title="Parakeet STT API",
    version="1.0.0",
    description="OpenAI-compatible Speech-to-Text API using NVIDIA Parakeet-TDT"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Parakeet STT API",
        "version": "1.0.0",
        "description": "OpenAI-compatible Speech-to-Text API",
        "backend": os.getenv("PARAKEET_BACKEND", "cuda"),
        "device": os.getenv("PARAKEET_DEVICE", "unknown"),
        "model": os.getenv("PARAKEET_MODEL", "nvidia/parakeet-tdt-0.6b-v3")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "backend": os.getenv("PARAKEET_BACKEND", "cuda"),
        "device": os.getenv("PARAKEET_DEVICE", "unknown"),
        "model": os.getenv("PARAKEET_MODEL", "unknown")
    }

@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(default="parakeet-tdt-0.6b-v3"),
    language: str = Form(default=None),
    prompt: str = Form(default=None),
    response_format: str = Form(default="json"),
    temperature: float = Form(default=0.0)
):
    """
    OpenAI-compatible transcription endpoint

    POST /v1/audio/transcriptions

    Accepts audio files (.wav, .flac, .mp3, etc.) and returns transcription text
    Compatible with OpenAI Whisper API format

    Args:
        file: Audio file to transcribe
        model: Model identifier (informational, actual model from PARAKEET_MODEL env)
        language: Optional language code for transcription
        prompt: Optional context prompt (not used by Parakeet)
        response_format: Format of response (json, verbose_json, text)
        temperature: Sampling temperature (0.0 = greedy decoding)

    Returns:
        Transcription result in requested format
    """
    try:
        logger.info(f"Received transcription request: file={file.filename}, language={language}, format={response_format}")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"Saved temporary file: {tmp_path}")

        # Transcribe using backend-specific function
        result = await transcribe_audio(
            audio_path=tmp_path,
            language=language,
            temperature=temperature
        )

        # Clean up temporary file
        os.unlink(tmp_path)

        # Format response based on response_format
        if response_format == "json":
            return {"text": result["text"]}
        elif response_format == "verbose_json":
            return result
        elif response_format == "text":
            return result["text"]
        else:
            return {"text": result["text"]}

    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        # Clean up temp file if it exists
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/audio/transcriptions/advanced")
async def transcribe_advanced(
    file: UploadFile = File(...),
    return_timestamps: bool = Form(default=True),
    word_timestamps: bool = Form(default=False)
):
    """
    Advanced transcription endpoint with Parakeet-specific features

    POST /v1/audio/transcriptions/advanced

    Returns word-level timestamps and additional metadata

    Args:
        file: Audio file to transcribe
        return_timestamps: Whether to return segment timestamps
        word_timestamps: Whether to return word-level timestamps

    Returns:
        Detailed transcription result with timestamps
    """
    try:
        logger.info(f"Received advanced transcription request: file={file.filename}, timestamps={return_timestamps}, word_timestamps={word_timestamps}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = await transcribe_audio(
            audio_path=tmp_path,
            return_timestamps=return_timestamps,
            word_timestamps=word_timestamps
        )

        os.unlink(tmp_path)
        return result

    except Exception as e:
        logger.error(f"Advanced transcription error: {str(e)}", exc_info=True)
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
