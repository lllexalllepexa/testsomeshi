"""Русские подписи для отчётов и UI (колонки в БД остаются на английском)."""
from __future__ import annotations

import pandas as pd

# Колонки
COLUMNS_RU: dict[str, str] = {
    "region": "регион",
    "country": "страна",
    "state": "штат",
    "city": "город",
    "year": "год",
    "month": "месяц",
    "category": "категория",
    "sub_category": "подкатегория",
    "segment": "сегмент",
    "sales": "выручка",
    "profit": "прибыль",
    "quantity": "количество",
    "discount": "скидка",
    "revenue": "выручка",
    "margin": "маржа",
    "lines": "строк_заказов",
    "order_id": "id_заказа",
    "customer_id": "id_клиента",
    "product_name": "товар",
    "profit_margin": "маржа_прибыли",
    "delivery_days": "дней_доставки",
    "shipping_cost": "стоимость_доставки",
    "avg_sales": "ср_выручка",
    "avg_profit": "ср_прибыль",
    "avg_discount": "ср_скидка",
    "avg_qty": "ср_количество",
    "pc1": "ГК1",
    "pc2": "ГК2",
}

# Значения из датасета
CATEGORY_RU: dict[str, str] = {
    "Technology": "Технологии",
    "Furniture": "Мебель",
    "Office Supplies": "Канцтовары",
}

SEGMENT_RU: dict[str, str] = {
    "Consumer": "Потребительский",
    "Corporate": "Корпоративный",
    "Home Office": "Домашний офис",
}

REGION_RU: dict[str, str] = {
    "West": "Запад",
    "East": "Восток",
    "Central": "Центр",
    "South": "Юг",
    "Southeast Asia": "Юго-Восточная Азия",
    "Eastern Asia": "Восточная Азия",
    "North Asia": "Северная Азия",
    "Central Asia": "Центральная Азия",
    "Oceania": "Океания",
    "Africa": "Африка",
    "Europe": "Европа",
    "Middle East and North Africa": "Ближний Восток и Северная Африка",
    "Caribbean": "Карибы",
    "North America": "Северная Америка",
    "South America": "Южная Америка",
}

SHIP_MODE_RU: dict[str, str] = {
    "Standard Class": "Стандарт",
    "Second Class": "Второй класс",
    "First Class": "Первый класс",
    "Same Day": "В день заказа",
}

ORDER_PRIORITY_RU: dict[str, str] = {
    "Low": "Низкий",
    "Medium": "Средний",
    "High": "Высокий",
    "Critical": "Критический",
}

QUALITY_CHECKS_RU: dict[str, str] = {
    "row_count": "число строк",
    "no_null_order_id": "id заказа без пропусков",
    "positive_sales": "выручка > 0",
    "profit_margin_range": "разброс маржи",
    "valid_years": "годы 2011–2014",
    "regions_present": "регионы в данных",
    "order_dates_populated": "даты заказов заполнены",
    "row_id_unique": "уникальность row_id",
    "valid_category": "валидные категории",
    "valid_segment": "валидные сегменты",
    "valid_ship_mode": "валидные режимы доставки",
    "valid_region_values": "валидные значения регионов",
}

FEATURES_RU: dict[str, str] = {
    "quantity": "количество",
    "discount": "скидка",
    "shipping_cost": "доставка",
}


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={k: v for k, v in COLUMNS_RU.items() if k in df.columns})


def translate_series(s: pd.Series, mapping: dict[str, str]) -> pd.Series:
    return s.map(lambda x: mapping.get(x, x) if pd.notna(x) else x)


def translate_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col, mapping in (
        ("category", CATEGORY_RU),
        ("segment", SEGMENT_RU),
        ("region", REGION_RU),
        ("ship_mode", SHIP_MODE_RU),
        ("order_priority", ORDER_PRIORITY_RU),
    ):
        if col in out.columns:
            out[col] = translate_series(out[col], mapping)
    return out


def for_display(df: pd.DataFrame, translate_enums: bool = True) -> pd.DataFrame:
    d = translate_values(df) if translate_enums else df.copy()
    return rename_columns(d)
