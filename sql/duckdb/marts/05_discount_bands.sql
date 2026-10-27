-- Profit margin by discount band with a 95% confidence interval.
-- margin = sum(profit) / sum(sales) is a ratio estimator; its standard error uses the usual
-- linearisation: se = sqrt(sum((profit - margin * sales)^2) / (n * (n - 1))) / avg(sales).

WITH band AS (
    SELECT
        discount_band,
        discount_band_order,
        count(*)                    AS lines,
        sum(sales)                  AS sales,
        sum(profit)                 AS profit,
        sum(profit) / sum(sales)    AS margin,
        avg(sales)                  AS mean_sales,
        avg((profit < 0)::INT)      AS loss_line_share,
        avg(discount)               AS avg_discount
    FROM stg_orders
    GROUP BY 1, 2
),
se AS (
    SELECT
        b.discount_band,
        sqrt(sum(power(o.profit - b.margin * o.sales, 2)) / nullif(b.lines * (b.lines - 1), 0)) / b.mean_sales AS margin_se
    FROM band AS b
    JOIN stg_orders AS o USING (discount_band)
    GROUP BY b.discount_band, b.lines, b.mean_sales
)
SELECT
    b.discount_band,
    b.lines,
    round(b.sales, 2)                                       AS sales,
    round(b.sales / sum(b.sales) OVER (), 4)                AS sales_share,
    round(b.profit, 2)                                      AS profit,
    round(b.margin, 4)                                      AS margin,
    round(b.margin - 1.96 * se.margin_se, 4)                AS margin_ci_low,
    round(b.margin + 1.96 * se.margin_se, 4)                AS margin_ci_high,
    round(b.loss_line_share, 4)                             AS loss_line_share,
    round(b.avg_discount, 4)                                AS avg_discount
FROM band AS b
JOIN se USING (discount_band)
ORDER BY b.discount_band_order;
