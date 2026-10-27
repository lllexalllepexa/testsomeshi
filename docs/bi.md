# Подключение BI-инструментов

Источники после пайплайна:

- `data/processed/orders_clean.parquet` — очищенные строки заказов (в репозитории);
- `data/processed/superstore.duckdb` — таблица `orders`, view `stg_orders` и витрины `mart_*` (создаётся `python -m superstore.pipeline`);
- PostgreSQL — таблица `orders` и view `mart_region_year`, `mart_discount_bands`.

## PostgreSQL для Superset, DataLens, Power BI

```bash
docker compose up -d postgres
python -m superstore.loaders.load_postgres
```

Строка подключения: `postgresql://analyst:analyst@localhost:5432/superstore` (локальная демо-база).

## Меры для Power BI

```
Выручка = SUM(orders[sales])
Прибыль = SUM(orders[profit])
Маржа = DIVIDE([Прибыль], [Выручка])
Заказы = DISTINCTCOUNT(orders[order_key])
Доля выручки со скидкой > 20% = DIVIDE(CALCULATE([Выручка], orders[discount] > 0.2), [Выручка])
```

`order_key` (Order ID + Customer ID) нужен потому, что Order ID в этом датасете повторяется в разных странах.
