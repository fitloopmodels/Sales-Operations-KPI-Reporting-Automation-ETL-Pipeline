"""
ab_testing.py
-------------
Statistical hypothesis testing for sales campaign effectiveness.

Tests run:
  1. Independent t-test  — Is mean deal size significantly different between campaign A vs B?
  2. Chi-square test     — Is win rate (proportion) significantly different between A vs B?

Results are exported to Excel for stakeholder presentation.
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'etl'))
import load

EXPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

ALPHA = 0.05  # significance level


def get_campaign_data() -> pd.DataFrame:
    sql = """
        SELECT
            o.opportunity_id,
            o.deal_value,
            o.is_won,
            o.is_closed,
            o.days_in_pipeline,
            c.campaign_id,
            c.campaign_name,
            c.campaign_type
        FROM fact_opportunities o
        JOIN dim_campaigns c ON o.campaign_id = c.campaign_id
        WHERE o.is_closed = 1
    """
    return load.query(sql)


def run_ttest(df: pd.DataFrame, group_col: str, value_col: str,
              group_a: str = 'A', group_b: str = 'B') -> dict:
    """Independent two-sample t-test."""
    a = df[df[group_col] == group_a][value_col].dropna()
    b = df[df[group_col] == group_b][value_col].dropna()

    t_stat, p_val = stats.ttest_ind(a, b, equal_var=False)  # Welch's t-test

    result = {
        'test':          "Independent t-test (Welch's)",
        'metric':        value_col,
        'group_a':       group_a,
        'group_b':       group_b,
        'n_a':           len(a),
        'n_b':           len(b),
        'mean_a':        round(a.mean(), 2),
        'mean_b':        round(b.mean(), 2),
        'mean_diff':     round(b.mean() - a.mean(), 2),
        'mean_diff_pct': round((b.mean() - a.mean()) / a.mean() * 100, 2),
        't_statistic':   round(t_stat, 4),
        'p_value':       round(p_val, 6),
        'alpha':         ALPHA,
        'significant':   p_val < ALPHA,
        'conclusion':    (
            f"Statistically significant difference in {value_col} (p={p_val:.4f} < α={ALPHA}). "
            f"Group {group_b} mean is {abs((b.mean()-a.mean())/a.mean()*100):.1f}% "
            f"{'higher' if b.mean() > a.mean() else 'lower'} than Group {group_a}."
            if p_val < ALPHA else
            f"No statistically significant difference in {value_col} (p={p_val:.4f} ≥ α={ALPHA}). "
            f"Cannot conclude the campaigns perform differently."
        )
    }
    return result


def run_chisquare(df: pd.DataFrame, group_col: str,
                  group_a: str = 'A', group_b: str = 'B') -> dict:
    """Chi-square test for win rate proportions."""
    a = df[df[group_col] == group_a]['is_won']
    b = df[df[group_col] == group_b]['is_won']

    won_a, lost_a = a.sum(), len(a) - a.sum()
    won_b, lost_b = b.sum(), len(b) - b.sum()

    contingency = np.array([[won_a, lost_a],
                             [won_b, lost_b]])
    chi2, p_val, dof, expected = stats.chi2_contingency(contingency)

    win_rate_a = round(won_a / len(a), 4)
    win_rate_b = round(won_b / len(b), 4)

    result = {
        'test':          'Chi-square test',
        'metric':        'win_rate',
        'group_a':       group_a,
        'group_b':       group_b,
        'n_a':           len(a),
        'n_b':           len(b),
        'win_rate_a':    win_rate_a,
        'win_rate_b':    win_rate_b,
        'won_a':         int(won_a),
        'lost_a':        int(lost_a),
        'won_b':         int(won_b),
        'lost_b':        int(lost_b),
        'chi2_statistic':round(chi2, 4),
        'degrees_of_freedom': dof,
        'p_value':       round(p_val, 6),
        'alpha':         ALPHA,
        'significant':   p_val < ALPHA,
        'conclusion':    (
            f"Statistically significant difference in win rate (p={p_val:.4f} < α={ALPHA}). "
            f"Group {group_b} win rate ({win_rate_b:.1%}) vs Group {group_a} ({win_rate_a:.1%}) — "
            f"difference of {abs(win_rate_b - win_rate_a):.1%}."
            if p_val < ALPHA else
            f"No statistically significant difference in win rate (p={p_val:.4f} ≥ α={ALPHA}). "
            f"Groups {group_a} ({win_rate_a:.1%}) and {group_b} ({win_rate_b:.1%}) are comparable."
        )
    }
    return result


def run_effect_size(df: pd.DataFrame, group_col: str, value_col: str,
                    group_a: str = 'A', group_b: str = 'B') -> dict:
    """Cohen's d effect size."""
    a = df[df[group_col] == group_a][value_col].dropna()
    b = df[df[group_col] == group_b][value_col].dropna()
    pooled_std = np.sqrt((a.std()**2 + b.std()**2) / 2)
    d = (b.mean() - a.mean()) / pooled_std if pooled_std > 0 else 0

    magnitude = 'Negligible' if abs(d) < 0.2 else \
                'Small'      if abs(d) < 0.5 else \
                'Medium'     if abs(d) < 0.8 else 'Large'
    return {'cohens_d': round(d, 4), 'effect_magnitude': magnitude}


def summarize_by_campaign(df: pd.DataFrame) -> pd.DataFrame:
    """Per-campaign summary statistics."""
    return df.groupby(['campaign_name', 'campaign_type']).agg(
        total_opps=('opportunity_id', 'count'),
        won_opps=('is_won', 'sum'),
        win_rate=('is_won', 'mean'),
        avg_deal_value=('deal_value', 'mean'),
        median_deal_value=('deal_value', 'median'),
        std_deal_value=('deal_value', 'std'),
        total_revenue=('deal_value', lambda x: x[df.loc[x.index, 'is_won'] == 1].sum()),
        avg_cycle_days=('days_in_pipeline', 'mean'),
    ).round(2).reset_index()


def run():
    print("── Running A/B Tests ────────────────────────────────────")

    df = get_campaign_data()
    print(f"  Dataset: {len(df)} closed opportunities across {df['campaign_type'].nunique()} campaign types")

    # Summary stats
    summary = summarize_by_campaign(df)
    print(f"\n  Campaign Summary:")
    print(summary[['campaign_name', 'campaign_type', 'total_opps', 'win_rate', 'avg_deal_value']].to_string(index=False))

    # Test 1: T-test on deal value
    ttest_result   = run_ttest(df, 'campaign_type', 'deal_value')
    effect         = run_effect_size(df, 'campaign_type', 'deal_value')
    ttest_result.update(effect)

    # Test 2: Chi-square on win rate
    chi2_result    = run_chisquare(df, 'campaign_type')

    print(f"\n  T-TEST (Deal Value):")
    print(f"    Group A mean:  ${ttest_result['mean_a']:,.2f}")
    print(f"    Group B mean:  ${ttest_result['mean_b']:,.2f}")
    print(f"    t-statistic:   {ttest_result['t_statistic']}")
    print(f"    p-value:       {ttest_result['p_value']}")
    print(f"    Significant:   {ttest_result['significant']}")
    print(f"    Effect size:   {ttest_result['cohens_d']} ({ttest_result['effect_magnitude']})")
    print(f"    → {ttest_result['conclusion']}")

    print(f"\n  CHI-SQUARE (Win Rate):")
    print(f"    Group A win rate: {chi2_result['win_rate_a']:.1%}")
    print(f"    Group B win rate: {chi2_result['win_rate_b']:.1%}")
    print(f"    χ² statistic:     {chi2_result['chi2_statistic']}")
    print(f"    p-value:          {chi2_result['p_value']}")
    print(f"    Significant:      {chi2_result['significant']}")
    print(f"    → {chi2_result['conclusion']}")

    # Export to Excel
    export_path = os.path.join(EXPORT_DIR, 'ab_test_results.xlsx')
    with pd.ExcelWriter(export_path, engine='openpyxl') as writer:
        summary.to_excel(writer, sheet_name='Campaign Summary', index=False)
        pd.DataFrame([ttest_result]).to_excel(writer, sheet_name='T-Test Results', index=False)
        pd.DataFrame([chi2_result]).to_excel(writer, sheet_name='Chi-Square Results', index=False)

    print(f"\n  Results exported: {export_path}")
    return summary, ttest_result, chi2_result


if __name__ == '__main__':
    run()
