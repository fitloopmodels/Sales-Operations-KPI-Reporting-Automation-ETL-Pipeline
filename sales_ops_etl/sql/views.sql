-- ============================================================
-- Reporting Views — Sales Operations Warehouse
-- ============================================================

-- View: Executive KPI Summary (used by Power BI)
CREATE VIEW IF NOT EXISTS vw_exec_kpi_summary AS
SELECT
    r.region,
    r.territory,
    r.rep_name,
    strftime('%Y-%m', rv.close_date) AS month_year,
    SUM(rv.revenue)                  AS actual_revenue,
    q.quota_amount,
    ROUND(SUM(rv.revenue) / NULLIF(q.quota_amount, 0), 4) AS quota_attainment,
    COUNT(DISTINCT o.opportunity_id) AS total_opps,
    SUM(o.is_won)                    AS won_opps,
    ROUND(SUM(o.is_won) * 1.0 / NULLIF(COUNT(DISTINCT o.opportunity_id), 0), 4) AS win_rate,
    ROUND(AVG(o.days_in_pipeline), 1) AS avg_cycle_days
FROM fact_revenue rv
JOIN dim_reps r   ON rv.rep_id = r.rep_id
LEFT JOIN fact_opportunities o
    ON o.rep_id = rv.rep_id
    AND strftime('%Y-%m', o.close_date) = strftime('%Y-%m', rv.close_date)
    AND o.is_closed = 1
LEFT JOIN fact_quotas q
    ON q.rep_id = rv.rep_id
    AND q.month_year = strftime('%Y-%m', rv.close_date)
GROUP BY r.region, r.territory, r.rep_name, month_year, q.quota_amount;


-- View: Pipeline Health (open opportunities)
CREATE VIEW IF NOT EXISTS vw_pipeline_health AS
SELECT
    r.rep_name,
    r.territory,
    o.stage,
    COUNT(*)                    AS opp_count,
    SUM(o.deal_value)           AS pipeline_value,
    SUM(o.deal_value * o.probability / 100.0) AS weighted_pipeline,
    ROUND(AVG(o.days_in_pipeline), 1) AS avg_age_days
FROM fact_opportunities o
JOIN dim_reps r ON o.rep_id = r.rep_id
WHERE o.is_closed = 0
GROUP BY r.rep_name, r.territory, o.stage;


-- View: Campaign Performance
CREATE VIEW IF NOT EXISTS vw_campaign_performance AS
SELECT
    c.campaign_name,
    c.campaign_type,
    COUNT(o.opportunity_id)     AS total_opps,
    SUM(o.is_won)               AS won_opps,
    ROUND(SUM(o.is_won) * 1.0 / NULLIF(COUNT(o.opportunity_id), 0), 4) AS win_rate,
    ROUND(AVG(o.deal_value), 2) AS avg_deal_value,
    ROUND(SUM(CASE WHEN o.is_won = 1 THEN o.deal_value ELSE 0 END), 2) AS total_revenue
FROM fact_opportunities o
JOIN dim_campaigns c ON o.campaign_id = c.campaign_id
WHERE o.is_closed = 1
GROUP BY c.campaign_name, c.campaign_type;
