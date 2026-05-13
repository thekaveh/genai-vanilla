ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN pip install requests psycopg2-binary PyJWT

COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

CMD ["sh", "-c", "python3 /app/scripts/register-tools.py && python3 /app/scripts/register-functions.py"]
