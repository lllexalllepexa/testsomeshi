# Airflow DAG

[`superstore_etl.py`](superstore_etl.py):

```
etl_raw_to_parquet → validate → marts → stats → charts
```

Each task calls one step of `python -m superstore.pipeline`, the same CLI used locally. If `data/raw/` is empty, the ETL task is skipped and the rest runs on the committed Parquet.

How to run: [docs/airflow.md](../docs/airflow.md).
