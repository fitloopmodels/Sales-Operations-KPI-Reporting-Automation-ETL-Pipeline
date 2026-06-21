"""
test_pipeline.py
----------------
Unit tests for ETL transforms and KPI calculations.
Run: python -m pytest tests/test_pipeline.py -v
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'etl'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis'))

import transform


# ── Transform Tests ───────────────────────────────────────────

class TestTransformReps:
    def test_deduplication(self):
        df = pd.DataFrame({'rep_id': ['R001', 'R001', 'R002'],
                           'rep_name': ['Alice', 'Alice', 'Bob'],
                           'region': ['North', 'North', 'South'],
                           'territory': ['NYC', 'NYC', 'Texas'],
                           'manager': ['Mgr1', 'Mgr1', 'Mgr2'],
                           'hire_date': ['2020-01-01', '2020-01-01', '2021-06-15']})
        result = transform.transform_reps(df)
        assert len(result) == 2

    def test_drops_nulls(self):
        df = pd.DataFrame({'rep_id': ['R001', None],
                           'rep_name': ['Alice', 'Bob'],
                           'region': ['North', 'South'],
                           'territory': ['NYC', 'Texas'],
                           'manager': ['M', 'M'],
                           'hire_date': ['2020-01-01', '2021-01-01']})
        result = transform.transform_reps(df)
        assert len(result) == 1

    def test_name_title_case(self):
        df = pd.DataFrame({'rep_id': ['R001'],
                           'rep_name': ['alice smith'],
                           'region': ['north'],
                           'territory': ['nyc metro'],
                           'manager': ['mgr'],
                           'hire_date': ['2020-01-01']})
        result = transform.transform_reps(df)
        assert result['rep_name'].iloc[0] == 'Alice Smith'


class TestTransformOpportunities:
    def _base(self):
        return pd.DataFrame({
            'opportunity_id':   ['O001', 'O002'],
            'rep_id':           ['R001', 'R001'],
            'product_id':       ['P001', 'P001'],
            'campaign_id':      ['C001', 'C001'],
            'created_date':     ['2023-01-15', '2023-02-10'],
            'close_date':       ['2023-03-01', '2023-04-15'],
            'stage':            ['Closed Won', 'Closed Lost'],
            'deal_value':       [10000, 8000],
            'probability':      [100, 0],
            'days_in_pipeline': [45, 63],
            'is_won':           [1, 0],
            'is_closed':        [1, 1],
        })

    def test_negative_deal_value_dropped(self):
        df = self._base()
        df.loc[0, 'deal_value'] = -500
        result = transform.transform_opportunities(df)
        assert len(result) == 1

    def test_closed_no_date_dropped(self):
        df = self._base()
        df.loc[0, 'close_date'] = None
        result = transform.transform_opportunities(df)
        assert 'O001' not in result['opportunity_id'].values

    def test_invalid_stage_corrected(self):
        df = self._base()
        df.loc[0, 'stage'] = 'GARBAGE'
        result = transform.transform_opportunities(df)
        assert result.loc[result['opportunity_id'] == 'O001', 'stage'].iloc[0] == 'Prospecting'

    def test_weighted_value_computed(self):
        df = self._base()
        result = transform.transform_opportunities(df)
        assert 'weighted_value' in result.columns
        row = result[result['opportunity_id'] == 'O001'].iloc[0]
        assert row['weighted_value'] == round(row['deal_value'] * row['probability'] / 100, 2)

    def test_probability_clipped(self):
        df = self._base()
        df.loc[0, 'probability'] = 150  # > 100
        result = transform.transform_opportunities(df)
        assert result.loc[result['opportunity_id'] == 'O001', 'probability'].iloc[0] <= 100


class TestTransformRevenue:
    def test_zero_revenue_dropped(self):
        df = pd.DataFrame({
            'revenue_id':     ['REV001', 'REV002'],
            'opportunity_id': ['O001', 'O002'],
            'rep_id':         ['R001', 'R001'],
            'product_id':     ['P001', 'P001'],
            'close_date':     ['2023-03-01', '2023-04-01'],
            'revenue':        [10000, 0],
            'month_year':     ['2023-03', '2023-04'],
        })
        result = transform.transform_revenue(df)
        assert len(result) == 1

    def test_month_year_derived(self):
        df = pd.DataFrame({
            'revenue_id':     ['REV001'],
            'opportunity_id': ['O001'],
            'rep_id':         ['R001'],
            'product_id':     ['P001'],
            'close_date':     ['2023-07-15'],
            'revenue':        [5000],
            'month_year':     ['2023-07'],
        })
        result = transform.transform_revenue(df)
        assert result['month_year'].iloc[0] == '2023-07'


class TestDimDate:
    def test_date_range(self):
        df = transform.build_dim_date('2023-01-01', '2023-12-31')
        assert len(df) == 365

    def test_weekday_flag(self):
        df = transform.build_dim_date('2023-01-02', '2023-01-02')  # Monday
        assert df['is_weekday'].iloc[0] == 1

    def test_weekend_flag(self):
        df = transform.build_dim_date('2023-01-07', '2023-01-07')  # Saturday
        assert df['is_weekday'].iloc[0] == 0


# ── KPI Sanity Tests (require DB) ────────────────────────────

class TestKPIRanges:
    """Run only after pipeline has been executed."""

    @pytest.fixture(autouse=True)
    def skip_if_no_db(self):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales_ops.db')
        if not os.path.exists(db_path):
            pytest.skip("Database not found — run etl/pipeline.py first")

    def test_win_rate_in_range(self):
        from analysis import kpi_calculator
        df = kpi_calculator.calc_win_rate()
        assert df['win_rate'].between(0, 1).all(), "Win rates must be between 0 and 1"

    def test_quota_attainment_positive(self):
        from analysis import kpi_calculator
        df = kpi_calculator.calc_quota_attainment()
        assert (df['quota_attainment'] >= 0).all()

    def test_pipeline_velocity_positive(self):
        from analysis import kpi_calculator
        df = kpi_calculator.calc_pipeline_velocity()
        assert (df['pipeline_velocity'] >= 0).all()
