"""
kpi_calculator.py
-----------------
Computes all core sales KPIs from the warehouse.
Returns DataFrames suitable for reporting and Power BI export.
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'etl'))
import load

EXPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)


# ── 1. Win Rate ───────────────────────────────────────────────

def calc_win_rate(granularity: str = 'rep_month') -> pd.DataFrame:
    """
    granularity: 'rep_month' | 'region_month' | 'overall'
    """
    sql = """
        SELECT
            r.rep_name, r.region, r.territory,
            strftime('%Y-%m', o.close_date) AS month_year,
            COUNT(*) AS total_closed,
            SUM(o.is_won) AS won,
            ROUND(SUM(o.is_won) * 1.0 / COUNT(*), 4) AS win_rate
        FROM fact_opportunities o
        JOIN dim_reps r ON o.rep_id = r.rep_id
        WHERE o.is_closed = 1 AND o.close_date IS NOT NULL
        GROUP BY r.rep_name, r.region, r.territory, month_year
        ORDER BY month_year, win_rate DESC
    """
    df = load.query(sql)
    return df


# ── 2. Pipeline Velocity ──────────────────────────────────────

def calc_pipeline_velocity() -> pd.DataFrame:
    """
    Pipeline Velocity = (Opps × Win Rate × Avg Deal Size) / Avg Sales Cycle (days)
    """
    sql = """
        SELECT
            r.region,
            strftime('%Y-%m', o.created_date) AS month_year,
            COUNT(*) AS num_opportunities,
            ROUND(AVG(o.deal_value), 2) AS avg_deal_size,
            ROUND(SUM(o.is_won) * 1.0 / NULLIF(SUM(o.is_closed), 0), 4) AS win_rate,
            ROUND(AVG(o.days_in_pipeline), 1) AS avg_cycle_days
        FROM fact_opportunities o
        JOIN dim_reps r ON o.rep_id = r.rep_id
        GROUP BY r.region, month_year
        HAVING avg_cycle_days > 0
        ORDER BY month_year, r.region
    """
    df = load.query(sql)
    df['pipeline_velocity'] = (
        df['num_opportunities'] * df['win_rate'] * df['avg_deal_size']
        / df['avg_cycle_days']
    ).round(2)
    return df


# ── 3. Quota Attainment ───────────────────────────────────────

def calc_quota_attainment() -> pd.DataFrame:
    sql = """
        SELECT
            r.rep_name, r.region, r.territory,
            q.month_year,
            COALESCE(SUM(rv.revenue), 0) AS actual_revenue,
            q.quota_amount,
            ROUND(COALESCE(SUM(rv.revenue), 0) / NULLIF(q.quota_amount, 0), 4) AS quota_attainment
        FROM fact_quotas q
        JOIN dim_reps r ON q.rep_id = r.rep_id
        LEFT JOIN fact_revenue rv
            ON rv.rep_id = q.rep_id AND rv.month_year = q.month_year
        GROUP BY r.rep_name, r.region, r.territory, q.month_year, q.quota_amount
        ORDER BY q.month_year DESC, quota_attainment DESC
    """
    df = load.query(sql)
    df['attainment_band'] = pd.cut(
        df['quota_attainment'],
        bins=[-np.inf, 0.5, 0.8, 1.0, 1.2, np.inf],
        labels=['<50%', '50-80%', '80-100%', '100-120%', '>120%']
    )
    return df


# ── 4. Revenue Forecast Accuracy ──────────────────────────────

def calc_forecast_accuracy() -> pd.DataFrame:
    sql = """
        SELECT
            r.rep_name, r.region,
            f.month_year,
            f.forecasted_rev,
            COALESCE(SUM(rv.revenue), 0) AS actual_revenue
        FROM fact_forecasts f
        JOIN dim_reps r ON f.rep_id = r.rep_id
        LEFT JOIN fact_revenue rv
            ON rv.rep_id = f.rep_id AND rv.month_year = f.month_year
        GROUP BY r.rep_name, r.region, f.month_year, f.forecasted_rev
        ORDER BY f.month_year DESC
    """
    df = load.query(sql)
    df['abs_error']         = (df['actual_revenue'] - df['forecasted_rev']).abs()
    df['forecast_accuracy'] = (
        1 - df['abs_error'] / df['actual_revenue'].replace(0, np.nan)
    ).clip(lower=0).round(4)
    df['mape'] = (df['abs_error'] / df['actual_revenue'].replace(0, np.nan) * 100).round(2)
    return df


# ── 5. MoM Revenue Variance ───────────────────────────────────

def calc_mom_variance() -> pd.DataFrame:
    sql = """
        SELECT month_year, SUM(revenue) AS total_revenue
        FROM fact_revenue
        GROUP BY month_year
        ORDER BY month_year
    """
    df = load.query(sql)
    df['prev_revenue']   = df['total_revenue'].shift(1)
    df['variance']       = df['total_revenue'] - df['prev_revenue']
    df['variance_pct']   = (df['variance'] / df['prev_revenue'] * 100).round(2)
    return df.dropna()


# ── 6. Territory Performance ──────────────────────────────────

def calc_territory_performance() -> pd.DataFrame:
    sql = """
        SELECT
            r.territory, r.region,
            COUNT(DISTINCT o.opportunity_id) AS total_opps,
            SUM(o.is_won) AS won_opps,
            ROUND(SUM(o.is_won) * 1.0 / NULLIF(COUNT(DISTINCT o.opportunity_id), 0), 4) AS win_rate,
            ROUND(SUM(CASE WHEN o.is_won=1 THEN o.deal_value ELSE 0 END), 2) AS total_revenue,
            ROUND(AVG(CASE WHEN o.is_won=1 THEN o.deal_value END), 2) AS avg_deal_size,
            ROUND(AVG(o.days_in_pipeline), 1) AS avg_cycle_days
        FROM fact_opportunities o
        JOIN dim_reps r ON o.rep_id = r.rep_id
        WHERE o.is_closed = 1
        GROUP BY r.territory, r.region
        ORDER BY total_revenue DESC
    """
    return load.query(sql)


# ── Export all KPIs ───────────────────────────────────────────

def run():
    print("── Computing KPIs ───────────────────────────────────────")

    kpis = {
        'win_rate':            calc_win_rate(),
        'pipeline_velocity':   calc_pipeline_velocity(),
        'quota_attainment':    calc_quota_attainment(),
        'forecast_accuracy':   calc_forecast_accuracy(),
        'mom_variance':        calc_mom_variance(),
        'territory_perf':      calc_territory_performance(),
    }

    for name, df in kpis.items():
        path = os.path.join(EXPORT_DIR, f'{name}.csv')
        df.to_csv(path, index=False)
        print(f"  {name:<25} {len(df):>5} rows → {path.split('/')[-1]}")

    print(f"\n  Exports: {EXPORT_DIR}")
    return kpis


if __name__ == '__main__':
    run()
