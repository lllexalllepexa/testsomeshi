-- Monthly sales, profit and orders, with growth against the same month a year earlier.
-- The prior month is joined by date, not taken with lag(12), so a missing month cannot shift the comparison.

WITH monthly AS (
    SELECT
        order_month,
        count(DISTINCT order_key)   AS orders,
        sum(sales)                  AS sales,
        sum(profit)                 AS profit
    FROM stg_orders
    GROUP BY 1
)
SELECT
    strftime(m.order_month, '%Y-%m')                AS month,
    m.orders,
    round(m.sales, 2)                               AS sales,
    round(m.profit, 2)                              AS profit,
    round(m.profit / m.sales, 4)                    AS margin,
    round(m.sales / p.sales - 1, 4)                 AS sales_yoy
FROM monthly AS m
LEFT JOIN monthly AS p ON p.order_month = (m.order_month - INTERVAL 1 YEAR)::DATE
ORDER BY m.order_month;
