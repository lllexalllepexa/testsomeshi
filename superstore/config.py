"""Repository paths, defined once."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PARQUET = ROOT / "data" / "processed" / "orders_clean.parquet"
DUCKDB_PATH = ROOT / "data" / "processed" / "superstore.duckdb"
SQL_DIR = ROOT / "sql" / "duckdb"
OUTPUTS_DIR = ROOT / "outputs"
FIGURES_DIR = ROOT / "docs" / "images"
