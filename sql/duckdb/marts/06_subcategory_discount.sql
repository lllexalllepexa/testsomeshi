-- Sub-category: overall margin, how much of its sales carry a deep discount (> 20%), and the profit
-- those deep-discount lines produce. Sorted from the most to the least profit lost on deep discounts.

SELECT
    category,
    sub_category,
    round(sum(sales), 2)                                                        AS sales,
    round(sum(profit), 2)                                                       AS profit,
    round(sum(profit) / sum(sales), 4)                                          AS margin,
    round(avg(discount), 4)                                                     AS avg_discount,
    round(coalesce(sum(sales) FILTER (WHERE deep_discount), 0) / sum(sales), 4) AS deep_discount_sales_share,
    round(coalesce(sum(profit) FILTER (WHERE deep_discount), 0), 2)             AS deep_discount_profit,
    round(coalesce(sum(profit) FILTER (WHERE NOT deep_discount), 0), 2)         AS other_profit
FROM stg_orders
GROUP BY 1, 2
ORDER BY deep_discount_profit, sub_category;
