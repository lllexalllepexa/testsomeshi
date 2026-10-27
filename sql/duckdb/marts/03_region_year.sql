-- Region x year: sales, profit, margin, year-over-year growth and the cumulative share of the
-- region's total sales reached by the end of each year (1.0 in the region's last year).
-- The prior year is joined by value, so a year with no orders cannot shift the comparison.

WITH region_year AS (
    SELECT
        region,
        year,
        count(DISTINCT order_key)   AS orders,
        sum(sales)                  AS sales,
        sum(profit)                 AS profit
    FROM stg_orders
    GROUP BY 1, 2
)
SELECT
    r.region,
    r.year,
    r.orders,
    round(r.sales, 2)                                                                   AS sales,
    round(r.profit, 2)                                                                  AS profit,
    round(r.profit / r.sales, 4)                                                        AS margin,
    round(r.sales / p.sales - 1, 4)                                                     AS sales_yoy,
    round(
        sum(r.sales) OVER (PARTITION BY r.region ORDER BY r.year ROWS UNBOUNDED PRECEDING)
        / sum(r.sales) OVER (PARTITION BY r.region), 4)                                 AS cumulative_share
FROM region_year AS r
LEFT JOIN region_year AS p ON p.region = r.region AND p.year = r.year - 1
ORDER BY r.region, r.year;
