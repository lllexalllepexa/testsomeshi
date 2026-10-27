"""The dashboard renders against the fixture and its KPIs follow the filters."""

from __future__ import annotations

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from superstore import config

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")


@pytest.fixture
def app(fixture_parquet, monkeypatch) -> AppTest:
    monkeypatch.setattr(config, "PARQUET", fixture_parquet)
    st.cache_resource.clear()  # never reuse a connection opened on another test's data
    st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    yield at
    st.cache_resource.clear()
    st.cache_data.clear()


def metric(at: AppTest, label: str) -> str:
    return next(m.value for m in at.metric if m.label == label)


def test_dashboard_renders_fixture_kpis(app):
    assert not app.exception
    assert metric(app, "Выручка") == "$970"
    assert metric(app, "Прибыль") == "−$70"
    assert metric(app, "Заказы") == "6"
    assert metric(app, "Доля возвратов") == "33.3%"
    assert "56% выручки" in app.info[0].value  # deep-discount lines: 540 / 970


def test_market_filter(app):
    app.sidebar.multiselect[0].set_value(["США"]).run()
    assert not app.exception
    assert metric(app, "Выручка") == "$250"
    assert metric(app, "Заказы") == "2"


def test_selection_without_deep_discounts(app):
    app.sidebar.multiselect[0].set_value(["Латинская Америка"]).run()
    assert not app.exception
    assert "нет строк со скидкой больше 20%" in app.info[0].value


def test_empty_selection_shows_hint(app):
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert "хотя бы один рынок" in app.info[0].value
