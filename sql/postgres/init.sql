-- PostgreSQL schema for the cleaned Global Superstore order lines.
-- Idempotent: the loader (superstore/loaders/load_postgres.py) runs it before every load.

CREATE TABLE IF NOT EXISTS orders (
    row_id              BIGINT PRIMARY KEY,
    order_id            TEXT NOT NULL,
    order_key           TEXT NOT NULL,          -- Order ID + Customer ID: Order ID alone repeats across countries
    order_date          DATE NOT NULL,
    ship_date           DATE NOT NULL,
    ship_mode           TEXT,
    customer_id         TEXT NOT NULL,
    customer_name       TEXT,
    segment             TEXT,
    city                TEXT,
    state               TEXT,
    country             TEXT,
    market              TEXT,
    region              TEXT,
    product_id          TEXT NOT NULL,
    category            TEXT,
    sub_category        TEXT,
    product_name        TEXT,
    sales               NUMERIC(14, 4) NOT NULL CHECK (sales > 0),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    discount            NUMERIC(6, 4) NOT NULL CHECK (discount >= 0 AND discount < 1),
    profit              NUMERIC(14, 4) NOT NULL,
    shipping_cost       NUMERIC(10, 2),
    order_priority      TEXT,
    is_returned         BOOLEAN,
    year                INTEGER NOT NULL,
    delivery_days       INTEGER NOT NULL,
    profit_margin       DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_region ON orders (region);

-- Region x year mart (same grain and definitions as sql/duckdb/marts/03_region_year.sql).
CREATE OR REPLACE VIEW mart_region_year AS
SELECT
    region,
    year,
    count(DISTINCT order_key)           AS orders,
    sum(sales)                          AS sales,
    sum(profit)                         AS profit,
    sum(profit) / sum(sales)            AS margin
FROM orders
GROUP BY region, year;

-- Discount bands for BI tools (Superset, DataLens, Power BI).
CREATE OR REPLACE VIEW mart_discount_bands AS
SELECT
    CASE
        WHEN discount = 0    THEN '0%'
        WHEN discount <= 0.1 THEN '1–10%'
        WHEN discount <= 0.2 THEN '11–20%'
        WHEN discount <= 0.3 THEN '21–30%'
        WHEN discount <= 0.5 THEN '31–50%'
        ELSE '>50%'
    END                                 AS discount_band,
    count(*)                            AS lines,
    sum(sales)                          AS sales,
    sum(profit)                         AS profit,
    sum(profit) / sum(sales)            AS margin
FROM orders
GROUP BY 1;
