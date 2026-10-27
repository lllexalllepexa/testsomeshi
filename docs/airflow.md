# Airflow

DAG: [`dags/superstore_etl.py`](../dags/superstore_etl.py) — `etl_raw_to_parquet → validate → marts → stats → charts`.

Каждая задача вызывает один шаг `python -m superstore.pipeline`, поэтому логика не дублируется: DAG добавляет только порядок, повторы и историю запусков. Если в `data/raw/` нет исходного файла, задача ETL помечается как пропущенная, а остальные работают на закоммиченном Parquet.

## Запуск в Docker (Windows, macOS, Linux)

```bash
docker compose -f docker-compose.airflow.yml run --rm airflow-dag-test
```

## Linux / WSL без Docker

```bash
export AIRFLOW_HOME=$PWD/.airflow AIRFLOW_PROJECT_ROOT=$PWD PYTHONPATH=$PWD
pip install apache-airflow==2.10.4 duckdb pyarrow python-calamine scipy statsmodels matplotlib
airflow db migrate
airflow dags test superstore_etl 2024-01-01
```

На Windows без Docker Airflow не запускается (нет модуля `fcntl`).
