"""Statistics behind the discount findings.

Run: python -m superstore.analysis.stats_models

1. Welch test: profit per order line with vs. without a discount, overall and within each category
   (discounts are not spread evenly across categories, so the pooled gap mixes in product mix).
   Reported as a dollar difference with a 95% CI, not just a p-value: with ~51k lines almost any gap
   is "significant".
2. OLS with heteroscedasticity-robust (HC3) errors: line profit margin on discount band, controlling
   for sub-category and market. Bands instead of a linear discount term because margin falls
   non-linearly with discount. Breusch-Pagan confirms the residual variance is not constant, which is
   why HC3 errors are used. The model is descriptive: discounts were not randomised, so coefficients
   are associations, not causal effects. Shipping cost is deliberately left out: it is computed from
   the order value (corr ~0.77 with sales) and would leak the outcome.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.stats.diagnostic import het_breuschpagan  # noqa: E402

BASE_BAND = "0%"
BAND_ORDER = ["0%", "1–10%", "11–20%", "21–30%", "31–50%", ">50%"]
MODEL_FORMULA = f"profit_margin ~ C(discount_band, Treatment(reference='{BASE_BAND}')) + C(sub_category) + C(market)"


def welch_row(group: str, no_discount: pd.Series, discount: pd.Series) -> dict:
    res = stats.ttest_ind(discount, no_discount, equal_var=False)
    ci = res.confidence_interval(0.95)
    return {
        "group": group,
        "n_no_discount": len(no_discount),
        "n_discount": len(discount),
        "mean_profit_no_discount": round(float(no_discount.mean()), 2),
        "mean_profit_discount": round(float(discount.mean()), 2),
        "mean_diff": round(float(discount.mean() - no_discount.mean()), 2),
        "ci_low": round(float(ci.low), 2),
        "ci_high": round(float(ci.high), 2),
        "median_diff": round(float(discount.median() - no_discount.median()), 2),
        "p_value": float(f"{res.pvalue:.3g}"),
    }


def discount_profit_test(df: pd.DataFrame) -> pd.DataFrame:
    """Mean profit per line, discounted minus not discounted: pooled and within each category."""
    rows = []
    for group, part in [("all", df), *sorted(df.groupby("category"))]:
        rows.append(
            welch_row(group, part.loc[part["discount"] == 0, "profit"], part.loc[part["discount"] > 0, "profit"])
        )
    return pd.DataFrame(rows)


def fit_margin_model(df: pd.DataFrame):
    return smf.ols(MODEL_FORMULA, data=df).fit(cov_type="HC3")


def margin_model_tables(model) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(discount band coefficients relative to no discount, one-row model summary)."""
    ci = model.conf_int()
    rows = [{"discount_band": BASE_BAND, "coef": 0.0, "se": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": None}]
    for term in model.params.index:
        if match := re.search(r"discount_band.*\[T\.(.+)\]$", term):
            rows.append(
                {
                    "discount_band": match.group(1),
                    "coef": round(float(model.params[term]), 4),
                    "se": round(float(model.bse[term]), 4),
                    "ci_low": round(float(ci.loc[term, 0]), 4),
                    "ci_high": round(float(ci.loc[term, 1]), 4),
                    "p_value": float(f"{model.pvalues[term]:.3g}"),
                }
            )
    coefs = pd.DataFrame(rows)
    coefs["discount_band"] = pd.Categorical(coefs["discount_band"], BAND_ORDER, ordered=True)
    coefs = coefs.sort_values("discount_band").reset_index(drop=True)
    coefs["discount_band"] = coefs["discount_band"].astype(str)

    bp_pvalue = het_breuschpagan(model.resid, model.model.exog)[1]
    info = pd.DataFrame(
        [
            {
                "formula": MODEL_FORMULA,
                "n": int(model.nobs),
                "r2": round(float(model.rsquared), 4),
                "adj_r2": round(float(model.rsquared_adj), 4),
                "cov_type": model.cov_type,
                "breusch_pagan_p": float(f"{bp_pvalue:.3g}"),
            }
        ]
    )
    return coefs, info


def plot_residuals(model, path: Path) -> Path:
    """Residuals vs fitted and a QQ plot: the visual check behind using robust errors."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.scatter(model.fittedvalues, model.resid, s=3, alpha=0.15, color="#2c5282", rasterized=True)
    ax1.axhline(0, color="#c53030", lw=1)
    ax1.set_xlabel("Прогноз маржи строки")
    ax1.set_ylabel("Остаток")
    ax1.set_title("Остатки против прогноза")
    stats.probplot(model.resid.sample(5000, random_state=0), dist="norm", plot=ax2)
    ax2.set_title("QQ-график остатков (5 000 строк)")
    ax2.set_xlabel("Теоретические квантили нормального распределения")
    ax2.set_ylabel("Квантили остатков")
    ax2.get_lines()[0].set(markersize=2, alpha=0.4)
    fig.suptitle("Диагностика модели маржи: разброс неоднородный и хвосты тяжелее нормальных → ошибки HC3")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def run(df: pd.DataFrame, figures_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    model = fit_margin_model(df)
    coefs, info = margin_model_tables(model)
    if figures_dir is not None:
        plot_residuals(model, figures_dir / "margin_model_residuals.png")
    return {
        "stats_discount_ttest": discount_profit_test(df),
        "stats_margin_model": coefs,
        "stats_margin_model_info": info,
    }


def main() -> None:
    from superstore.warehouse import connect

    con = connect()
    results = run(con.table("stg_orders").df())
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        for name, table in results.items():
            print(f"\n=== {name} ===\n{table.to_string(index=False)}")


if __name__ == "__main__":
    main()
