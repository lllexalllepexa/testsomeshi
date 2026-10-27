"""PostgreSQL load against a real server (embedded via pgserver; skipped when it is not installed)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from superstore.loaders.load_postgres import load

pgserver = pytest.importorskip("pgserver")


@pytest.fixture(scope="module")
def pg_url(tmp_path_factory) -> str:
    server = pgserver.get_server(tmp_path_factory.mktemp("pg"), cleanup_mode="stop")
    yield server.get_uri().replace("postgresql://", "postgresql+psycopg2://")
    server.cleanup()


def test_load_is_repeatable_and_keeps_schema_and_views(pg_url, clean_df):
    assert load(clean_df, pg_url) == 9
    assert load(clean_df, pg_url) == 9  # a second load replaces rows; the views on `orders` survive
    engine = create_engine(pg_url)
    try:
        with engine.connect() as conn:
            types = dict(
                conn.execute(
                    text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = 'orders' AND column_name IN ('sales', 'order_date', 'is_returned')"
                    )
                ).fetchall()
            )
            bands = conn.execute(text("SELECT count(*), sum(sales) FROM mart_discount_bands")).one()
            east = (
                conn.execute(text("SELECT sales FROM mart_region_year WHERE region = 'East' ORDER BY year"))
                .scalars()
                .all()
            )
            leftovers = conn.execute(text("SELECT to_regclass('orders_staging')")).scalar()
    finally:
        engine.dispose()
    assert types == {"sales": "numeric", "order_date": "date", "is_returned": "boolean"}
    assert (bands[0], float(bands[1])) == (6, 970.0)
    assert [float(s) for s in east] == [150.0, 100.0]
    assert leftovers is None
