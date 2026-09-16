"""pytest: ETL и качество данных."""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "processed" / "orders_clean.parquet"


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    """Загрузка реальных данных (пропуск, если ETL не запускался)."""
    if not PARQUET.exists():
        pytest.skip("Сначала запустите ETL")
    return pd.read_parquet(PARQUET)


@pytest.fixture()
def sample_raw_df() -> pd.DataFrame:
    """Синтетический DataFrame для unit-тестов, не зависящих от реальных данных."""
    return pd.DataFrame(
        {
            "Order ID": [
                "CA-2012-1001",
                "CA-2012-1001",  # дубликат
                "CA-2013-2002",
                "MX-2014-3003",
            ],
            "Row ID": [1, 1, 2, 3],  # row_id=1 дублируется
            "Sales": ["100.5", "100.5", "50.0", "200.0"],
            "Profit": ["20.1", "20.1", "-5.0", "30.0"],
            "year": [2012, 2012, 2013, 2014],
            "weeknum": [10, 10, 15, None],  # None → fallback 26
            "Ship Mode": [
                "First Class",
                "First Class",
                "Standard Class",
                "Same Day",
            ],
            "region": ["West", "West", "East", "Central"],
            "category": ["Technology", "Technology", "Furniture", "Office Supplies"],
            "segment": ["Consumer", "Consumer", "Corporate", "Home Office"],
            "country": ["US", "US", "US", "MX"],
        }
    )


# ---------------------------------------------------------------------------
# Интеграционные тесты (на реальных данных)
# ---------------------------------------------------------------------------

def test_row_count(df: pd.DataFrame) -> None:
    assert len(df) > 50_000


def test_required_columns(df: pd.DataFrame) -> None:
    required = {
        "order_id",
        "sales",
        "profit",
        "region",
        "category",
        "order_date",
        "profit_margin",
    }
    assert required.issubset(df.columns)


def test_revenue_positive(df: pd.DataFrame) -> None:
    assert (df["sales"] > 0).all()


def test_quality_module(df: pd.DataFrame) -> None:
    from superstore.etl.data_quality import run_checks

    report = run_checks(df)
    assert report.passed


# ---------------------------------------------------------------------------
# Unit-тесты на синтетике (H6)
# ---------------------------------------------------------------------------

def test_clean_removes_duplicates(sample_raw_df: pd.DataFrame) -> None:
    """C3: дедупликация должна убрать полный дубликат строки."""
    from superstore.etl.load_and_clean import clean

    result = clean(sample_raw_df)
    assert len(result) == 3, f"Ожидалось 3 строки после дедупликации, получено {len(result)}"


def test_clean_produces_required_columns(sample_raw_df: pd.DataFrame) -> None:
    """clean() должна создать order_date, ship_date, delivery_days, profit_margin."""
    from superstore.etl.load_and_clean import clean

    result = clean(sample_raw_df)
    for col in ("order_date", "ship_date", "delivery_days", "profit_margin"):
        assert col in result.columns, f"Колонка {col} отсутствует"


def test_clean_no_nat_dates(sample_raw_df: pd.DataFrame) -> None:
    """H2: после clean() не должно быть NaT в order_date."""
    from superstore.etl.load_and_clean import clean

    result = clean(sample_raw_df)
    assert result["order_date"].notna().all(), "Обнаружены NaT-даты"


def test_clean_does_not_mutate_input(sample_raw_df: pd.DataFrame) -> None:
    """H3: clean() не должна мутировать входной DataFrame."""
    from superstore.etl.load_and_clean import clean

    original_cols = list(sample_raw_df.columns)
    original_len = len(sample_raw_df)
    _ = clean(sample_raw_df)

    assert list(sample_raw_df.columns) == original_cols, "Входной DF был мутирован (колонки)"
    assert len(sample_raw_df) == original_len, "Входной DF был мутирован (строки)"


def test_clean_profit_margin_no_nan(sample_raw_df: pd.DataFrame) -> None:
    """L1: profit_margin не должен быть NaN."""
    from superstore.etl.load_and_clean import clean

    result = clean(sample_raw_df)
    assert result["profit_margin"].notna().all(), "Обнаружены NaN в profit_margin"


def test_clean_strips_whitespace() -> None:
    """M2: clean() должна убирать пробелы в строковых колонках."""
    from superstore.etl.load_and_clean import clean

    df = pd.DataFrame(
        {
            "Order ID": ["CA-2012-1001"],
            "Row ID": [1],
            "Sales": ["100.0"],
            "Profit": ["10.0"],
            "year": [2012],
            "weeknum": [10],
            "Ship Mode": ["  First Class  "],
            "region": [" West "],
            "category": ["Technology "],
            "segment": ["Consumer"],
            "country": ["US"],
        }
    )
    result = clean(df)
    assert result["region"].iloc[0] == "West"
    assert result["ship_mode"].iloc[0] == "First Class"
