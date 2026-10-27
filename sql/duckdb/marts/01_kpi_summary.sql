-- Headline KPIs for the whole dataset (one row).
--   orders       = distinct Order ID + Customer ID (Order ID alone repeats across countries)
--   return_rate  = share of orders flagged in the Returns sheet
--   deep_*       = lines with discount > 20%, the band where margin turns negative

WITH per_order AS (
    SELECT order_key, bool_or(is_returned) AS is_returned
    FROM stg_orders
    GROUP BY 1
)
SELECT
    count(*)                                                               AS order_lines,
    (SELECT count(*) FROM per_order)                                       AS orders,
    count(DISTINCT customer_id)                                            AS customers,
    round(sum(sales), 2)                                                   AS sales,
    round(sum(profit), 2)                                                  AS profit,
    round(sum(profit) / sum(sales), 4)                                     AS margin,
    round(avg(discount), 4)                                                AS avg_discount,
    round((SELECT avg(is_returned::INT) FROM per_order), 4)                AS return_rate,
    round(avg((profit < 0)::INT), 4)                                       AS loss_line_share,
    round(avg((discount > 0)::INT) FILTER (WHERE profit < 0), 4)           AS loss_lines_discounted_share,
    round(coalesce(sum(profit) FILTER (WHERE profit < 0), 0), 2)           AS loss_lines_profit,
    round(coalesce(sum(sales) FILTER (WHERE deep_discount), 0) / sum(sales), 4) AS deep_discount_sales_share,
    round(coalesce(sum(profit) FILTER (WHERE deep_discount), 0), 2)        AS deep_discount_profit
FROM stg_orders;
