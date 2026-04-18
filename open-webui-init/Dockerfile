ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

RUN pip install requests psycopg2-binary PyJWT

COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

CMD ["python3", "/app/scripts/register-tools.py"]
