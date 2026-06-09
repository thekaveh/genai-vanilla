# Init-container exception to the stack's "vanilla alpine + apk add" rule:
# this init needs psycopg2 + requests + pyyaml to UPSERT the live-assembled
# ComfyUI catalog. Python-slim avoids the apk + build-deps gymnastics that
# the musl/alpine wheel story for psycopg2 forces. Mirrors the
# services/litellm/catalog-init image.
FROM python:3.12.7-slim

# psycopg2-binary: same pinned wheel as llm-catalog-init for consistency.
# requests + PyYAML: live HF/civitai scrape + sidecar YAML parse via
# bootstrapper/utils/comfyui_library (mounted at /catalog). Pinned so a
# future upstream regression doesn't slip in at docker compose up time
# (this Dockerfile isn't covered by CI build-validation).
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 requests==2.32.3 PyYAML==6.0.2

WORKDIR /app

# Scripts and the catalog module are bind-mounted at runtime, NOT
# baked into the image, so users can edit ``comfyui_library.py`` without
# rebuilding the image.

ENTRYPOINT ["python", "/scripts/sync-catalog.py"]
