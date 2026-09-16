# Модель данных

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : "places"
    ORDER ||--|{ ORDER_LINE : "contains"
    PRODUCT ||--o{ ORDER_LINE : "ordered in"

    CUSTOMER {
        string customer_id PK
        string customer_name
        string segment
    }
    ORDER {
        string order_id PK
        string customer_id FK
        date order_date
        date ship_date
        string ship_mode
    }
    PRODUCT {
        string product_id PK
        string category
        string sub_category
        string product_name
    }
    ORDER_LINE {
        bigint row_id PK
        string order_id FK
        string product_id FK
        float sales
        float profit
        float discount
        int quantity
    }
```

## Витрина `mart_region_year`

| Поле | Тип | Смысл |
|------|-----|--------|
| region, country, year | измерения | |
| order_lines | count | число строк |
| revenue, profit | sum | метрики |
| margin | ratio | profit / revenue |

SQL: `sql/duckdb/analytics.sql`, `sql/postgres/init.sql`.
