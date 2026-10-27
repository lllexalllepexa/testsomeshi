# SQL

| Файл | Что |
|---|---|
| [`duckdb/stg_orders.sql`](duckdb/stg_orders.sql) | staging-view: диапазоны скидок и месяц заказа определены один раз |
| [`duckdb/marts/`](duckdb/marts/) | 7 витрин; запускаются `python -m superstore.pipeline --step marts`, выгрузки в [`outputs/`](../outputs/) |
| [`postgres/init.sql`](postgres/init.sql) | схема PostgreSQL с типами и ограничениями, view для BI |

Дашборд выполняет те же файлы витрин на отфильтрованных строках: определения метрик живут только здесь.
