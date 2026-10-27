-- Staging view over the cleaned order lines: one row per order line.
-- Discount bands are defined here once; marts, statistics and the dashboard all read this view.

CREATE OR REPLACE VIEW stg_orders AS
SELECT
    *,
    date_trunc('month', order_date)::DATE                   AS order_month,
    CASE
        WHEN discount = 0    THEN '0%'
        WHEN discount <= 0.1 THEN '1–10%'
        WHEN discount <= 0.2 THEN '11–20%'
        WHEN discount <= 0.3 THEN '21–30%'
        WHEN discount <= 0.5 THEN '31–50%'
        ELSE '>50%'
    END                                                     AS discount_band,
    CASE
        WHEN discount = 0    THEN 0
        WHEN discount <= 0.1 THEN 1
        WHEN discount <= 0.2 THEN 2
        WHEN discount <= 0.3 THEN 3
        WHEN discount <= 0.5 THEN 4
        ELSE 5
    END                                                     AS discount_band_order,
    discount > 0.2                                          AS deep_discount
FROM orders;
