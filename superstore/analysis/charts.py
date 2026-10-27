"""Static charts for the README, drawn from the mart tables (outputs/*.csv)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: CI, containers, Airflow workers

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from superstore.labels import MARKET_RU, SUB_CATEGORY_RU  # noqa: E402

GAIN, LOSS, NEUTRAL = "#2f855a", "#c53030", "#4a5568"
USD_K = mtick.FuncFormatter(lambda x, _: f"${x / 1000:,.0f}K")


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def discount_margin(bands: pd.DataFrame, path: Path) -> Path:
    """Margin by discount band with 95% CIs; labels show each band's share of sales."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    colors = [GAIN if m >= 0 else LOSS for m in bands["margin"]]
    err = np.vstack([bands["margin"] - bands["margin_ci_low"], bands["margin_ci_high"] - bands["margin"]])
    ax.bar(bands["discount_band"], bands["margin"], color=colors, yerr=err, capsize=4, ecolor=NEUTRAL)
    for x, (m, share) in enumerate(zip(bands["margin"], bands["sales_share"], strict=True)):
        ax.annotate(
            f"{m:.0%}\n{share:.0%} выручки",
            (x, m),
            xytext=(0, 8 if m >= 0 else -30),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )
    ax.axhline(0, color=NEUTRAL, lw=0.8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_ylim(bands["margin_ci_low"].min() * 1.25, bands["margin_ci_high"].max() * 1.6)
    ax.set_xlabel("Скидка в строке заказа")
    ax.set_ylabel("Маржа (прибыль / выручка)")
    ax.set_title("Маржа уходит в минус при скидке больше 20%")
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, path)


def subcategory_band_heatmap(cells: pd.DataFrame, path: Path) -> Path:
    """Margin for each sub-category x discount band; cells with < 30 lines are hatched."""
    order = cells.drop_duplicates("discount_band").sort_values("discount_band_order")["discount_band"].tolist()
    margin = cells.pivot(index="sub_category", columns="discount_band", values="margin").reindex(columns=order)
    small = cells.pivot(index="sub_category", columns="discount_band", values="small_sample").reindex(columns=order)
    margin = margin.loc[margin.mean(axis=1).sort_values().index]
    small = small.loc[margin.index]

    fig, ax = plt.subplots(figsize=(9.5, 7.5))
    im = ax.imshow(margin.clip(-1, 1).values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    for i in range(margin.shape[0]):
        for j in range(margin.shape[1]):
            value = margin.iat[i, j]
            if pd.isna(value):
                continue
            if small.iat[i, j]:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, hatch="///", lw=0, color=NEUTRAL))
            color = "white" if abs(value) > 0.7 else "black"
            ax.text(j, i, f"{value:.0%}", ha="center", va="center", fontsize=8.5, color=color)
    ax.set_xticks(range(len(order)), order)
    ax.set_yticks(range(len(margin)), [SUB_CATEGORY_RU.get(s, s) for s in margin.index])
    ax.set_xlabel("Скидка в строке заказа")
    ax.set_title("Маржа по подкатегориям и уровням скидки (штриховка: меньше 30 строк)")
    fig.colorbar(im, ax=ax, format=mtick.PercentFormatter(1.0), label="Маржа (обрезана до ±100%)")
    return _save(fig, path)


def market_discount(markets: pd.DataFrame, path: Path) -> Path:
    """Average discount vs margin per market; bubble size = sales."""
    fig, ax = plt.subplots(figsize=(8, 4.8))
    sizes = markets["sales"] / markets["sales"].max() * 1500
    ax.scatter(markets["avg_discount"], markets["margin"], s=sizes, color="#2b6cb0", alpha=0.55, edgecolor="white")
    # APAC, US and Africa sit almost on top of each other: spread their labels apart
    offsets = {"APAC": (-115, 14), "US": (14, 10), "Africa": (14, -14)}
    for _, row in markets.iterrows():
        ax.annotate(
            MARKET_RU.get(row["market"], row["market"]),
            (row["avg_discount"], row["margin"]),
            xytext=offsets.get(row["market"], (10, 6)),
            textcoords="offset points",
            fontsize=9,
            arrowprops={"arrowstyle": "-", "color": NEUTRAL, "lw": 0.6} if row["market"] in offsets else None,
        )
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_xlabel("Средняя скидка в строке")
    ax.set_ylabel("Маржа рынка")
    ax.set_title("Рынки, где скидки выше, зарабатывают меньше (размер — выручка)")
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, path)


def monthly_sales(monthly: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    months = pd.to_datetime(monthly["month"])
    ax.plot(months, monthly["sales"], color="#2b6cb0", lw=2, label="Выручка")
    ax.plot(months, monthly["profit"], color=GAIN, lw=2, label="Прибыль")
    ax.yaxis.set_major_formatter(USD_K)
    ax.set_title("Помесячная выручка и прибыль: рост год к году и пики в конце года")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, path)


def render_all(marts: dict[str, pd.DataFrame], figures_dir: Path) -> list[Path]:
    return [
        discount_margin(marts["05_discount_bands"], figures_dir / "discount_margin.png"),
        subcategory_band_heatmap(marts["07_subcategory_band"], figures_dir / "subcategory_discount_heatmap.png"),
        market_discount(marts["04_market_discount"], figures_dir / "market_discount.png"),
        monthly_sales(marts["02_monthly_sales"], figures_dir / "monthly_sales.png"),
    ]
