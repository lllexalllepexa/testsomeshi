"""End-to-end: the committed Parquet passes the gate, and the committed outputs equal a fresh run.
All writes go to pytest tmp dirs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from superstore import config
from superstore.pipeline import main as run_pipeline
from superstore.warehouse import MARTS

STATS = ["stats_discount_ttest", "stats_margin_model", "stats_margin_model_info"]
FIGURES = [
    "discount_margin.png",
    "subcategory_discount_heatmap.png",
    "market_discount.png",
    "monthly_sales.png",
    "margin_model_residuals.png",
]


@pytest.fixture(scope="module")
def full_run(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("run")
    dirs = {"outputs": root / "outputs", "figures": root / "figures", "database": root / "superstore.duckdb"}
    assert (
        run_pipeline(
            [
                f"--outputs-dir={dirs['outputs']}",
                f"--figures-dir={dirs['figures']}",
                f"--database={dirs['database']}",
            ]
        )
        == 0
    )
    return dirs


def test_pipeline_writes_outputs_and_figures(full_run):
    for name in [*MARTS, *STATS]:
        assert not pd.read_csv(full_run["outputs"] / f"{name}.csv").empty, name
    for figure in FIGURES:
        assert (full_run["figures"] / figure).stat().st_size > 0, figure
    assert full_run["database"].exists()


@pytest.mark.parametrize("name", [*MARTS, *STATS])
def test_committed_outputs_match_fresh_run(full_run, name):
    committed = pd.read_csv(config.OUTPUTS_DIR / f"{name}.csv")
    fresh = pd.read_csv(full_run["outputs"] / f"{name}.csv")
    pd.testing.assert_frame_equal(committed, fresh, check_exact=False, rtol=1e-6)


def test_committed_parquet_matches_readme_totals():
    df = pd.read_parquet(config.PARQUET)
    assert len(df) == 51_290
    assert df["order_key"].nunique() == 25_753
    assert round(df["sales"].sum(), 2) == 12_642_501.91
    assert round(df["profit"].sum(), 2) == 1_467_457.29


def test_validate_step_rejects_bad_parquet(tmp_path, clean_df):
    path = tmp_path / "bad.parquet"
    clean_df.assign(sales=-1.0).to_parquet(path)
    with pytest.raises(SystemExit, match="sales_positive"):
        run_pipeline(["--step", "validate", f"--parquet={path}"])
