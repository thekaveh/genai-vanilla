FROM python:3.12-slim

# psycopg2-binary keeps the image small (no system libpq build chain).
# pyyaml renders the config.yaml from query results.
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 PyYAML==6.0.2

WORKDIR /app

# Scripts are bind-mounted at runtime (see docker-compose.yml).

ENTRYPOINT ["python", "/scripts/init.py"]
