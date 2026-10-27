"""Global Superstore dashboard: where discounts cost money.

Run: streamlit run dashboard/app.py

Every chart is one of the SQL marts in sql/duckdb/marts/, re-run on the filtered rows: the dashboard and
the committed outputs share the same definitions.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from superstore import config  # noqa: E402
from superstore.labels import CATEGORY_RU, MARKET_RU, SEGMENT_RU, SUB_CATEGORY_RU, translate  # noqa: E402
from superstore.warehouse import connect  # noqa: E402

SELECTION_MACRO = """
CREATE OR REPLACE MACRO selection(markets, categories, year_from, year_to) AS TABLE
    SELECT * FROM stg_orders
    WHERE list_contains(markets, market)
      AND list_contains(categories, category)
      AND year BETWEEN year_from AND year_to
"""
SELECTION_CALL = "selection($markets, $categories, $year_from, $year_to)"
GAIN, LOSS = "#2f855a", "#c53030"


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    con = connect(config.PARQUET)
    con.execute(SELECTION_MACRO)
    return con


def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    # A cursor per query: one DuckDB connection is not safe to share across Streamlit threads.
    return get_connection().cursor().execute(sql, params or {}).df()


@st.cache_data
def filter_options() -> tuple[list[str], list[str], int, int]:
    row = query(
        """
        SELECT list(DISTINCT market ORDER BY market) AS markets,
               list(DISTINCT category ORDER BY category) AS categories,
               min(year) AS first_year, max(year) AS last_year
        FROM stg_orders
        """
    ).iloc[0]
    return list(row.markets), list(row.categories), int(row.first_year), int(row.last_year)


def selection_params(selection: tuple) -> dict:
    markets, categories, year_from, year_to = selection
    return {"markets": list(markets), "categories": list(categories), "year_from": year_from, "year_to": year_to}


@st.cache_data
def mart(model: str, selection: tuple) -> pd.DataFrame:
    """Run a mart's SQL on the filtered rows instead of the whole table."""
    sql = (config.SQL_DIR / "marts" / f"{model}.sql").read_text(encoding="utf-8").replace("stg_orders", SELECTION_CALL)
    return query(sql, selection_params(selection))


def usd(value: float) -> str:
    sign = "−" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:,.0f}K"
    return f"{sign}${value:,.0f}"


def render_sidebar() -> tuple:
    markets, categories, first_year, last_year = filter_options()
    st.sidebar.header("Фильтры")
    market_ru = st.sidebar.multiselect(
        "Рынок", [MARKET_RU[m] for m in markets], default=[MARKET_RU[m] for m in markets]
    )
    category_ru = st.sidebar.multiselect(
        "Категория", [CATEGORY_RU[c] for c in categories], default=[CATEGORY_RU[c] for c in categories]
    )
    year_from, year_to = st.sidebar.slider("Годы", first_year, last_year, (first_year, last_year))
    back = {**{v: k for k, v in MARKET_RU.items()}, **{v: k for k, v in CATEGORY_RU.items()}}
    return tuple(back[m] for m in market_ru), tuple(back[c] for c in category_ru), year_from, year_to


def render_kpis(selection: tuple) -> pd.Series:
    kpi = mart("01_kpi_summary", selection).iloc[0]
    if not kpi["order_lines"]:
        st.info("Под фильтры не попала ни одна строка.")
        st.stop()
    cols = st.columns(6)
    cols[0].metric("Выручка", usd(kpi["sales"]))
    cols[1].metric("Прибыль", usd(kpi["profit"]))
    cols[2].metric("Маржа", f"{kpi['margin']:.1%}", help="Прибыль / выручка")
    cols[3].metric("Заказы", f"{int(kpi['orders']):,}".replace(",", " "), help="Order ID + Customer ID")
    cols[4].metric("Средняя скидка", f"{kpi['avg_discount']:.1%}", help="Средняя скидка в строке заказа")
    cols[5].metric("Доля возвратов", f"{kpi['return_rate']:.1%}", help="Доля заказов из листа Returns")
    return kpi


def render_takeaway(kpi: pd.Series) -> None:
    if not kpi["deep_discount_sales_share"]:
        st.info("В выбранном срезе нет строк со скидкой больше 20%.")
        return
    deep_profit = kpi["deep_discount_profit"]
    losses = (
        f" Убыточных строк — {kpi['loss_line_share']:.0%}, "
        f"из них со скидкой — {kpi['loss_lines_discounted_share']:.0%}."
        if kpi["loss_line_share"]
        else ""
    )
    message = (
        f"**Строки со скидкой больше 20%** дают {kpi['deep_discount_sales_share']:.0%} выручки "
        f"и {usd(deep_profit)} прибыли. Остальные строки заработали {usd(kpi['profit'] - deep_profit)}.{losses}"
    )
    st.info(message.replace("$", r"\$"))  # a bare pair of $ signs would render as LaTeX


def render_discounts(selection: tuple) -> None:
    bands = mart("05_discount_bands", selection)
    fig = go.Figure(
        go.Bar(
            x=bands["discount_band"],
            y=bands["margin"],
            marker_color=[GAIN if m >= 0 else LOSS for m in bands["margin"]],
            error_y={
                "type": "data",
                "symmetric": False,
                "array": bands["margin_ci_high"] - bands["margin"],
                "arrayminus": bands["margin"] - bands["margin_ci_low"],
            },
            customdata=bands[["sales_share", "lines"]],
            hovertemplate=(
                "Маржа %{y:.1%}<br>Доля выручки %{customdata[0]:.1%}<br>Строк %{customdata[1]:,}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Маржа по уровню скидки (95% доверительный интервал)",
        yaxis_tickformat=".0%",
        xaxis_title="Скидка в строке",
        yaxis_title="Маржа",
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Маржа = прибыль / выручка группы строк. Интервал — 95% по линеаризации отношения сумм. "
        "Связь описательная: скидки назначались не случайно."
    )


def render_subcategories(selection: tuple) -> None:
    cells = mart("07_subcategory_band", selection)
    cells["sub_category"] = translate(cells["sub_category"], SUB_CATEGORY_RU)
    order = cells.drop_duplicates("discount_band").sort_values("discount_band_order")["discount_band"].tolist()
    pivot = cells.pivot(index="sub_category", columns="discount_band", values="margin").reindex(columns=order)
    pivot = pivot.loc[pivot.mean(axis=1).sort_values().index]
    fig = px.imshow(
        pivot.clip(-1, 1),
        color_continuous_scale="RdYlGn",
        zmin=-1,
        zmax=1,
        aspect="auto",
        text_auto=".0%",
        labels={"color": "Маржа", "x": "Скидка", "y": ""},
        title="Маржа по подкатегориям и уровням скидки",
    )
    fig.update_layout(height=620, coloraxis_colorbar_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    worst = mart("06_subcategory_discount", selection).head(8)
    worst["sub_category"] = translate(worst["sub_category"], SUB_CATEGORY_RU)
    st.subheader("Где глубокие скидки стоят дороже всего")
    st.dataframe(
        worst[["sub_category", "sales", "margin", "deep_discount_sales_share", "deep_discount_profit", "other_profit"]],
        hide_index=True,
        width="stretch",
        column_config={
            "sub_category": "Подкатегория",
            "sales": st.column_config.NumberColumn("Выручка", format="dollar"),
            "margin": st.column_config.NumberColumn("Маржа", format="percent"),
            "deep_discount_sales_share": st.column_config.NumberColumn(
                "Доля выручки со скидкой > 20%", format="percent"
            ),
            "deep_discount_profit": st.column_config.NumberColumn("Прибыль строк со скидкой > 20%", format="dollar"),
            "other_profit": st.column_config.NumberColumn("Прибыль остальных строк", format="dollar"),
        },
    )


def render_markets(selection: tuple) -> None:
    markets = mart("04_market_discount", selection)
    markets["market_ru"] = translate(markets["market"], MARKET_RU)
    fig = px.scatter(
        markets,
        x="avg_discount",
        y="margin",
        size="sales",
        text="market_ru",
        title="Средняя скидка и маржа по рынкам (размер — выручка)",
        labels={"avg_discount": "Средняя скидка", "margin": "Маржа", "sales": "Выручка"},
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    segments = query(
        f"SELECT segment, sum(sales) AS sales, sum(profit) AS profit FROM {SELECTION_CALL} GROUP BY 1 ORDER BY 3 DESC",
        selection_params(selection),
    )
    segments["segment"] = translate(segments["segment"], SEGMENT_RU)
    st.plotly_chart(
        px.bar(
            segments, x="segment", y="profit", title="Прибыль по сегментам", labels={"segment": "", "profit": "Прибыль"}
        ),
        width="stretch",
    )


def render_trend(selection: tuple) -> None:
    monthly = mart("02_monthly_sales", selection)
    fig = px.line(
        monthly,
        x="month",
        y=["sales", "profit"],
        markers=True,
        title="Помесячная выручка и прибыль",
        labels={"month": "Месяц", "value": "USD", "variable": ""},
    )
    fig.for_each_trace(lambda t: t.update(name={"sales": "Выручка", "profit": "Прибыль"}[t.name]))
    st.plotly_chart(fig, width="stretch")


def main() -> None:
    st.set_page_config(page_title="Global Superstore: скидки и прибыль", layout="wide")
    st.title("Global Superstore: где скидки съедают прибыль")
    st.caption("51 290 строк заказов, 2011–2014 · данные Tableau Global Superstore · все суммы в USD")

    selection = render_sidebar()
    if not selection[0] or not selection[1]:
        st.info("Выберите хотя бы один рынок и одну категорию.")
        st.stop()
    kpi = render_kpis(selection)
    render_takeaway(kpi)

    tabs = st.tabs(["Скидки", "Подкатегории", "Рынки и сегменты", "Динамика"])
    with tabs[0]:
        render_discounts(selection)
    with tabs[1]:
        render_subcategories(selection)
    with tabs[2]:
        render_markets(selection)
    with tabs[3]:
        render_trend(selection)


if __name__ == "__main__":
    main()
