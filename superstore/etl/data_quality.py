"""Проверки качества данных после ETL."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    passed: bool
    checks: list[dict]


def run_checks(df: pd.DataFrame, min_rows: int = 10_000) -> QualityReport:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": ok, "detail": detail})

    add("row_count", len(df) >= min_rows, f"строк={len(df):,}")
    add("no_null_order_id", df["order_id"].notna().all())
    add("positive_sales", (df["sales"] > 0).all(), "вся выручка > 0")

    margin = df["profit_margin"].dropna()
    p99 = margin.abs().quantile(0.99)
    add(
        "profit_margin_range",
        p99 < 5,
        f"99-й перц. |маржа|={p99:.2f}",
    )

    add(
        "valid_years",
        df["year"].between(2011, 2014).fillna(False).all(),
        f"годы={sorted(df['year'].dropna().unique().astype(int).tolist())}",
    )

    add(
        "regions_present",
        df["region"].nunique() >= 4,
        f"регионов={df['region'].nunique()}",
    )

    # H2: ужесточено — 100% дат должны быть заполнены
    # (NaT-строки теперь отсеиваются в clean(), но проверяем на всякий случай)
    add(
        "order_dates_populated",
        df["order_date"].notna().all(),
        f"заполнено дат={df['order_date'].notna().mean():.1%}",
    )

    # M3: проверяем уникальность row_id (если колонка есть)
    if "row_id" in df.columns:
        row_id_unique = df["row_id"].is_unique
        add(
            "row_id_unique",
            row_id_unique,
            f"уникальных row_id={df['row_id'].nunique():,} из {len(df):,}",
        )

    # M1: валидация enum-значений по словарям labels.py
    from superstore.labels import CATEGORY_RU, REGION_RU, SEGMENT_RU, SHIP_MODE_RU

    for col, valid_keys, label in (
        ("category", set(CATEGORY_RU.keys()), "категории"),
        ("segment", set(SEGMENT_RU.keys()), "сегменты"),
        ("ship_mode", set(SHIP_MODE_RU.keys()), "режимы доставки"),
    ):
        if col in df.columns:
            valid = df[col].dropna().isin(valid_keys)
            invalid_count = (~valid).sum()
            add(
                f"valid_{col}",
                invalid_count == 0,
                f"невалидных {label}={invalid_count:,}",
            )

    # Регионы — проверяем отдельно, т.к. в Global Superstore их 13+
    if "region" in df.columns:
        valid_regions = set(REGION_RU.keys())
        invalid_regions = df["region"].dropna()[~df["region"].dropna().isin(valid_regions)]
        add(
            "valid_region_values",
            len(invalid_regions) == 0,
            f"невалидных регионов={len(invalid_regions):,}",
        )

    passed = all(c["ok"] for c in checks)
    return QualityReport(passed=passed, checks=checks)


def print_report(report: QualityReport) -> None:
    from superstore.labels import QUALITY_CHECKS_RU

    for c in report.checks:
        status = "ОК" if c["ok"] else "ОШИБКА"
        name = QUALITY_CHECKS_RU.get(c["check"], c["check"])
        detail = f" — {c['detail']}" if c.get("detail") else ""
        logger.info("[%s] %s%s", status, name, detail)
    if report.passed:
        logger.info("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    else:
        logger.error("ЕСТЬ ОШИБКИ КАЧЕСТВА ДАННЫХ")
