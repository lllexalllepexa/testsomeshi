"""
Мат. статистика: t-критерий, регрессия, PCA.
Запуск: python -m superstore.analysis.stats_models
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from superstore.labels import COLUMNS_RU, FEATURES_RU, SEGMENT_RU

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "data" / "processed" / "orders_clean.parquet"


def load() -> pd.DataFrame:
    if PARQUET.exists():
        return pd.read_parquet(PARQUET)
    from superstore.etl.load_and_clean import clean, resolve_raw

    return clean(pd.read_csv(resolve_raw(), low_memory=False))


def discount_profit_test(df: pd.DataFrame) -> dict:
    a = df.loc[df["discount"] == 0, "profit"].dropna()
    b = df.loc[df["discount"] > 0, "profit"].dropna()
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return {
        "без_скидки_n": len(a),
        "со_скидкой_n": len(b),
        "t_статистика": round(float(t), 4),
        "p_значение": float(p),
    }


def sales_regression(df: pd.DataFrame) -> dict:
    sub = df[["sales", "quantity", "discount", "shipping_cost"]].dropna()
    X = sub[["quantity", "discount", "shipping_cost"]].values
    y = sub["sales"].values
    model = LinearRegression().fit(X, y)
    coef = {
        FEATURES_RU[k]: round(v, 4)
        for k, v in zip(["quantity", "discount", "shipping_cost"], model.coef_)
    }
    return {
        "коэффициенты": coef,
        "свободный_член": round(float(model.intercept_), 4),
        "R2": round(float(model.score(X, y)), 4),
    }


def pca_segment_profiles(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("segment")
        .agg(
            avg_sales=("sales", "mean"),
            avg_profit=("profit", "mean"),
            avg_discount=("discount", "mean"),
            avg_qty=("quantity", "mean"),
            lines=("order_id", "count"),
        )
        .fillna(0)
    )
    agg.index = [SEGMENT_RU.get(i, i) for i in agg.index]
    agg.columns = [COLUMNS_RU.get(c, c) for c in agg.columns]
    X = StandardScaler().fit_transform(agg.values)
    pca = PCA(n_components=2)
    scores = pca.fit_transform(X)
    out = agg.copy()
    out["ГК1"] = scores[:, 0]
    out["ГК2"] = scores[:, 1]
    out.attrs["explained_variance_ratio"] = pca.explained_variance_ratio_.tolist()
    return out


def main() -> None:
    df = load()
    print("=== t-критерий Уэлча: прибыль (без скидки vs со скидкой) ===")
    print(discount_profit_test(df))
    print("\n=== Линейная регрессия: выручка ~ признаки ===")
    print(sales_regression(df))
    print("\n=== PCA профилей сегментов ===")
    seg = pca_segment_profiles(df)
    print(seg)
    ev = seg.attrs.get("explained_variance_ratio")
    if ev is not None:
        print("Доля объяснённой дисперсии:", [round(float(x), 4) for x in ev])


if __name__ == "__main__":
    main()
