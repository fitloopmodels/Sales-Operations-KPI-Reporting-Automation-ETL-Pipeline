"""
transform.py
------------
Cleans and enriches raw source data before loading.

Steps per dataset:
  1. Schema validation
  2. Null handling
  3. Type coercion
  4. Business rule enforcement
  5. Derived column generation
"""

import os
import pandas as pd
import numpy as np

RAW_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
PROC_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
os.makedirs(PROC_DIR, exist_ok=True)

VALID_STAGES = {'Prospecting', 'Qualification', 'Proposal',
                'Negotiation', 'Closed Won', 'Closed Lost'}


def _report(label: str, df_before: pd.DataFrame, df_after: pd.DataFrame):
    dropped = len(df_before) - len(df_after)
    print(f"  [{label}] {len(df_before)} → {len(df_after)} rows  |  dropped: {dropped}")


# ── Individual transformations ────────────────────────────────

def transform_reps(df: pd.DataFrame) -> pd.DataFrame:
    orig = df.copy()
    df = df.drop_duplicates(subset='rep_id')
    df['rep_name']  = df['rep_name'].str.strip().str.title()
    df['region']    = df['region'].str.strip().str.title()
    df['territory'] = df['territory'].str.strip().str.title()
    df['hire_date'] = pd.to_datetime(df['hire_date'], errors='coerce').dt.date
    df = df.dropna(subset=['rep_id', 'rep_name', 'region', 'territory'])
    _report('Reps', orig, df)
    return df


def transform_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    orig = df.copy()
    df = df.drop_duplicates(subset='opportunity_id')

    # Type coercion
    df['created_date']     = pd.to_datetime(df['created_date'],   errors='coerce').dt.date
    df['close_date']       = pd.to_datetime(df['close_date'],     errors='coerce').dt.date
    df['deal_value']       = pd.to_numeric(df['deal_value'],       errors='coerce')
    df['probability']      = pd.to_numeric(df['probability'],      errors='coerce').clip(0, 100)
    df['days_in_pipeline'] = pd.to_numeric(df['days_in_pipeline'], errors='coerce').abs()
    df['is_won']           = df['is_won'].fillna(0).astype(int)
    df['is_closed']        = df['is_closed'].fillna(0).astype(int)

    # Business rules
    invalid_stage = ~df['stage'].isin(VALID_STAGES)
    df.loc[invalid_stage, 'stage'] = 'Prospecting'

    # Deal value must be positive
    df = df[df['deal_value'] > 0]

    # Closed opps must have a close_date
    closed_no_date = df['is_closed'].eq(1) & df['close_date'].isna()
    df = df[~closed_no_date]

    # Derived: weighted deal value
    df['weighted_value'] = (df['deal_value'] * df['probability'] / 100).round(2)

    _report('Opportunities', orig, df)
    return df


def transform_revenue(df: pd.DataFrame) -> pd.DataFrame:
    orig = df.copy()
    df = df.drop_duplicates(subset='revenue_id')
    df['close_date'] = pd.to_datetime(df['close_date'], errors='coerce').dt.date
    df['revenue']    = pd.to_numeric(df['revenue'], errors='coerce')
    df = df.dropna(subset=['revenue_id', 'rep_id', 'revenue', 'close_date'])
    df = df[df['revenue'] > 0]
    # Ensure month_year is consistent
    df['month_year'] = pd.to_datetime(df['close_date']).dt.to_period('M').astype(str)
    _report('Revenue', orig, df)
    return df


def transform_quotas(df: pd.DataFrame) -> pd.DataFrame:
    orig = df.copy()
    df = df.drop_duplicates(subset='quota_id')
    df['quota_amount'] = pd.to_numeric(df['quota_amount'], errors='coerce')
    df = df.dropna(subset=['quota_id', 'rep_id', 'month_year', 'quota_amount'])
    df = df[df['quota_amount'] > 0]
    _report('Quotas', orig, df)
    return df


def transform_forecasts(df: pd.DataFrame) -> pd.DataFrame:
    orig = df.copy()
    df = df.drop_duplicates(subset='forecast_id')
    df['forecasted_rev'] = pd.to_numeric(df['forecasted_rev'], errors='coerce')
    df['forecast_date']  = pd.to_datetime(df['forecast_date'], errors='coerce').dt.date
    df = df.dropna(subset=['forecast_id', 'rep_id', 'month_year', 'forecasted_rev'])
    _report('Forecasts', orig, df)
    return df


def transform_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset='product_id')
    df['unit_price']  = pd.to_numeric(df['unit_price'],  errors='coerce')
    df['cost_price']  = pd.to_numeric(df['cost_price'],  errors='coerce')
    # Derived: margin %
    df['margin_pct'] = ((df['unit_price'] - df['cost_price']) / df['unit_price'] * 100).round(2)
    return df


def transform_campaigns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset='campaign_id')
    df['campaign_type'] = df['campaign_type'].str.upper().str.strip()
    return df


def build_dim_date(start='2023-01-01', end='2024-12-31') -> pd.DataFrame:
    """Generate date dimension table."""
    dates = pd.date_range(start=start, end=end, freq='D')
    df = pd.DataFrame({'date_id': dates.strftime('%Y-%m-%d'),
                       'year':        dates.year,
                       'quarter':     dates.quarter,
                       'month':       dates.month,
                       'month_name':  dates.strftime('%B'),
                       'week':        dates.isocalendar().week.values,
                       'day_of_week': dates.dayofweek,
                       'is_weekday':  (dates.dayofweek < 5).astype(int)})
    return df


# ── Master runner ─────────────────────────────────────────────

def run():
    print("── Transforming data ────────────────────────────────────")

    reps      = transform_reps(pd.read_csv(f"{RAW_DIR}/crm_reps.csv"))
    opps      = transform_opportunities(pd.read_csv(f"{RAW_DIR}/crm_opportunities.csv"))
    revenue   = transform_revenue(pd.read_csv(f"{RAW_DIR}/erp_revenue.csv"))
    quotas    = transform_quotas(pd.read_csv(f"{RAW_DIR}/quota_targets.csv"))
    forecasts = transform_forecasts(pd.read_csv(f"{RAW_DIR}/revenue_forecasts.csv"))
    products  = transform_products(pd.read_csv(f"{RAW_DIR}/product_catalog.csv"))
    campaigns = transform_campaigns(pd.read_csv(f"{RAW_DIR}/campaigns.csv"))
    dim_date  = build_dim_date()

    # Save processed outputs
    reps.to_csv(f"{PROC_DIR}/dim_reps.csv",           index=False)
    opps.to_csv(f"{PROC_DIR}/fact_opportunities.csv",  index=False)
    revenue.to_csv(f"{PROC_DIR}/fact_revenue.csv",     index=False)
    quotas.to_csv(f"{PROC_DIR}/fact_quotas.csv",       index=False)
    forecasts.to_csv(f"{PROC_DIR}/fact_forecasts.csv", index=False)
    products.to_csv(f"{PROC_DIR}/dim_products.csv",    index=False)
    campaigns.to_csv(f"{PROC_DIR}/dim_campaigns.csv",  index=False)
    dim_date.to_csv(f"{PROC_DIR}/dim_date.csv",        index=False)

    print(f"\n  Processed CSVs saved to: {PROC_DIR}")
    return reps, opps, revenue, quotas, forecasts, products, campaigns, dim_date


if __name__ == '__main__':
    run()
