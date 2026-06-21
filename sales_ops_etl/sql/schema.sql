-- ============================================================
-- Sales Operations Data Warehouse Schema
-- ============================================================

-- Dimension: Sales Representatives
CREATE TABLE IF NOT EXISTS dim_reps (
    rep_id      TEXT PRIMARY KEY,
    rep_name    TEXT NOT NULL,
    region      TEXT NOT NULL,
    territory   TEXT NOT NULL,
    manager     TEXT,
    hire_date   DATE
);

-- Dimension: Products
CREATE TABLE IF NOT EXISTS dim_products (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    unit_price      REAL NOT NULL,
    cost_price      REAL NOT NULL
);

-- Dimension: Campaigns
CREATE TABLE IF NOT EXISTS dim_campaigns (
    campaign_id     TEXT PRIMARY KEY,
    campaign_name   TEXT NOT NULL,
    campaign_type   TEXT NOT NULL,  -- 'A' or 'B' for A/B testing
    start_date      DATE,
    end_date        DATE,
    budget          REAL
);

-- Dimension: Date
CREATE TABLE IF NOT EXISTS dim_date (
    date_id         TEXT PRIMARY KEY,  -- YYYY-MM-DD
    year            INTEGER,
    quarter         INTEGER,
    month           INTEGER,
    month_name      TEXT,
    week            INTEGER,
    day_of_week     INTEGER,
    is_weekday      INTEGER
);

-- Fact: Opportunities (CRM pipeline)
CREATE TABLE IF NOT EXISTS fact_opportunities (
    opportunity_id      TEXT PRIMARY KEY,
    rep_id              TEXT REFERENCES dim_reps(rep_id),
    product_id          TEXT REFERENCES dim_products(product_id),
    campaign_id         TEXT REFERENCES dim_campaigns(campaign_id),
    created_date        DATE NOT NULL,
    close_date          DATE,
    stage               TEXT NOT NULL,  -- Prospecting, Qualification, Proposal, Negotiation, Closed Won, Closed Lost
    deal_value          REAL NOT NULL,
    probability         REAL,
    days_in_pipeline    INTEGER,
    is_won              INTEGER,        -- 1 = Won, 0 = Lost/Open
    is_closed           INTEGER        -- 1 = Closed (won or lost), 0 = open
);

-- Fact: Revenue (actual bookings)
CREATE TABLE IF NOT EXISTS fact_revenue (
    revenue_id      TEXT PRIMARY KEY,
    opportunity_id  TEXT REFERENCES fact_opportunities(opportunity_id),
    rep_id          TEXT REFERENCES dim_reps(rep_id),
    product_id      TEXT REFERENCES dim_products(product_id),
    close_date      DATE NOT NULL,
    revenue         REAL NOT NULL,
    month_year      TEXT NOT NULL  -- YYYY-MM for easy grouping
);

-- Fact: Quotas
CREATE TABLE IF NOT EXISTS fact_quotas (
    quota_id        TEXT PRIMARY KEY,
    rep_id          TEXT REFERENCES dim_reps(rep_id),
    month_year      TEXT NOT NULL,
    quota_amount    REAL NOT NULL
);

-- Fact: Forecasts
CREATE TABLE IF NOT EXISTS fact_forecasts (
    forecast_id     TEXT PRIMARY KEY,
    rep_id          TEXT REFERENCES dim_reps(rep_id),
    month_year      TEXT NOT NULL,
    forecasted_rev  REAL NOT NULL,
    forecast_date   DATE NOT NULL
);
