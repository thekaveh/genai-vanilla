# Init-container exception to the stack's "vanilla alpine + apk add" rule:
# this init needs psycopg2-binary + PyJWT, both of which ship glibc-only
# wheels (musl/alpine incompatible). Python-slim avoids the apk + build-deps
# gymnastics. Override via OPEN_WEB_UI_INIT_IMAGE in .env if needed.
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN pip install requests psycopg2-binary PyJWT

COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

CMD ["sh", "-c", "python3 /app/scripts/register-tools.py && python3 /app/scripts/register-functions.py"]
