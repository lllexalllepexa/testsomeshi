-- Market: margin next to how heavily the market discounts.

SELECT
    market,
    count(DISTINCT order_key)                                                   AS orders,
    round(sum(sales), 2)                                                        AS sales,
    round(sum(profit), 2)                                                       AS profit,
    round(sum(profit) / sum(sales), 4)                                          AS margin,
    round(avg(discount), 4)                                                     AS avg_discount,
    round(coalesce(sum(sales) FILTER (WHERE deep_discount), 0) / sum(sales), 4) AS deep_discount_sales_share,
    round(coalesce(sum(profit) FILTER (WHERE deep_discount), 0), 2)             AS deep_discount_profit
FROM stg_orders
GROUP BY 1
ORDER BY margin, market;
