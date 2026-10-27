"""ETL: the raw Global Superstore workbook (or a CSV export of its Orders sheet) -> cleaned Parquet.

Run: python -m superstore.etl.load_and_clean [--raw PATH]

Nothing is reconstructed or silently dropped: dates must be real dates, and every row that reaches
the Parquet file passes the data quality gate first (superstore.etl.data_quality).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from superstore import config
from superstore.etl.data_quality import print_report, run_checks

log = logging.getLogger(__name__)

# Raw header -> column name. Postal Code is left out: it is empty for 80% of rows (non-US orders).
COLUMNS: dict[str, str] = {
    "Row ID": "row_id",
    "Order ID": "order_id",
    "Order Date": "order_date",
    "Ship Date": "ship_date",
    "Ship Mode": "ship_mode",
    "Customer ID": "customer_id",
    "Customer Name": "customer_name",
    "Segment": "segment",
    "City": "city",
    "State": "state",
    "Country": "country",
    "Market": "market",
    "Region": "region",
    "Product ID": "product_id",
    "Category": "category",
    "Sub-Category": "sub_category",
    "Product Name": "product_name",
    "Sales": "sales",
    "Quantity": "quantity",
    "Discount": "discount",
    "Profit": "profit",
    "Shipping Cost": "shipping_cost",
    "Order Priority": "order_priority",
}
NUMERIC = ["row_id", "sales", "quantity", "discount", "profit", "shipping_cost"]
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y")

# The Returns sheet spells the US market out in full; the Orders sheet uses "US".
RETURNS_MARKET_ALIASES = {"United States": "US"}


class RawDataError(ValueError):
    """The raw file does not have the expected structure or contains values that are not data."""


def find_raw(raw_dir: Path = config.RAW_DIR) -> Path:
    for pattern in ("*.xls", "*.xlsx", "*.csv"):
        if found := sorted(raw_dir.glob(pattern)):
            return found[0]
    raise FileNotFoundError(f"No raw file in {raw_dir}. Download the dataset as described in README, section «Данные».")


def read_raw(path: Path) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Return (orders, returns). A CSV has no Returns sheet, so returns is None."""
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, low_memory=False), None
    sheets = pd.read_excel(path, sheet_name=None, engine="calamine")
    if "Orders" not in sheets:
        raise RawDataError(f"{path.name}: no 'Orders' sheet (found {list(sheets)})")
    return sheets["Orders"], sheets.get("Returns")


def parse_dates(s: pd.Series, name: str) -> pd.Series:
    """Parse a date column without guessing: the whole column must match one known format."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s.astype("datetime64[ns]").dt.normalize()
    text = s.astype("string").str.strip()
    for fmt in DATE_FORMATS:
        parsed = pd.to_datetime(text, format=fmt, errors="coerce")
        if parsed.notna().all():
            return parsed.astype("datetime64[ns]")
    bad = text[pd.to_datetime(text, format=DATE_FORMATS[0], errors="coerce").isna()]
    raise RawDataError(
        f"{name}: {len(bad):,} values are not dates (e.g. {bad.iloc[0]!r}). "
        "Excel exports sometimes break dates into '00:00.0'; use the original workbook instead."
    )


def returned_orders(returns: pd.DataFrame) -> pd.DataFrame:
    """Distinct (order_id, market) pairs marked as returned."""
    out = returns.rename(columns={"Order ID": "order_id", "Market": "market", "Returned": "returned"})
    out = out[out["returned"].astype("string").str.strip().str.lower() == "yes"]
    out["order_id"] = out["order_id"].astype("string").str.strip()
    out["market"] = out["market"].astype("string").str.strip().replace(RETURNS_MARKET_ALIASES)
    return out[["order_id", "market"]].drop_duplicates()


def clean(orders: pd.DataFrame, returns: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rename, type and enrich the Orders sheet. The input frame is not modified."""
    if missing := [c for c in COLUMNS if c not in orders.columns]:
        raise RawDataError(f"Missing columns: {missing}")
    df = orders[list(COLUMNS)].rename(columns=COLUMNS)

    for col in df.columns.difference(NUMERIC + ["order_date", "ship_date"]):
        df[col] = df[col].astype("string").str.strip()
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["quantity"] = df["quantity"].astype("Int64")
    df["row_id"] = df["row_id"].astype("Int64")
    df["order_date"] = parse_dates(df["order_date"], "Order Date")
    df["ship_date"] = parse_dates(df["ship_date"], "Ship Date")

    n_before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    if dropped := n_before - len(df):
        log.info("Dropped %d exact duplicate rows", dropped)

    if returns is None:
        df["is_returned"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    else:
        flagged = returned_orders(returns).assign(is_returned=True)
        df = df.merge(flagged, on=["order_id", "market"], how="left")  # pairs are distinct: no fan-out
        df["is_returned"] = df["is_returned"].notna().astype("boolean")

    # Order ID repeats across countries and customers in this dataset; Order ID + Customer ID identifies an order.
    df["order_key"] = df["order_id"] + "|" + df["customer_id"]
    df["year"] = df["order_date"].dt.year.astype("Int64")
    df["delivery_days"] = (df["ship_date"] - df["order_date"]).dt.days.astype("Int64")
    df["profit_margin"] = df["profit"] / df["sales"]
    return df


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.parquet")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)  # readers never see a half-written file


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Global Superstore ETL: raw workbook -> cleaned Parquet")
    parser.add_argument("--raw", type=Path, default=None, help="raw .xls/.xlsx/.csv (default: first file in data/raw)")
    parser.add_argument("--out", type=Path, default=config.PARQUET)
    parser.add_argument("--min-rows", type=int, default=50_000, help="row count the quality gate expects")
    args = parser.parse_args(argv)

    raw_path = args.raw or find_raw()
    log.info("Reading %s", raw_path)
    orders, returns = read_raw(raw_path)
    df = clean(orders, returns)

    report = run_checks(df, min_rows=args.min_rows)
    print_report(report)
    if not report.passed:
        raise SystemExit("Data quality checks failed; Parquet was not written")

    write_parquet(df, args.out)
    log.info("Wrote %s (%s rows, %s orders)", args.out, f"{len(df):,}", f"{df['order_key'].nunique():,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
