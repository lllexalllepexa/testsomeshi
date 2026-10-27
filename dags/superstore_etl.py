"""Airflow DAG: raw workbook -> Parquet -> quality gate -> DuckDB marts -> statistics -> charts.

Each task runs one step of the same CLI used locally, so the DAG adds orchestration (retries, ordering,
history) without a second copy of the logic. When no raw file is present, the ETL task is skipped and
the downstream tasks run on the committed Parquet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

PROJECT_ROOT = Path(os.environ.get("AIRFLOW_PROJECT_ROOT", Path(__file__).resolve().parents[1]))


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=PROJECT_ROOT, check=True)


def _etl() -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    if not any(raw_dir.glob(p) for p in ("*.xls", "*.xlsx", "*.csv")):
        raise AirflowSkipException("No raw file in data/raw; using the committed Parquet")
    _run("-m", "superstore.etl.load_and_clean")


def _step(name: str) -> None:
    _run("-m", "superstore.pipeline", "--step", name)


default_args = {
    "owner": "data-analyst",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}

with DAG(
    dag_id="superstore_etl",
    description="Global Superstore: raw -> Parquet -> quality -> marts -> statistics -> charts",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,  # historical 2011-2014 data: run on demand
    catchup=False,
    tags=["superstore", "etl", "portfolio"],
) as dag:
    etl = PythonOperator(task_id="etl_raw_to_parquet", python_callable=_etl)
    steps = [
        PythonOperator(
            task_id=name,
            python_callable=_step,
            op_kwargs={"name": name},
            trigger_rule=TriggerRule.NONE_FAILED,  # still run when the ETL task was skipped
        )
        for name in ("validate", "marts", "stats", "charts")
    ]
    etl >> steps[0] >> steps[1] >> steps[2] >> steps[3]
