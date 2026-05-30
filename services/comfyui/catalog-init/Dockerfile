# Init-container exception to the stack's "vanilla alpine + apk add" rule:
# this init needs psycopg2 + requests + pyyaml to UPSERT the live-assembled
# ComfyUI catalog. Python-slim avoids the apk + build-deps gymnastics that
# the musl/alpine wheel story for psycopg2 forces. Mirrors the
# services/litellm/catalog-init image.
FROM python:3.12-slim

# psycopg2-binary: same pinned wheel as llm-catalog-init for consistency.
# requests + pyyaml: live HF/civitai scrape + sidecar YAML parse via
# bootstrapper/utils/comfyui_library (mounted at /catalog).
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 requests pyyaml

WORKDIR /app

# Scripts and the catalog module are bind-mounted at runtime, NOT
# baked into the image, so users can edit ``comfyui_library.py`` without
# rebuilding the image.

ENTRYPOINT ["python", "/scripts/sync-catalog.py"]
