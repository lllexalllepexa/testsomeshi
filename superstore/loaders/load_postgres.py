"""
Загрузка Parquet в PostgreSQL.

Сначала поднимите Postgres:
  docker compose up -d postgres
  (Docker Desktop должен быть запущен: docker info)

Затем:
  python -m superstore.loaders.load_postgres
"""
from __future__ import annotations

import logging
import os
import socket
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "data" / "processed" / "orders_clean.parquet"

# M8: URL из переменной окружения, fallback для локальной разработки
URL = os.getenv(
    "SUPERSTORE_PG_URL",
    "postgresql+psycopg2://analyst:analyst@127.0.0.1:5432/superstore",
)


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main(url: str = URL) -> None:
    if not PARQUET.exists():
        raise SystemExit(
            f"Нет {PARQUET}. Сначала: python -m superstore.etl.load_and_clean"
        )

    if not _port_open("127.0.0.1", 5432):
        logger.error(
            "PostgreSQL на порту 5432 недоступен.\n"
            "1. Запустите Docker Desktop (иконка в трее → Engine running).\n"
            "2. docker compose up -d postgres\n"
            "3. Подождите ~10 сек и повторите эту команду.\n"
            "\n"
            "Без Docker используйте SQL через DuckDB:\n"
            "  .\\scripts\\sql_duckdb_demo.ps1\n"
            "  или: docs/sql_postgres.md"
        )
        raise SystemExit(1)

    df = pd.read_parquet(PARQUET)
    engine = create_engine(
        url,
        connect_args={"connect_timeout": 10, "options": "-c client_encoding=UTF8"},
    )

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(
            "Не удалось подключиться к PostgreSQL.\n"
            "URL: %s\nОшибка: %s\n\n"
            "Проверьте: docker compose ps\n"
            "Логи: docker compose logs postgres",
            url,
            exc,
        )
        raise SystemExit(1) from exc

    try:
        # C5: атомарная загрузка через staging-таблицу
        df.to_sql(
            "orders_staging", engine, if_exists="replace", index=False, chunksize=5000
        )
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS orders_old"))
            conn.execute(text("ALTER TABLE IF EXISTS orders RENAME TO orders_old"))
            conn.execute(text("ALTER TABLE orders_staging RENAME TO orders"))
            conn.execute(text("DROP TABLE IF EXISTS orders_old"))
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_orders_region ON orders (region)")
            )
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        logger.info("PostgreSQL: в таблице orders — %s строк", f"{n:,}")
    finally:
        # M6: освобождаем пул соединений
        engine.dispose()


if __name__ == "__main__":
    main()
