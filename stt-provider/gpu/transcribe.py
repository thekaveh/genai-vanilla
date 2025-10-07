"""
NVIDIA NeMo-based transcription implementation for Parakeet-TDT
Optimized for NVIDIA GPUs with CUDA acceleration
"""

import os
import logging
import nemo.collections.asr as nemo_asr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model (loaded once on startup)
_model = None

def load_model():
    """Load Parakeet model using NVIDIA NeMo (lazy loading)"""
    global _model

    if _model is None:
        model_name = os.getenv("PARAKEET_MODEL", "nvidia/parakeet-tdt-0.6b-v3")
        device = os.getenv("PARAKEET_DEVICE", "cuda")

        logger.info(f"Loading Parakeet model: {model_name} on device: {device}")

        try:
            # Load model using NeMo
            _model = nemo_asr.models.ASRModel.from_pretrained(model_name)

            # Move to specified device
            if device == "cuda":
                _model = _model.cuda()
                logger.info(f"Model loaded on CUDA device")
            else:
                _model = _model.cpu()
                logger.info(f"Model loaded on CPU device")

            # Set to evaluation mode
            _model.eval()

            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    return _model

async def transcribe_audio(
    audio_path: str,
    language: str = None,
    temperature: float = 0.0,
    return_timestamps: bool = False,
    word_timestamps: bool = False
):
    """
    Transcribe audio file using Parakeet-TDT with NVIDIA NeMo

    Args:
        audio_path: Path to audio file (.wav, .flac, etc.)
        language: Optional language code (auto-detect if None)
        temperature: Sampling temperature (not used by NeMo)
        return_timestamps: Whether to return segment timestamps
        word_timestamps: Whether to return word-level timestamps

    Returns:
        dict: Transcription result with text and optional timestamps
    """
    try:
        # Load model (lazy loading)
        model = load_model()

        # Transcribe using NeMo
        logger.info(f"Transcribing audio file: {audio_path}")

        # NeMo transcription
        transcription = model.transcribe([audio_path])

        # Extract text result
        if isinstance(transcription, list):
            text = transcription[0]
        else:
            text = str(transcription)

        logger.info(f"Transcription complete: {len(text)} characters")

        # Build result
        result = {
            "text": text,
            "language": language or "auto"
        }

        # Add timestamp information if requested and available
        if return_timestamps:
            # Parakeet-TDT supports word-level timestamps
            try:
                # Get timestamps from model if available
                timestamps_result = model.transcribe(
                    [audio_path],
                    return_hypotheses=True
                )
                if hasattr(timestamps_result[0], 'timestep'):
                    result["timestamps"] = timestamps_result[0].timestep
                    result["has_timestamps"] = True
                else:
                    result["has_timestamps"] = False
            except Exception as e:
                logger.warning(f"Could not extract timestamps: {e}")
                result["has_timestamps"] = False

        return result

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise

# Pre-load model on module import (optional, for faster first request)
if os.getenv("PRELOAD_MODEL", "false").lower() == "true":
    logger.info("Pre-loading model on startup...")
    load_model()
