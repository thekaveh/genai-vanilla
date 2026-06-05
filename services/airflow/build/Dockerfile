ARG BASE_IMAGE=apache/airflow:3.2.2
FROM ${BASE_IMAGE}

# Pin to the matching Airflow constraints file. Without --constraint
# pip can silently upgrade transitive deps (sqlalchemy, alembic, flask,
# etc.) past versions Airflow tested against — same shipping-class bug
# Pass 12-13 hit when unbounded floors let `>=2.0.0` / `>=4.1.0` resolve
# to nonexistent versions. The constraint file is the upstream fence.
ARG AIRFLOW_VERSION=3.2.2
ARG PYTHON_MAJOR_MINOR=3.12

# Providers needed for the cross-stack integrations declared in the spec
# §5.3. apache-spark for SparkSubmitOperator; amazon for S3Hook (works
# with MinIO via endpoint override); openai for LiteLLM integration;
# weaviate + neo4j + postgres + redis for the per-DB Connections seeded
# by airflow-init; fab for the auth backend; common-sql for the sample
# DAG's SQLExecuteQueryOperator. (LangChain runs via PythonOperator +
# langchain-openai; no apache-airflow-providers-langchain package
# exists on PyPI.)
COPY requirements.txt /tmp/airflow-providers.txt
RUN pip install --no-cache-dir -r /tmp/airflow-providers.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_MAJOR_MINOR}.txt"
