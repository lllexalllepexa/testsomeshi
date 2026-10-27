"""Shared fixtures. tests/fixtures/ holds 10 hand-written order lines (one exact duplicate) and 2 returns,
small enough to check every mart by hand:

line  order  customer  market  region     month    sub-category  sales  profit  discount
1     O-1    C1        US      East       2012-01  Phones          100      30   0
2     O-1    C1        US      East       2012-01  Paper            50      10   0
3     O-2    C2        EU      Central    2012-02  Tables          200     -80   0.40   returned
4     O-3    C3        APAC    Oceania    2013-03  Chairs          100      15   0.10
5     O-3    C3        APAC    Oceania    2013-03  Phones          100       5   0.20
6     O-4    C1        US      East       2013-12  Binders          40     -60   0.70   returned ("United States")
7     O-4    C1        US      East       2013-12  Paper            60      15   0      returned ("United States")
8     O-5    C4        EU      North      2014-06  Phones          300     -10   0.25
9     O-5    C5        LATAM   Caribbean  2014-07  Paper            20       5   0      (same Order ID, other customer)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from superstore.etl.load_and_clean import clean, write_parquet
from superstore.warehouse import build_marts, connect

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_orders() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "orders.csv")


@pytest.fixture
def raw_returns() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "returns.csv")


@pytest.fixture
def clean_df(raw_orders, raw_returns) -> pd.DataFrame:
    return clean(raw_orders, raw_returns)


@pytest.fixture
def fixture_parquet(tmp_path, clean_df) -> Path:
    path = tmp_path / "orders_clean.parquet"
    write_parquet(clean_df, path)
    return path


@pytest.fixture
def marts(fixture_parquet) -> dict[str, pd.DataFrame]:
    con = connect(fixture_parquet)
    try:
        return build_marts(con)
    finally:
        con.close()
