"""Example DAG demonstrating Spark + MinIO + LiteLLM integrations.

Runs daily. Steps:
1. SparkSubmitOperator submits a stub job to the in-stack Spark cluster.
2. OpenAIOperator (wired to LiteLLM via litellm_default) summarizes a
   piece of text.
3. S3Hook lists the contents of an arbitrary MinIO bucket (smoke).

This DAG is intentionally tiny — it confirms each Connection works
end-to-end without doing real work. Replace with your own DAGs.
"""
from __future__ import annotations

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.openai.operators.openai import OpenAIOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "genai-vanilla",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def list_minio(**_ctx):
    s3 = S3Hook(aws_conn_id="minio_default")
    buckets = s3.get_conn().list_buckets()["Buckets"]
    print(f"buckets: {[b['Name'] for b in buckets]}")


with DAG(
    "example_etl_with_llm",
    description="Smoke test: Spark + MinIO + LiteLLM integrations",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 6, 4),
    catchup=False,
    tags=["smoke", "stack-internal"],
) as dag:

    spark_step = SparkSubmitOperator(
        task_id="spark_stub_job",
        conn_id="spark_default",
        application="/opt/airflow/dags/example_etl_with_llm.py",
        conf={"spark.master": "spark://spark-master:7077"},
    )

    llm_step = OpenAIOperator(
        task_id="summarize_via_litellm",
        conn_id="litellm_default",
        model="ollama/qwen3.6:latest",
        messages=[{"role": "user", "content": "Reply with the single word 'ok'."}],
    )

    minio_step = PythonOperator(
        task_id="list_minio_buckets",
        python_callable=list_minio,
    )

    spark_step >> llm_step >> minio_step
