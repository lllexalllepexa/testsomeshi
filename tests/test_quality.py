"""Every data quality check passes on clean data and fires on an injected defect."""

from __future__ import annotations

import pandas as pd
import pytest

from superstore.etl.data_quality import run_checks


def test_fixture_passes(clean_df):
    report = run_checks(clean_df, min_rows=5)
    assert report.passed, report.failures


def test_row_count_uses_threshold(clean_df):
    assert run_checks(clean_df).failures == ["row_count"]  # default expects the full 51k-row dataset


@pytest.mark.parametrize(
    ("column", "value", "check"),
    [
        ("sales", 0.0, "sales_positive"),
        ("quantity", 0, "quantity_positive"),
        ("discount", 1.0, "discount_range"),
        ("discount", -0.1, "discount_range"),
        ("ship_date", pd.Timestamp("2011-12-31"), "ship_after_order"),
        ("order_date", pd.Timestamp("2010-06-01"), "years_in_range"),
        ("customer_id", pd.NA, "required_not_null"),
        ("market", "Mars", "valid_market"),
        ("sub_category", "Gadgets", "valid_sub_category"),
        ("region", "Atlantis", "valid_region"),
        ("ship_mode", "Teleport", "valid_ship_mode"),
    ],
)
def test_defect_is_detected(clean_df, column, value, check):
    clean_df.loc[0, column] = value
    report = run_checks(clean_df, min_rows=5)
    assert check in report.failures


def test_duplicate_row_id_is_detected(clean_df):
    clean_df.loc[1, "row_id"] = clean_df.loc[0, "row_id"]
    assert "row_id_unique" in run_checks(clean_df, min_rows=5).failures
