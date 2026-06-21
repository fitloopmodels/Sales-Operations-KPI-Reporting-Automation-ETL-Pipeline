-- ============================================================
-- KPI Queries — Sales Operations
-- ============================================================

-- -----------------------------------------------------------
-- 1. Win Rate by Rep (monthly)
-- -----------------------------------------------------------
SELECT
    r.rep_name,
    r.region,
    r.territory,
    strftime('%Y-%m', o.close_date) AS month_year,
    COUNT(*)                         AS total_closed,
    SUM(o.is_won)                    AS total_won,
    ROUND(SUM(o.is_won) * 1.0 / COUNT(*), 4) AS win_rate
FROM fact_opportunities o
JOIN dim_reps r ON o.rep_id = r.rep_id
WHERE o.is_closed = 1
  AND o.close_date IS NOT NULL
GROUP BY r.rep_name, r.region, r.territory, month_year
ORDER BY month_year DESC, win_rate DESC;


-- -----------------------------------------------------------
-- 2. Pipeline Velocity by Region (monthly)
--    Formula: (# Opps × Win Rate × Avg Deal Size) / Avg Cycle Days
-- -----------------------------------------------------------
SELECT
    r.region,
    strftime('%Y-%m', o.created_date) AS month_year,
    COUNT(*)                            AS num_opportunities,
    ROUND(AVG(o.deal_value), 2)         AS avg_deal_size,
    ROUND(SUM(o.is_won) * 1.0 / NULLIF(SUM(o.is_closed), 0), 4) AS win_rate,
    ROUND(AVG(o.days_in_pipeline), 1)   AS avg_cycle_days,
    ROUND(
        (COUNT(*) * (SUM(o.is_won) * 1.0 / NULLIF(SUM(o.is_closed), 0)) * AVG(o.deal_value))
        / NULLIF(AVG(o.days_in_pipeline), 0),
        2
    ) AS pipeline_velocity
FROM fact_opportunities o
JOIN dim_reps r ON o.rep_id = r.rep_id
GROUP BY r.region, month_year
ORDER BY month_year DESC, pipeline_velocity DESC;


-- -----------------------------------------------------------
-- 3. Quota Attainment by Rep (monthly)
-- -----------------------------------------------------------
SELECT
    r.rep_name,
    r.territory,
    q.month_year,
    COALESCE(SUM(rv.revenue), 0)        AS actual_revenue,
    q.quota_amount,
    ROUND(COALESCE(SUM(rv.revenue), 0) / NULLIF(q.quota_amount, 0), 4) AS quota_attainment
FROM fact_quotas q
JOIN dim_reps r ON q.rep_id = r.rep_id
LEFT JOIN fact_revenue rv
    ON rv.rep_id = q.rep_id
    AND rv.month_year = q.month_year
GROUP BY r.rep_name, r.territory, q.month_year, q.quota_amount
ORDER BY q.month_year DESC, quota_attainment DESC;


-- -----------------------------------------------------------
-- 4. Revenue Forecast Accuracy by Rep (monthly)
-- -----------------------------------------------------------
SELECT
    r.rep_name,
    f.month_year,
    f.forecasted_rev,
    COALESCE(SUM(rv.revenue), 0)    AS actual_revenue,
    ROUND(
        1.0 - ABS(COALESCE(SUM(rv.revenue), 0) - f.forecasted_rev)
            / NULLIF(COALESCE(SUM(rv.revenue), 0), 0),
        4
    ) AS forecast_accuracy
FROM fact_forecasts f
JOIN dim_reps r ON f.rep_id = r.rep_id
LEFT JOIN fact_revenue rv
    ON rv.rep_id = f.rep_id
    AND rv.month_year = f.month_year
GROUP BY r.rep_name, f.month_year, f.forecasted_rev
ORDER BY f.month_year DESC;


-- -----------------------------------------------------------
-- 5. Month-over-Month Revenue Variance
-- -----------------------------------------------------------
WITH monthly_rev AS (
    SELECT
        month_year,
        SUM(revenue) AS total_revenue
    FROM fact_revenue
    GROUP BY month_year
),
lagged AS (
    SELECT
        month_year,
        total_revenue,
        LAG(total_revenue) OVER (ORDER BY month_year) AS prev_month_revenue
    FROM monthly_rev
)
SELECT
    month_year,
    ROUND(total_revenue, 2)         AS current_revenue,
    ROUND(prev_month_revenue, 2)    AS previous_revenue,
    ROUND(total_revenue - prev_month_revenue, 2) AS revenue_variance,
    ROUND(
        (total_revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0) * 100,
        2
    ) AS variance_pct
FROM lagged
WHERE prev_month_revenue IS NOT NULL
ORDER BY month_year;


-- -----------------------------------------------------------
-- 6. Territory Performance Summary
-- -----------------------------------------------------------
SELECT
    r.territory,
    r.region,
    COUNT(DISTINCT o.opportunity_id)    AS total_opportunities,
    COUNT(DISTINCT rv.revenue_id)       AS closed_won_deals,
    ROUND(SUM(rv.revenue), 2)           AS total_revenue,
    ROUND(AVG(rv.revenue), 2)           AS avg_deal_size,
    ROUND(
        COUNT(DISTINCT rv.revenue_id) * 1.0
        / NULLIF(COUNT(DISTINCT o.opportunity_id), 0),
        4
    )                                   AS win_rate,
    ROUND(AVG(o.days_in_pipeline), 1)   AS avg_sales_cycle_days
FROM dim_reps r
LEFT JOIN fact_opportunities o ON o.rep_id = r.rep_id
LEFT JOIN fact_revenue rv ON rv.rep_id = r.rep_id
GROUP BY r.territory, r.region
ORDER BY total_revenue DESC;


-- -----------------------------------------------------------
-- 7. Sales Cycle Length by Stage and Product
-- -----------------------------------------------------------
SELECT
    p.category,
    o.stage,
    COUNT(*)                        AS opportunity_count,
    ROUND(AVG(o.days_in_pipeline), 1) AS avg_days,
    ROUND(MIN(o.days_in_pipeline), 1) AS min_days,
    ROUND(MAX(o.days_in_pipeline), 1) AS max_days
FROM fact_opportunities o
JOIN dim_products p ON o.product_id = p.product_id
WHERE o.is_closed = 1
GROUP BY p.category, o.stage
ORDER BY p.category, avg_days DESC;
