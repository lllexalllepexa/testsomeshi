"""Mart values on the hand-checkable fixture (see conftest for the 9 lines)."""

from __future__ import annotations

import math

import pandas as pd
import pytest


def records(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    return df[columns].to_dict("records")


def test_kpi_summary(marts):
    kpi = marts["01_kpi_summary"].iloc[0]
    assert (kpi["order_lines"], kpi["orders"], kpi["customers"]) == (9, 6, 5)
    assert (kpi["sales"], kpi["profit"], kpi["margin"]) == (970.0, -70.0, -0.0722)
    assert kpi["avg_discount"] == 0.1833  # 1.65 / 9
    assert kpi["return_rate"] == 0.3333  # O-2|C2 and O-4|C1 out of 6 orders
    assert (kpi["loss_line_share"], kpi["loss_lines_discounted_share"], kpi["loss_lines_profit"]) == (
        0.3333,
        1.0,
        -150.0,
    )
    assert (kpi["deep_discount_sales_share"], kpi["deep_discount_profit"]) == (0.5567, -150.0)  # lines 3, 6, 8


def test_monthly_sales_has_no_false_year_over_year(marts):
    df = marts["02_monthly_sales"]
    assert records(df, ["month", "orders", "sales", "profit"]) == [
        {"month": "2012-01", "orders": 1, "sales": 150.0, "profit": 40.0},
        {"month": "2012-02", "orders": 1, "sales": 200.0, "profit": -80.0},
        {"month": "2013-03", "orders": 1, "sales": 200.0, "profit": 20.0},
        {"month": "2013-12", "orders": 1, "sales": 100.0, "profit": -45.0},
        {"month": "2014-06", "orders": 1, "sales": 300.0, "profit": -10.0},
        {"month": "2014-07", "orders": 1, "sales": 20.0, "profit": 5.0},
    ]
    assert df["sales_yoy"].isna().all()  # no month has the same month a year earlier


def test_region_year_growth_and_cumulative_share(marts):
    east = marts["03_region_year"].query("region == 'East'").reset_index(drop=True)
    assert east["year"].tolist() == [2012, 2013]
    assert east["sales"].tolist() == [150.0, 100.0]
    assert pd.isna(east.loc[0, "sales_yoy"])
    assert east.loc[1, "sales_yoy"] == -0.3333  # 100 / 150 - 1
    assert east["cumulative_share"].tolist() == [0.6, 1.0]  # 150 / 250, then 250 / 250
    # one row per region and year, and every region ends at 100% of its own sales
    df = marts["03_region_year"]
    assert not df.duplicated(["region", "year"]).any()
    assert (df.groupby("region")["cumulative_share"].last() == 1.0).all()


def test_market_discount(marts):
    df = marts["04_market_discount"]
    columns = ["market", "sales", "profit", "margin", "deep_discount_sales_share", "deep_discount_profit"]
    assert df[columns].values.tolist() == [  # sorted from the lowest margin
        ["EU", 500.0, -90.0, -0.18, 1.0, -90.0],
        ["US", 250.0, -5.0, -0.02, 0.16, -60.0],
        ["APAC", 200.0, 20.0, 0.1, 0.0, 0.0],
        ["LATAM", 20.0, 5.0, 0.25, 0.0, 0.0],
    ]


def test_discount_bands(marts, clean_df):
    df = marts["05_discount_bands"]
    assert records(df, ["discount_band", "lines", "sales", "profit", "margin"]) == [
        {"discount_band": "0%", "lines": 4, "sales": 230.0, "profit": 60.0, "margin": 0.2609},
        {"discount_band": "1–10%", "lines": 1, "sales": 100.0, "profit": 15.0, "margin": 0.15},
        {"discount_band": "11–20%", "lines": 1, "sales": 100.0, "profit": 5.0, "margin": 0.05},
        {"discount_band": "21–30%", "lines": 1, "sales": 300.0, "profit": -10.0, "margin": -0.0333},
        {"discount_band": "31–50%", "lines": 1, "sales": 200.0, "profit": -80.0, "margin": -0.4},
        {"discount_band": ">50%", "lines": 1, "sales": 40.0, "profit": -60.0, "margin": -1.5},
    ]
    assert df["sales_share"].sum() == pytest.approx(1.0, abs=1e-3)

    # 95% CI of a ratio estimator, computed independently from the raw lines of the 0% band
    base = clean_df[clean_df["discount"] == 0]
    r = base["profit"].sum() / base["sales"].sum()
    n = len(base)
    se = math.sqrt(((base["profit"] - r * base["sales"]) ** 2).sum() / (n * (n - 1))) / base["sales"].mean()
    row = df.set_index("discount_band").loc["0%"]
    assert (row["margin_ci_low"], row["margin_ci_high"]) == pytest.approx((r - 1.96 * se, r + 1.96 * se), abs=1e-4)
    assert df.set_index("discount_band").loc[">50%", ["margin_ci_low", "margin_ci_high"]].isna().all()  # n = 1


def test_subcategory_discount(marts):
    df = marts["06_subcategory_discount"]
    assert df["sub_category"].tolist() == ["Tables", "Binders", "Phones", "Chairs", "Paper"]
    phones = df.set_index("sub_category").loc["Phones"]
    assert (phones["sales"], phones["profit"], phones["deep_discount_sales_share"]) == (500.0, 25.0, 0.6)
    assert (phones["deep_discount_profit"], phones["other_profit"]) == (-10.0, 35.0)
    assert (df["deep_discount_profit"] + df["other_profit"]).tolist() == df["profit"].tolist()


def test_subcategory_band_flags_small_cells(marts):
    df = marts["07_subcategory_band"]
    assert len(df) == 7
    assert df["small_sample"].all()
    paper = df.query("sub_category == 'Paper'").iloc[0]
    assert (paper["discount_band"], paper["lines"], paper["sales"], paper["profit"]) == ("0%", 3, 130.0, 30.0)


def test_marts_reconcile(marts):
    total = marts["01_kpi_summary"].iloc[0]["sales"]
    for model in (
        "02_monthly_sales",
        "03_region_year",
        "04_market_discount",
        "05_discount_bands",
        "06_subcategory_discount",
    ):
        assert marts[model]["sales"].sum() == pytest.approx(total), model
