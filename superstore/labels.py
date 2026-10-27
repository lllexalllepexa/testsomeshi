"""Russian labels for reports and the dashboard (database columns stay in English).

The keys double as the allowed values that the data quality checks enforce.
"""

from __future__ import annotations

import pandas as pd

CATEGORY_RU: dict[str, str] = {
    "Technology": "Технологии",
    "Furniture": "Мебель",
    "Office Supplies": "Канцтовары",
}

SUB_CATEGORY_RU: dict[str, str] = {
    "Accessories": "Аксессуары",
    "Appliances": "Бытовая техника",
    "Art": "Товары для творчества",
    "Binders": "Папки",
    "Bookcases": "Книжные шкафы",
    "Chairs": "Стулья",
    "Copiers": "Копиры",
    "Envelopes": "Конверты",
    "Fasteners": "Крепёж",
    "Furnishings": "Предметы интерьера",
    "Labels": "Этикетки",
    "Machines": "Оргтехника",
    "Paper": "Бумага",
    "Phones": "Телефоны",
    "Storage": "Хранение",
    "Supplies": "Расходники",
    "Tables": "Столы",
}

SEGMENT_RU: dict[str, str] = {
    "Consumer": "Потребительский",
    "Corporate": "Корпоративный",
    "Home Office": "Домашний офис",
}

MARKET_RU: dict[str, str] = {
    "APAC": "Азия и Тихий океан",
    "Africa": "Африка",
    "Canada": "Канада",
    "EMEA": "EMEA",
    "EU": "Евросоюз",
    "LATAM": "Латинская Америка",
    "US": "США",
}

REGION_RU: dict[str, str] = {
    "Africa": "Африка",
    "Canada": "Канада",
    "Caribbean": "Карибы",
    "Central": "Центр",
    "Central Asia": "Центральная Азия",
    "EMEA": "EMEA",
    "East": "Восток",
    "North": "Север",
    "North Asia": "Северная Азия",
    "Oceania": "Океания",
    "South": "Юг",
    "Southeast Asia": "Юго-Восточная Азия",
    "West": "Запад",
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
    "row_id_unique": "уникальность row_id",
    "required_not_null": "обязательные поля заполнены",
    "sales_positive": "выручка > 0",
    "quantity_positive": "количество > 0",
    "discount_range": "скидка в [0, 1)",
    "ship_after_order": "отгрузка не раньше заказа",
    "years_in_range": "годы заказов в ожидаемом диапазоне",
    "valid_category": "валидные категории",
    "valid_sub_category": "валидные подкатегории",
    "valid_segment": "валидные сегменты",
    "valid_market": "валидные рынки",
    "valid_region": "валидные регионы",
    "valid_ship_mode": "валидные способы доставки",
    "valid_order_priority": "валидные приоритеты",
}


def translate(s: pd.Series, mapping: dict[str, str]) -> pd.Series:
    return s.map(lambda x: mapping.get(x, x) if pd.notna(x) else x)
