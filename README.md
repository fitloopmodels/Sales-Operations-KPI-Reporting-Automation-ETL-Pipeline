[README.md](https://github.com/user-attachments/files/29179720/README.md)
# Sales Operations KPI Reporting Automation & ETL Pipeline

End-to-end data pipeline and reporting system for sales operations analytics. Covers ETL, automated KPI reporting, statistical campaign analysis, and executive dashboarding.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data Extraction & Transform | Python, Pandas, SQL |
| Database | SQLite (swap for PostgreSQL/Snowflake in prod) |
| Statistical Analysis | Statsmodels, SciPy |
| Reporting | Excel (openpyxl), Power BI (DAX + Power Query) |
| Scheduling | Python `schedule` library |

---

## Project Structure

```
sales_ops_etl/
├── data/
│   ├── raw/                  # Simulated source CSVs (CRM, ERP, Marketing)
│   ├── processed/            # Cleaned, consolidated output
│   └── exports/              # Excel/CSV exports for reporting
├── etl/
│   ├── extract.py            # Data extraction from multiple sources
│   ├── transform.py          # Cleaning, enrichment, consolidation
│   ├── load.py               # Load into SQLite warehouse
│   └── pipeline.py           # Orchestrates full ETL run
├── sql/
│   ├── schema.sql            # Warehouse table definitions
│   ├── kpi_queries.sql       # Core KPI metric queries
│   └── views.sql             # Reporting views
├── analysis/
│   ├── kpi_calculator.py     # Win rate, pipeline velocity, quota attainment
│   ├── forecasting.py        # Revenue forecast accuracy
│   └── ab_testing.py         # Campaign A/B tests (t-test, chi-square)
├── reports/
│   └── report_generator.py   # Auto-generates Excel + PowerPoint reports
├── dashboard/
│   ├── dax_measures.md       # All Power BI DAX measures
│   └── power_query.md        # Power Query M scripts
├── tests/
│   └── test_pipeline.py      # Unit tests
├── scheduler.py              # Weekly automation scheduler
├── requirements.txt
└── README.md
```

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic data
python etl/extract.py

# 3. Run full ETL pipeline
python etl/pipeline.py

# 4. Generate KPI report
python reports/report_generator.py

# 5. Run A/B test analysis
python analysis/ab_testing.py

# 6. Start weekly scheduler (keeps running)
python scheduler.py
```

---

## Key KPIs Tracked

- **Win Rate** — Closed Won / Total Qualified Opportunities
- **Pipeline Velocity** — (Opportunities × Win Rate × Avg Deal Size) / Sales Cycle Length
- **Quota Attainment** — Actual Revenue / Quota Target
- **Revenue Forecast Accuracy** — 1 - |Actual - Forecast| / Actual
- **Sales Cycle Length** — Avg days from opportunity created to closed
- **MoM Revenue Variance** — Month-over-month revenue change %

---

## Statistical Analysis

Campaign effectiveness is measured using:
- **Independent t-test** — Compare mean deal sizes between campaign groups
- **Chi-square test** — Compare win rate proportions between campaign groups
- Results exported to Excel and PowerPoint for stakeholder presentation

---

## Power BI Dashboard

DAX measures and Power Query scripts are in `/dashboard/`. Connect Power BI Desktop to the SQLite `.db` file or the CSV exports in `/data/exports/`.

Visuals include:
- Pipeline funnel by stage
- Territory performance heatmap
- MoM revenue variance waterfall
- Win rate trend line
- Quota attainment gauge
