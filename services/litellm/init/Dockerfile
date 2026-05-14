# Init-container exception to the stack's "vanilla alpine + apk add" rule:
# this init needs pinned psycopg2-binary==2.9.9 and PyYAML==6.0.2. The
# psycopg2-binary wheel is glibc-only (incompatible with musl/alpine),
# and pinning matters because the script's SQL/YAML output is consumed by
# litellm's runtime config. Python-slim avoids the apk + build-deps gymnastics.
FROM python:3.12-slim

# psycopg2-binary keeps the image small (no system libpq build chain).
# pyyaml renders the config.yaml from query results.
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 PyYAML==6.0.2

WORKDIR /app

# Scripts are bind-mounted at runtime (see docker-compose.yml).

ENTRYPOINT ["python", "/scripts/init.py"]
