"""ETL: structure checks, real dates only, returns join, no input mutation."""

from __future__ import annotations

import pandas as pd
import pytest

from superstore.etl.load_and_clean import RawDataError, clean, find_raw, main, read_raw


def test_clean_fixture(clean_df):
    assert len(clean_df) == 9  # the exact duplicate of line 3 is dropped
    assert clean_df["row_id"].is_unique
    assert clean_df["order_key"].nunique() == 6  # O-5 belongs to two customers -> two orders
    line = clean_df.set_index("row_id")
    assert line.loc[1, "delivery_days"] == 4
    assert line.loc[6, "delivery_days"] == 3  # 2013-12-30 -> 2014-01-02 across the year boundary
    assert line.loc[6, "year"] == 2013
    assert line.loc[3, "profit_margin"] == pytest.approx(-0.4)


def test_returns_join_normalizes_market(clean_df):
    returned = set(clean_df.loc[clean_df["is_returned"], "row_id"])
    # O-2/EU directly; O-4 is listed under "United States" in the Returns sheet but "US" in Orders
    assert returned == {3, 6, 7}


def test_without_returns_flag_is_unknown(raw_orders):
    df = clean(raw_orders)
    assert df["is_returned"].isna().all()


def test_clean_does_not_mutate_input(raw_orders, raw_returns):
    before = raw_orders.copy()
    clean(raw_orders, raw_returns)
    pd.testing.assert_frame_equal(raw_orders, before)


def test_broken_excel_dates_are_rejected(raw_orders):
    raw_orders["Order Date"] = "00:00.0"
    with pytest.raises(RawDataError, match="not dates"):
        clean(raw_orders)


def test_day_first_dates_are_parsed(raw_orders):
    raw_orders["Order Date"] = pd.to_datetime(raw_orders["Order Date"]).dt.strftime("%d-%m-%Y")
    df = clean(raw_orders)
    assert df.set_index("row_id").loc[1, "order_date"] == pd.Timestamp("2012-01-10")


def test_missing_column_is_rejected(raw_orders):
    with pytest.raises(RawDataError, match="Sales"):
        clean(raw_orders.drop(columns="Sales"))


def test_xlsx_with_returns_sheet_matches_csv(tmp_path, raw_orders, raw_returns, clean_df):
    path = tmp_path / "Global Superstore.xlsx"
    with pd.ExcelWriter(path) as writer:
        raw_orders.to_excel(writer, sheet_name="Orders", index=False)
        raw_returns.to_excel(writer, sheet_name="Returns", index=False)
    orders, returns = read_raw(path)
    pd.testing.assert_frame_equal(clean(orders, returns), clean_df, check_dtype=False)


def test_find_raw(tmp_path):
    with pytest.raises(FileNotFoundError, match="Данные"):
        find_raw(tmp_path)
    (tmp_path / "export.csv").write_text("x")
    assert find_raw(tmp_path).name == "export.csv"


def test_main_writes_parquet_only_when_quality_passes(tmp_path):
    from tests.conftest import FIXTURES

    out = tmp_path / "orders_clean.parquet"
    with pytest.raises(SystemExit, match="Data quality"):
        main(["--raw", str(FIXTURES / "orders.csv"), "--out", str(out)])  # 9 rows < 50,000
    assert not out.exists()

    assert main(["--raw", str(FIXTURES / "orders.csv"), "--out", str(out), "--min-rows", "5"]) == 0
    assert len(pd.read_parquet(out)) == 9
