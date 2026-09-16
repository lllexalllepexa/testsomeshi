"""
ETL: CSV -> cleaned Parquet + DuckDB + optional PostgreSQL.
Run: python -m superstore.etl.load_and_clean
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "global_superstore.csv"
OUT_PARQUET = ROOT / "data" / "processed" / "orders_clean.parquet"
DUCKDB_PATH = ROOT / "data" / "processed" / "superstore.duckdb"

RENAME = {
    "Customer ID": "customer_id",
    "Customer Name": "customer_name",
    "Order Date": "order_date",
    "Order ID": "order_id",
    "Order Priority": "order_priority",
    "Product ID": "product_id",
    "Product Name": "product_name",
    "Row ID": "row_id",
    "Ship Date": "ship_date",
    "Ship Mode": "ship_mode",
    "Shipping Cost": "shipping_cost",
    "Sub-Category": "sub_category",
    "ji_lu-shu": "record_count",
    "Market2": "market_group",
}


def resolve_raw() -> Path:
    if RAW.exists():
        return RAW
    raise FileNotFoundError(f"Положите CSV сюда: {RAW}")


def repair_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    В этом CSV даты часто битые (Excel: '00:00.0').
    Восстанавливаем order_date из year + weeknum и order_id (CA-2011-…).
    Используем ISO-8601 недели для корректного вычисления дат.
    """
    # H3: работаем с копией, не мутируем входной DataFrame
    df = df.copy()

    year = pd.to_numeric(df.get("year"), errors="coerce")
    from_id = df["order_id"].str.extract(r"-(\d{4})-", expand=False)
    year = year.fillna(pd.to_numeric(from_id, errors="coerce"))

    week = pd.to_numeric(df.get("weeknum"), errors="coerce")

    # M5: логируем fallback для weeknum
    n_missing_week = week.isna().sum()
    if n_missing_week > 0:
        logger.warning(
            "weeknum отсутствует в %d строках (%.1f%%), подставлено 26 (≈конец июня)",
            n_missing_week,
            100 * n_missing_week / len(df),
        )
    week = week.fillna(26).clip(1, 52)

    # H1: используем ISO-8601 формат недель (%G-W%V-%u) вместо
    # наивного Jan-1 + (week-1)*7, который даёт сдвиг до ±6 дней
    iso_year = year.astype("Int64").astype(str)
    iso_week = week.astype("Int64").astype(str).str.zfill(2)
    order_date = pd.to_datetime(
        iso_year + "-W" + iso_week + "-1",
        format="%G-W%V-%u",
        errors="coerce",
    )

    ship_lag = {
        "same day": 0,
        "first class": 1,
        "second class": 3,
        "standard class": 5,
    }
    mode = df.get("ship_mode", pd.Series("", index=df.index)).astype(str).str.lower()
    lag = mode.map(ship_lag).fillna(3).astype(int)

    df["order_date"] = order_date
    df["ship_date"] = order_date + pd.to_timedelta(lag, unit="D")
    df["delivery_days"] = lag
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # H3: работаем с копией — не мутируем переданный DataFrame
    df = df.rename(columns=RENAME)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # M2: обрезаем пробелы во всех строковых колонках
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()

    numeric = ["sales", "profit", "quantity", "discount", "shipping_cost", "year", "weeknum"]
    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = repair_dates(df)

    # H2: добавлена order_date в subset — NaT-даты не проходят дальше
    df = df.dropna(subset=["order_id", "sales", "order_date"])
    df = df[df["sales"] > 0]

    # C3: дедупликация
    initial_len = len(df)
    df = df.drop_duplicates()
    if "row_id" in df.columns:
        df = df.drop_duplicates(subset=["row_id"], keep="first")
    dropped = initial_len - len(df)
    if dropped > 0:
        logger.info("Удалено дубликатов: %s", f"{dropped:,}")

    # L1: NaN-прибыль → margin = 0.0 (а не NaN, который пройдёт через dropna в QA)
    df["profit_margin"] = (df["profit"] / df["sales"]).fillna(0.0)
    return df


def load_duckdb(df: pd.DataFrame, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE OR REPLACE TABLE orders AS SELECT * FROM df")
        # M7: формула маржи синхронизирована с Postgres (SUM/SUM вместо AVG)
        con.execute(
            """
            CREATE OR REPLACE VIEW mart_region_year AS
            SELECT
                region,
                country,
                CAST(year AS INTEGER) AS year,
                COUNT(*) AS order_lines,
                SUM(sales) AS revenue,
                SUM(profit) AS profit,
                SUM(profit) / NULLIF(SUM(sales), 0) AS avg_margin
            FROM orders
            GROUP BY 1, 2, 3
            """
        )
    finally:
        con.close()


def load_postgres(df: pd.DataFrame, url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    try:
        # C5: загружаем в staging-таблицу, затем атомарный swap
        df.to_sql(
            "orders_staging",
            engine,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=5000,
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
        logger.info("PostgreSQL: атомарный swap orders завершён")
    finally:
        # M6: освобождаем пул соединений
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--postgres",
        default=None,
        help="postgresql://analyst:analyst@localhost:5432/superstore",
    )
    args = parser.parse_args()

    raw_path = resolve_raw()
    logger.info("Чтение: %s", raw_path)
    df = pd.read_csv(raw_path, encoding="utf-8", low_memory=False)
    logger.info("Строк в сырье: %s", f"{len(df):,}")

    clean_df = clean(df)

    # C4: атомарная запись Parquet (write → temp → rename)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    tmp_parquet = OUT_PARQUET.with_suffix(".tmp.parquet")
    clean_df.to_parquet(tmp_parquet, index=False)
    tmp_parquet.replace(OUT_PARQUET)
    logger.info("Сохранено: %s (%s строк)", OUT_PARQUET, f"{len(clean_df):,}")

    # C2: ловим только duckdb.IOException (блокировка файла) —
    # остальные ошибки пробрасываем наверх
    try:
        load_duckdb(clean_df, DUCKDB_PATH)
        logger.info("DuckDB обновлён: %s", DUCKDB_PATH)
    except duckdb.IOException as exc:
        logger.warning(
            "Файл DuckDB заблокирован (%s). "
            "Закройте Streamlit/Jupyter и повторите ETL. Parquet сохранён.",
            exc,
        )

    from superstore.etl.data_quality import print_report, run_checks

    report = run_checks(clean_df)
    print_report(report)
    if not report.passed:
        raise SystemExit("Проверки качества данных не пройдены")

    if args.postgres:
        load_postgres(clean_df, args.postgres)
        logger.info("Загружено в PostgreSQL, таблица orders")


if __name__ == "__main__":
    main()
