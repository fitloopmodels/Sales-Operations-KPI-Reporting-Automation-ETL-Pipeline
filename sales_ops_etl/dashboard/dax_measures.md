# Power BI DAX Measures

Connect Power BI Desktop to `data/sales_ops.db` via ODBC or to the CSV exports in `data/exports/`.

---

## How to Connect

**Option A — CSV Exports (easiest):**
1. Open Power BI Desktop
2. Get Data → Text/CSV
3. Import all CSVs from `data/exports/`
4. Build relationships on `rep_id` and `month_year`

**Option B — SQLite DB:**
1. Install `ODBC Driver for SQLite`
2. Get Data → ODBC → point to `data/sales_ops.db`
3. Import tables: `fact_revenue`, `fact_opportunities`, `fact_quotas`, `dim_reps`, `dim_products`

---

## Table Relationships

```
dim_reps ──< fact_opportunities >── dim_products
dim_reps ──< fact_revenue
dim_reps ──< fact_quotas
dim_reps ──< fact_forecasts
dim_campaigns ──< fact_opportunities
dim_date ──< fact_opportunities (on close_date)
```

---

## Core DAX Measures

```dax
-- Total Revenue
Total Revenue =
SUM(fact_revenue[revenue])

-- Win Rate
Win Rate =
DIVIDE(
    COUNTROWS(FILTER(fact_opportunities, fact_opportunities[is_won] = 1)),
    COUNTROWS(FILTER(fact_opportunities, fact_opportunities[is_closed] = 1)),
    0
)

-- Quota Attainment
Quota Attainment =
DIVIDE(
    [Total Revenue],
    SUM(fact_quotas[quota_amount]),
    0
)

-- Pipeline Velocity
Pipeline Velocity =
DIVIDE(
    COUNTROWS(fact_opportunities)
        * [Win Rate]
        * AVERAGE(fact_opportunities[deal_value]),
    AVERAGEX(
        FILTER(fact_opportunities, fact_opportunities[is_closed] = 1),
        fact_opportunities[days_in_pipeline]
    ),
    0
)

-- Forecast Accuracy
Forecast Accuracy =
VAR actual   = [Total Revenue]
VAR forecast = SUM(fact_forecasts[forecasted_rev])
RETURN
    1 - DIVIDE(ABS(actual - forecast), actual, 0)

-- MoM Revenue Variance %
MoM Revenue Variance % =
VAR current_month =
    CALCULATE([Total Revenue],
              DATESMTD(dim_date[date_id]))
VAR prev_month =
    CALCULATE([Total Revenue],
              PREVIOUSMONTH(dim_date[date_id]))
RETURN
    DIVIDE(current_month - prev_month, prev_month, 0)

-- Average Sales Cycle (days)
Avg Sales Cycle Days =
AVERAGEX(
    FILTER(fact_opportunities, fact_opportunities[is_closed] = 1),
    fact_opportunities[days_in_pipeline]
)

-- Weighted Pipeline Value
Weighted Pipeline =
SUMX(
    FILTER(fact_opportunities, fact_opportunities[is_closed] = 0),
    fact_opportunities[deal_value] * fact_opportunities[probability] / 100
)

-- Revenue vs Quota (KPI Card)
Revenue vs Quota =
[Total Revenue] - SUM(fact_quotas[quota_amount])

-- Attainment Band (for conditional formatting)
Attainment Band =
SWITCH(
    TRUE(),
    [Quota Attainment] >= 1.2,  "Exceeds (>120%)",
    [Quota Attainment] >= 1.0,  "On Track (100-120%)",
    [Quota Attainment] >= 0.8,  "Near Target (80-100%)",
    [Quota Attainment] >= 0.5,  "At Risk (50-80%)",
    "Critical (<50%)"
)

-- Closed Won Count
Closed Won Count =
COUNTROWS(
    FILTER(fact_opportunities, fact_opportunities[is_won] = 1)
)

-- Open Pipeline Count
Open Pipeline Count =
COUNTROWS(
    FILTER(fact_opportunities, fact_opportunities[is_closed] = 0)
)

-- Running Total Revenue (for trend line)
Running Total Revenue =
CALCULATE(
    [Total Revenue],
    FILTER(
        ALL(dim_date),
        dim_date[date_id] <= MAX(dim_date[date_id])
    )
)
```

---

## Suggested Dashboard Pages

### Page 1 — Executive Overview
- KPI Cards: Total Revenue | Win Rate | Quota Attainment | Avg Sales Cycle
- Line chart: Monthly Revenue trend with MoM variance %
- Bar chart: Quota Attainment by Rep (colour coded by Attainment Band)

### Page 2 — Pipeline Health
- Funnel visual: Opportunities by Stage
- Scatter: Deal Value vs Days in Pipeline (by Rep)
- Table: Open pipeline by Territory with Weighted Pipeline value

### Page 3 — Territory Performance
- Map or Matrix: Revenue and Win Rate by Region / Territory
- Bar: Top 10 Reps by Revenue
- Heatmap: Attainment by Rep × Month

### Page 4 — Campaign Analysis
- Bar: Win Rate by Campaign Type (A vs B)
- Bar: Avg Deal Size by Campaign
- Table: Full campaign stats with conditional formatting

---

## Conditional Formatting Rules

For Quota Attainment column:
- ≥ 1.2  → Green  (`#10B981`)
- ≥ 1.0  → Blue   (`#2563EB`)
- ≥ 0.8  → Orange (`#F59E0B`)
- < 0.8  → Red    (`#EF4444`)
