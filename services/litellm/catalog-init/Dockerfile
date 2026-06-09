# Init-container exception to the stack's "vanilla alpine + apk add" rule:
# this init needs pinned psycopg2-binary==2.9.9 to UPSERT the curated LLM
# catalog. The psycopg2-binary wheel is glibc-only (incompatible with
# musl/alpine); using Python-slim avoids the apk + build-deps gymnastics.
FROM python:3.12.7-slim

# psycopg2-binary keeps the image small (no system libpq build needed).
RUN pip install --no-cache-dir psycopg2-binary==2.9.9

WORKDIR /app

# Scripts and the catalog module are bind-mounted at runtime, NOT
# baked into the image, so users can edit ``llm_catalog.py`` without
# rebuilding the image.

ENTRYPOINT ["python", "/scripts/sync-catalog.py"]
