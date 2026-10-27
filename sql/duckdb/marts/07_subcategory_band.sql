-- Sub-category x discount band (long format, feeds the heatmap). Cells with fewer than 30 lines
-- are kept but flagged, so the chart can grey them out instead of over-reading a handful of rows.

SELECT
    sub_category,
    discount_band,
    discount_band_order,
    count(*)                                AS lines,
    round(sum(sales), 2)                    AS sales,
    round(sum(profit), 2)                   AS profit,
    round(sum(profit) / sum(sales), 4)      AS margin,
    count(*) < 30                           AS small_sample
FROM stg_orders
GROUP BY 1, 2, 3
ORDER BY sub_category, discount_band_order;
