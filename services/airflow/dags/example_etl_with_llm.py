"""Example DAG demonstrating Spark + MinIO + LiteLLM integrations.

Runs daily. Three operators that exercise each seeded Airflow Connection:

1. ``PythonOperator`` calls the Spark cluster via Spark Connect (the modern
   gRPC client; no JAR submission needed for a smoke test). Confirms
   ``spark_default`` Connection + the in-stack Spark master are healthy.
2. ``OpenAIOperator`` summarises a piece of text via LiteLLM. Confirms the
   ``litellm_default`` Connection works. The openai provider is the
   straightforward driver; for richer chains use ``LangChainOperator`` from
   ``apache-airflow-providers-langchain`` (bundled in build/requirements.txt)
   — see the commented block at the bottom of this file.
3. ``S3Hook`` lists buckets via ``minio_default``.

This DAG is intentionally tiny — replace with your own DAGs.

The smoke-test design rationale: the spec called for `SparkSubmitOperator`
but submitting a real Spark application from the init/airflow image would
require either (a) bundling the JAR in `services/airflow/dags/` or
(b) bind-mounting a separate scripts directory. Neither is in scope for
the v1 sample. Spark Connect via a tiny Python step gives the same
"connection is alive" smoke without owning a JAR build.

Model selection: the LLM step defaults to ``ollama/qwen3.6:latest``,
which assumes the stack's default Ollama-mode catalog. If you run with
``--llm-provider-source none`` + ``CLOUD_OPENAI_SOURCE=enabled`` (cloud-
only mode), swap ``model="ollama/qwen3.6:latest"`` for a cloud model id
like ``gpt-4o-mini``. See services/litellm/README.md for the available
model ids in each provider configuration.
"""
from __future__ import annotations

from airflow import DAG
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.openai.operators.openai import OpenAIOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator  # noqa: F401  # available for user DAGs
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta


default_args = {
    "owner": "genai-vanilla",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def spark_smoke(**_ctx):
    """Confirm spark://spark-master:7077 + sc://spark-master:15002 are reachable.

    Uses Spark Connect (modern gRPC client) — no JAR submission, no
    cluster-mode dependencies. Returns the master version.
    """
    from pyspark.sql import SparkSession
    spark = (
        SparkSession.builder
        .remote("sc://spark-master:15002")
        .appName("airflow-smoke")
        .getOrCreate()
    )
    print(f"Spark Connect connected; version={spark.version}")
    spark.stop()


def list_minio(**_ctx):
    s3 = S3Hook(aws_conn_id="minio_default")
    buckets = s3.get_conn().list_buckets()["Buckets"]
    print(f"buckets: {[b['Name'] for b in buckets]}")


with DAG(
    "example_etl_with_llm",
    description="Smoke test: Spark + MinIO + LiteLLM Connections",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 6, 4),
    catchup=False,
    tags=["smoke", "stack-internal"],
) as dag:

    spark_step = PythonOperator(
        task_id="spark_smoke",
        python_callable=spark_smoke,
    )

    llm_step = OpenAIOperator(
        task_id="summarize_via_litellm",
        conn_id="litellm_default",
        # Default Ollama model that ships in the stack's LiteLLM catalog
        # (see bootstrapper/utils/llm_catalog.py + services/litellm/README.md).
        model="ollama/qwen3.6:latest",
        messages=[{"role": "user", "content": "Reply with the single word 'ok'."}],
    )

    minio_step = PythonOperator(
        task_id="list_minio_buckets",
        python_callable=list_minio,
    )

    spark_step >> llm_step >> minio_step


# ─── LangChainOperator example (commented; uncomment + adapt as needed) ───
# from langchain_core.runnables import RunnablePassthrough
# from langchain_openai import ChatOpenAI
# from airflow.providers.langchain.operators.langchain import LangChainOperator
#
# def build_chain():
#     llm = ChatOpenAI(
#         model="ollama/qwen3.6:latest",
#         base_url="http://litellm:4000/v1",
#         api_key=os.environ["LITELLM_MASTER_KEY"],
#     )
#     return RunnablePassthrough() | llm
#
# with DAG("langchain_example", ...) as dag2:
#     LangChainOperator(
#         task_id="run_chain",
#         conn_id="litellm_default",
#         runnable=build_chain,
#         inputs={"input": "Reply with the single word 'ok'."},
#     )
