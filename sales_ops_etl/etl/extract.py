"""
extract.py
----------
Simulates extraction from three source systems:
  - CRM  → opportunities + contacts
  - ERP  → revenue bookings
  - Marketing DB → campaign data

Outputs raw CSVs to data/raw/.
"""

import os
import random
import pandas as pd
import numpy as np
from faker import Faker
from datetime import date, timedelta

fake = Faker()
random.seed(42)
np.random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

# ── Constants ────────────────────────────────────────────────
REGIONS    = ['North', 'South', 'East', 'West']
TERRITORIES = {
    'North': ['NYC Metro', 'New England'],
    'South': ['Texas', 'Southeast'],
    'East':  ['Mid-Atlantic', 'Florida'],
    'West':  ['California', 'Pacific NW'],
}
STAGES = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
PRODUCTS = [
    {'product_id': 'P001', 'product_name': 'Enterprise Suite',  'category': 'Software',  'unit_price': 45000, 'cost_price': 12000},
    {'product_id': 'P002', 'product_name': 'Professional Plan', 'category': 'Software',  'unit_price': 12000, 'cost_price': 3500},
    {'product_id': 'P003', 'product_name': 'Starter Pack',      'category': 'Software',  'unit_price': 3600,  'cost_price': 900},
    {'product_id': 'P004', 'product_name': 'Implementation Svc','category': 'Services',  'unit_price': 25000, 'cost_price': 14000},
    {'product_id': 'P005', 'product_name': 'Support & Training', 'category': 'Services', 'unit_price': 8000,  'cost_price': 3000},
]
CAMPAIGNS = [
    {'campaign_id': 'C001', 'campaign_name': 'Q1 Email Blast A',    'campaign_type': 'A'},
    {'campaign_id': 'C002', 'campaign_name': 'Q1 Email Blast B',    'campaign_type': 'B'},
    {'campaign_id': 'C003', 'campaign_name': 'Q2 Webinar Series A', 'campaign_type': 'A'},
    {'campaign_id': 'C004', 'campaign_name': 'Q2 Webinar Series B', 'campaign_type': 'B'},
    {'campaign_id': 'C005', 'campaign_name': 'Q3 LinkedIn Ads A',   'campaign_type': 'A'},
    {'campaign_id': 'C006', 'campaign_name': 'Q3 LinkedIn Ads B',   'campaign_type': 'B'},
]

START_DATE = date(2023, 1, 1)
END_DATE   = date(2024, 12, 31)
N_REPS     = 20
N_OPPS     = 1200


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def extract_crm_reps() -> pd.DataFrame:
    """Dimension: Sales Reps."""
    rows = []
    rep_id = 1
    for region, territories in TERRITORIES.items():
        for territory in territories:
            for _ in range(N_REPS // len(TERRITORIES) // len(territories) + 1):
                rows.append({
                    'rep_id':    f'R{rep_id:03d}',
                    'rep_name':  fake.name(),
                    'region':    region,
                    'territory': territory,
                    'manager':   fake.name(),
                    'hire_date': random_date(date(2018, 1, 1), date(2023, 6, 1)).isoformat(),
                })
                rep_id += 1
                if rep_id > N_REPS:
                    break
            if rep_id > N_REPS:
                break
        if rep_id > N_REPS:
            break
    return pd.DataFrame(rows[:N_REPS])


def extract_crm_opportunities(reps_df: pd.DataFrame) -> pd.DataFrame:
    """Fact: Opportunities from CRM."""
    rep_ids    = reps_df['rep_id'].tolist()
    product_ids = [p['product_id'] for p in PRODUCTS]
    campaign_ids = [c['campaign_id'] for c in CAMPAIGNS]

    rows = []
    for i in range(1, N_OPPS + 1):
        created = random_date(START_DATE, END_DATE - timedelta(days=30))
        cycle_days = random.randint(14, 120)
        close_dt = created + timedelta(days=cycle_days)
        if close_dt > END_DATE:
            close_dt = None
            is_closed = 0
            is_won = 0
            stage = random.choice(STAGES[:4])
        else:
            is_closed = 1
            # Win rate ~38% overall — realistic B2B
            is_won = int(random.random() < 0.38)
            stage = 'Closed Won' if is_won else 'Closed Lost'

        product = random.choice(PRODUCTS)
        noise   = random.uniform(0.85, 1.20)
        deal_val = round(product['unit_price'] * noise, 2)

        rows.append({
            'opportunity_id':   f'OPP{i:04d}',
            'rep_id':           random.choice(rep_ids),
            'product_id':       product['product_id'],
            'campaign_id':      random.choice(campaign_ids),
            'created_date':     created.isoformat(),
            'close_date':       close_dt.isoformat() if close_dt else None,
            'stage':            stage,
            'deal_value':       deal_val,
            'probability':      random.choice([10, 25, 50, 75, 90]) if not is_closed else (100 if is_won else 0),
            'days_in_pipeline': cycle_days if is_closed else (date.today() - created).days,
            'is_won':           is_won,
            'is_closed':        is_closed,
        })
    return pd.DataFrame(rows)


def extract_erp_revenue(opps_df: pd.DataFrame) -> pd.DataFrame:
    """Fact: Revenue bookings from ERP (only Closed Won records)."""
    won = opps_df[opps_df['is_won'] == 1].copy()
    rows = []
    for i, row in enumerate(won.itertuples(), 1):
        rows.append({
            'revenue_id':     f'REV{i:04d}',
            'opportunity_id': row.opportunity_id,
            'rep_id':         row.rep_id,
            'product_id':     row.product_id,
            'close_date':     row.close_date,
            'revenue':        row.deal_value,
            'month_year':     row.close_date[:7],  # YYYY-MM
        })
    return pd.DataFrame(rows)


def extract_quota_data(reps_df: pd.DataFrame) -> pd.DataFrame:
    """Fact: Monthly quotas per rep."""
    rows = []
    q_id = 1
    months = pd.period_range('2023-01', '2024-12', freq='M')
    for _, rep in reps_df.iterrows():
        # Base quota varies by territory
        base = random.choice([80000, 100000, 120000, 150000])
        for m in months:
            rows.append({
                'quota_id':     f'Q{q_id:04d}',
                'rep_id':       rep['rep_id'],
                'month_year':   str(m),
                'quota_amount': round(base * random.uniform(0.95, 1.05), 2),
            })
            q_id += 1
    return pd.DataFrame(rows)


def extract_forecast_data(reps_df: pd.DataFrame, revenue_df: pd.DataFrame) -> pd.DataFrame:
    """Fact: Revenue forecasts per rep per month (with realistic noise)."""
    rows = []
    f_id = 1
    for _, rep in reps_df.iterrows():
        rep_rev = revenue_df[revenue_df['rep_id'] == rep['rep_id']]
        monthly = rep_rev.groupby('month_year')['revenue'].sum().reset_index()
        for _, m in monthly.iterrows():
            # Forecast is actual ± 0–25% noise
            noise = random.uniform(-0.20, 0.25)
            rows.append({
                'forecast_id':    f'F{f_id:04d}',
                'rep_id':         rep['rep_id'],
                'month_year':     m['month_year'],
                'forecasted_rev': round(m['revenue'] * (1 + noise), 2),
                'forecast_date':  (pd.Period(m['month_year'], freq='M') - 1).to_timestamp().date().isoformat(),
            })
            f_id += 1
    return pd.DataFrame(rows)


def run():
    print("── Extracting source data ──────────────────────────────")

    reps = extract_crm_reps()
    print(f"  Reps:          {len(reps)} rows")

    opps = extract_crm_opportunities(reps)
    print(f"  Opportunities: {len(opps)} rows  |  Win rate: {opps['is_won'].mean():.1%}")

    revenue = extract_erp_revenue(opps)
    print(f"  Revenue rows:  {len(revenue)}  |  Total: ${revenue['revenue'].sum():,.0f}")

    quotas = extract_quota_data(reps)
    print(f"  Quota rows:    {len(quotas)}")

    forecasts = extract_forecast_data(reps, revenue)
    print(f"  Forecast rows: {len(forecasts)}")

    products  = pd.DataFrame(PRODUCTS)
    campaigns = pd.DataFrame(CAMPAIGNS)

    # Save raw CSVs (simulating multi-source extraction)
    reps.to_csv(f"{RAW_DIR}/crm_reps.csv",           index=False)
    opps.to_csv(f"{RAW_DIR}/crm_opportunities.csv",   index=False)
    revenue.to_csv(f"{RAW_DIR}/erp_revenue.csv",      index=False)
    quotas.to_csv(f"{RAW_DIR}/quota_targets.csv",     index=False)
    forecasts.to_csv(f"{RAW_DIR}/revenue_forecasts.csv", index=False)
    products.to_csv(f"{RAW_DIR}/product_catalog.csv", index=False)
    campaigns.to_csv(f"{RAW_DIR}/campaigns.csv",      index=False)

    print(f"\n  Raw CSVs saved to: {RAW_DIR}")
    return reps, opps, revenue, quotas, forecasts, products, campaigns


if __name__ == '__main__':
    run()
