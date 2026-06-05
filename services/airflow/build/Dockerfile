ARG BASE_IMAGE=apache/airflow:3.2.2
FROM ${BASE_IMAGE}

# Providers needed for the cross-stack integrations declared in the spec
# §5.3. apache-spark for SparkSubmitOperator; amazon for S3Hook (works
# with MinIO via endpoint override); langchain + openai for LiteLLM
# integration; weaviate + neo4j + postgres + redis for the per-DB
# Connections seeded by airflow-init.
COPY requirements.txt /tmp/airflow-providers.txt
RUN pip install --no-cache-dir -r /tmp/airflow-providers.txt
