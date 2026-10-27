"""Statistics: the margin model recovers known effects; the Welch table reports effect sizes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from superstore.analysis.stats_models import (
    BAND_ORDER,
    discount_profit_test,
    fit_margin_model,
    margin_model_tables,
)

TRUE_BAND_EFFECTS = {"0%": 0.0, "1–10%": -0.05, "11–20%": -0.15, "21–30%": -0.3, "31–50%": -0.6, ">50%": -1.4}


@pytest.fixture
def synthetic() -> pd.DataFrame:
    """Margins built from known band, sub-category and market effects plus small noise."""
    rng = np.random.default_rng(0)
    n = 1200
    df = pd.DataFrame(
        {
            "discount_band": np.tile(BAND_ORDER, n // len(BAND_ORDER)),
            "sub_category": rng.choice(["Chairs", "Paper", "Phones"], n),
            "market": rng.choice(["EU", "US"], n),
        }
    )
    sub = df["sub_category"].map({"Chairs": 0.0, "Paper": 0.05, "Phones": -0.02})
    market = df["market"].map({"EU": 0.0, "US": 0.03})
    df["profit_margin"] = 0.25 + df["discount_band"].map(TRUE_BAND_EFFECTS) + sub + market + rng.normal(0, 0.01, n)
    return df


def test_margin_model_recovers_band_effects(synthetic):
    coefs, info = margin_model_tables(fit_margin_model(synthetic))
    assert coefs["discount_band"].tolist() == BAND_ORDER
    estimated = dict(zip(coefs["discount_band"], coefs["coef"], strict=True))
    assert estimated == pytest.approx(TRUE_BAND_EFFECTS, abs=0.005)
    bands = coefs.iloc[1:]  # the reference band is fixed at 0
    assert ((bands["ci_low"] < bands["coef"]) & (bands["coef"] < bands["ci_high"]) & (bands["se"] > 0)).all()
    # every estimate within 4 robust standard errors of the truth
    assert ((bands["coef"] - bands["discount_band"].map(TRUE_BAND_EFFECTS)).abs() < 4 * bands["se"]).all()
    assert info.loc[0, "cov_type"] == "HC3"
    assert info.loc[0, "n"] == len(synthetic)
    assert info.loc[0, "r2"] > 0.99


def test_model_excludes_shipping_cost(synthetic):
    # shipping cost is computed from the order value; including it would leak the outcome
    assert "shipping_cost" not in fit_margin_model(synthetic).model.formula


def test_discount_profit_test_reports_effect_with_ci():
    df = pd.DataFrame(
        {
            "category": ["A"] * 7 + ["B"] * 7,
            "discount": [0, 0, 0, 0.2, 0.2, 0.2, 0.2] * 2,
            "profit": [10, 20, 30, -10, 0, 10, 20, 50, 60, 70, 0, 5, 10, 15],
        }
    )
    table = discount_profit_test(df).set_index("group")
    assert table.index.tolist() == ["all", "A", "B"]
    a = table.loc["A"]
    assert (a["mean_profit_no_discount"], a["mean_profit_discount"], a["mean_diff"]) == (20.0, 5.0, -15.0)
    assert a["median_diff"] == -15.0
    assert a["ci_low"] < a["mean_diff"] < a["ci_high"]
    assert table.loc["B", "mean_diff"] == -52.5  # 7.5 - 60
