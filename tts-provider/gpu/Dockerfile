FROM ghcr.io/matatonic/openedai-speech:latest

# Set working directory
WORKDIR /app

# Pre-download XTTS v2 model on build (optional optimization)
# Uncomment to pre-cache models in the image
# ENV PRELOAD_MODEL=tts-1-hd

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=2m --retries=5 \
  CMD curl -f http://localhost:8000/v1/models || exit 1

# Run server
CMD ["python", "-m", "openedai_speech"]
