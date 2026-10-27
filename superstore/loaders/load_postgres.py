"""Load the cleaned Parquet into PostgreSQL.

    docker compose up -d postgres
    python -m superstore.loaders.load_postgres          # URL from SUPERSTORE_PG_URL, see DEFAULT_URL

The load is one transaction: create the schema if needed (sql/postgres/init.sql), stage the rows,
TRUNCATE + INSERT into the typed `orders` table. Readers see either the old rows or the new ones, the
table keeps its declared types and constraints, and the views on top of it are never dropped.
"""

from __future__ import annotations

import logging
import os

import pandas as pd
from sqlalchemy import create_engine, text

from superstore import config

log = logging.getLogger(__name__)

DEFAULT_URL = "postgresql+psycopg2://analyst:analyst@127.0.0.1:5432/superstore"
INIT_SQL = config.ROOT / "sql" / "postgres" / "init.sql"
COLUMNS = [
    "row_id", "order_id", "order_key", "order_date", "ship_date", "ship_mode", "customer_id", "customer_name",
    "segment", "city", "state", "country", "market", "region", "product_id", "category", "sub_category",
    "product_name", "sales", "quantity", "discount", "profit", "shipping_cost", "order_priority", "is_returned",
    "year", "delivery_days", "profit_margin",
]  # fmt: skip


def load(df: pd.DataFrame, url: str) -> int:
    """Replace the contents of `orders` with ``df`` atomically; return the row count."""
    engine = create_engine(url)
    cols = ", ".join(COLUMNS)
    try:
        with engine.begin() as conn:
            with conn.connection.cursor() as cur:  # plain DBAPI cursor: init.sql has literal '%' signs
                cur.execute(INIT_SQL.read_text(encoding="utf-8"))
            df[COLUMNS].to_sql("orders_staging", conn, if_exists="replace", index=False, chunksize=5000)
            conn.execute(text("TRUNCATE orders"))
            conn.execute(text(f"INSERT INTO orders ({cols}) SELECT {cols} FROM orders_staging"))
            conn.execute(text("DROP TABLE orders_staging"))
            return conn.execute(text("SELECT count(*) FROM orders")).scalar_one()
    finally:
        engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    url = os.getenv("SUPERSTORE_PG_URL", DEFAULT_URL)
    n = load(pd.read_parquet(config.PARQUET), url)
    log.info("PostgreSQL: orders has %s rows", f"{n:,}")


if __name__ == "__main__":
    main()
