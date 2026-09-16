from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)


def _project_root() -> Path:
    if env := os.environ.get("AIRFLOW_PROJECT_ROOT"):
        return Path(env)
    here = Path(__file__).resolve()
    for candidate in (here.parents[1], here.parents[2], *here.parents):
        if (candidate / "superstore" / "etl").is_dir():
            return candidate
    return here.parents[2]


PROJECT_ROOT = _project_root()


def _run_python_module(module: str, **context) -> None:
    subprocess.run(
        [sys.executable, "-m", module],
        cwd=str(PROJECT_ROOT),
        check=True,
    )


def _validate_data_quality(**context) -> None:
    import pandas as pd

    from superstore.etl.data_quality import run_checks

    path = PROJECT_ROOT / "data" / "processed" / "orders_clean.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run ETL task first")
    df = pd.read_parquet(path)
    report = run_checks(df)
    if not report.passed:
        failed = [c["check"] for c in report.checks if not c["ok"]]
        raise ValueError(f"Quality failed: {failed}")
    logger.info("Проверка пройдена: %s строк", f"{len(df):,}")


# H4: включены retries, execution_timeout; убран email_on_failure=False
default_args = {
    "owner": "data-analyst",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}

with DAG(
    dag_id="superstore_etl",
    description="Загрузка CSV → Parquet/DuckDB → проверка качества",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    # L5: исторические данные 2011-2014 — ежедневный перезапуск не нужен
    schedule=None,
    catchup=False,
    tags=["superstore", "etl", "portfolio"],
) as dag:
    # C1: исправлены имена модулей (python.* → superstore.*)
    etl = PythonOperator(
        task_id="run_python_etl",
        python_callable=_run_python_module,
        op_kwargs={"module": "superstore.etl.load_and_clean"},
    )

    eda = PythonOperator(
        task_id="run_eda_plots",
        python_callable=_run_python_module,
        op_kwargs={"module": "superstore.analysis.eda"},
    )

    validate = PythonOperator(
        task_id="validate_data_quality",
        python_callable=_validate_data_quality,
    )

    stats = PythonOperator(
        task_id="run_stats_models",
        python_callable=_run_python_module,
        op_kwargs={"module": "superstore.analysis.stats_models"},
    )

    etl >> [eda, validate] >> stats
