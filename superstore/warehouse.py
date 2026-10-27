"""DuckDB warehouse: cleaned Parquet -> orders table -> stg_orders view -> mart_* tables."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from superstore import config

log = logging.getLogger(__name__)

MARTS: tuple[str, ...] = (
    "01_kpi_summary",
    "02_monthly_sales",
    "03_region_year",
    "04_market_discount",
    "05_discount_bands",
    "06_subcategory_discount",
    "07_subcategory_band",
)


def mart_table_name(model: str) -> str:
    """'05_discount_bands' -> 'mart_discount_bands' (identifiers cannot start with a digit)."""
    return "mart_" + model.split("_", 1)[1]


def connect(parquet: Path = config.PARQUET, database: str | Path = ":memory:", sql_dir: Path = config.SQL_DIR):
    """Open DuckDB, load the cleaned orders and create the staging view."""
    con = duckdb.connect(str(database))
    con.read_parquet(Path(parquet).as_posix()).create("orders")
    con.execute((sql_dir / "stg_orders.sql").read_text(encoding="utf-8"))
    return con


def build_marts(con: duckdb.DuckDBPyConnection, sql_dir: Path = config.SQL_DIR) -> dict[str, pd.DataFrame]:
    """Materialize every mart as a table and return its contents keyed by model name."""
    results: dict[str, pd.DataFrame] = {}
    for model in MARTS:
        sql = (sql_dir / "marts" / f"{model}.sql").read_text(encoding="utf-8").strip().rstrip(";")
        table = mart_table_name(model)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS\n{sql}")
        results[model] = con.table(table).df()
        log.info("Built %-26s %4d rows", table, len(results[model]))
    return results


def build_warehouse_file(path: Path = config.DUCKDB_PATH, parquet: Path = config.PARQUET) -> dict[str, pd.DataFrame]:
    """Rebuild the persistent DuckDB file from scratch (for BI tools and ad-hoc SQL)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        for stale in (path, path.with_name(path.name + ".wal")):
            stale.unlink(missing_ok=True)
    except PermissionError as exc:
        raise SystemExit(f"{path} is open in another program (DBeaver, Jupyter, ...). Close it and rerun.") from exc
    con = connect(parquet, path)
    try:
        return build_marts(con)
    finally:
        con.close()
