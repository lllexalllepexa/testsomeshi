"""Data quality gate for the cleaned orders table.

The ETL does not filter rows, so every check here can actually fail: a violation stops the pipeline
instead of being silently dropped upstream.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from superstore.labels import (
    CATEGORY_RU,
    MARKET_RU,
    ORDER_PRIORITY_RU,
    QUALITY_CHECKS_RU,
    REGION_RU,
    SEGMENT_RU,
    SHIP_MODE_RU,
    SUB_CATEGORY_RU,
)

log = logging.getLogger(__name__)

REQUIRED = [
    "row_id",
    "order_id",
    "order_date",
    "ship_date",
    "customer_id",
    "product_id",
    "sales",
    "quantity",
    "discount",
    "profit",
]
ENUMS: dict[str, dict[str, str]] = {
    "category": CATEGORY_RU,
    "sub_category": SUB_CATEGORY_RU,
    "segment": SEGMENT_RU,
    "market": MARKET_RU,
    "region": REGION_RU,
    "ship_mode": SHIP_MODE_RU,
    "order_priority": ORDER_PRIORITY_RU,
}


@dataclass
class QualityReport:
    passed: bool
    checks: list[dict]

    @property
    def failures(self) -> list[str]:
        return [c["check"] for c in self.checks if not c["ok"]]


def run_checks(df: pd.DataFrame, min_rows: int = 50_000, years: tuple[int, int] = (2011, 2014)) -> QualityReport:
    checks: list[dict] = []

    def add(name: str, bad: int, detail: str = "") -> None:
        checks.append({"check": name, "ok": bad == 0, "bad_rows": int(bad), "detail": detail})

    add("row_count", int(len(df) < min_rows), f"rows={len(df):,}, expected >= {min_rows:,}")
    add("row_id_unique", int(df["row_id"].duplicated().sum()))
    add("required_not_null", int(df[REQUIRED].isna().any(axis=1).sum()), ", ".join(REQUIRED))
    add("sales_positive", int((~(df["sales"] > 0)).sum()))
    add("quantity_positive", int((~(df["quantity"] > 0)).sum()))
    add("discount_range", int((~df["discount"].between(0, 1, inclusive="left")).sum()))
    add("ship_after_order", int((df["ship_date"] < df["order_date"]).sum()))
    add(
        "years_in_range",
        int((~df["order_date"].dt.year.between(*years)).sum()),
        f"expected {years[0]}–{years[1]}",
    )
    for col, allowed in ENUMS.items():
        invalid = df[col].dropna()[~df[col].dropna().isin(allowed)]
        add(f"valid_{col}", len(invalid), f"e.g. {sorted(invalid.unique())[:3]}" if len(invalid) else "")

    return QualityReport(passed=all(c["ok"] for c in checks), checks=checks)


def print_report(report: QualityReport) -> None:
    for c in report.checks:
        status = "ОК" if c["ok"] else f"ОШИБКА ({c['bad_rows']:,} строк)"
        detail = f" — {c['detail']}" if c["detail"] else ""
        log.info("[%s] %s%s", status, QUALITY_CHECKS_RU.get(c["check"], c["check"]), detail)
    if report.passed:
        log.info("Все %d проверок пройдены", len(report.checks))
    else:
        log.error("Проверки качества не пройдены: %s", ", ".join(report.failures))
