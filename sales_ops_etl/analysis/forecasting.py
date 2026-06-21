"""
forecasting.py
--------------
Revenue forecasting using Exponential Smoothing (Holt-Winters).
Compares forecast vs actual and computes accuracy metrics.
"""

import os
import sys
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'etl'))
import load

EXPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)


def get_monthly_revenue() -> pd.DataFrame:
    sql = """
        SELECT month_year, SUM(revenue) AS total_revenue
        FROM fact_revenue
        GROUP BY month_year
        ORDER BY month_year
    """
    df = load.query(sql)
    df.index = pd.PeriodIndex(df['month_year'], freq='M')
    return df


def fit_forecast(series: pd.Series, forecast_periods: int = 3) -> dict:
    """Fit Holt-Winters ETS model and forecast next N months."""
    model = ExponentialSmoothing(
        series,
        trend='add',
        seasonal=None,
        initialization_method='estimated'
    )
    fit = model.fit(optimized=True)

    forecast  = fit.forecast(forecast_periods)
    fitted    = fit.fittedvalues

    # Accuracy metrics on in-sample fit
    residuals = series - fitted
    mae   = np.abs(residuals).mean()
    rmse  = np.sqrt((residuals**2).mean())
    mape  = (np.abs(residuals / series) * 100).replace([np.inf, -np.inf], np.nan).dropna().mean()

    return {
        'model':      fit,
        'fitted':     fitted,
        'forecast':   forecast,
        'mae':        round(mae, 2),
        'rmse':       round(rmse, 2),
        'mape':       round(mape, 2),
        'alpha':      round(fit.params.get('smoothing_level', 0), 4),
    }


def plot_forecast(series: pd.Series, fitted: pd.Series, forecast: pd.Series):
    fig, ax = plt.subplots(figsize=(12, 5))
    series.plot(ax=ax,  label='Actual Revenue',    color='#2563EB', linewidth=2, marker='o', ms=4)
    fitted.plot(ax=ax,  label='Fitted (ETS model)',color='#10B981', linewidth=1.5, linestyle='--')
    forecast.plot(ax=ax,label='Forecast',          color='#F59E0B', linewidth=2,  linestyle='--', marker='s', ms=6)

    ax.set_title('Monthly Revenue — Actual vs ETS Forecast', fontsize=14, fontweight='bold')
    ax.set_xlabel('Month')
    ax.set_ylabel('Revenue ($)')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    path = os.path.join(EXPORT_DIR, 'revenue_forecast_chart.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def run():
    print("── Revenue Forecasting ──────────────────────────────────")

    df = get_monthly_revenue()
    series = df['total_revenue'].astype(float)

    result = fit_forecast(series, forecast_periods=3)

    print(f"  Training months: {len(series)}")
    print(f"  MAE:  ${result['mae']:>12,.2f}")
    print(f"  RMSE: ${result['rmse']:>12,.2f}")
    print(f"  MAPE: {result['mape']:>11.2f}%")
    print(f"  Smoothing α: {result['alpha']}")

    print("\n  3-Month Forecast:")
    for period, value in result['forecast'].items():
        print(f"    {period}: ${value:>12,.2f}")

    chart_path = plot_forecast(series, result['fitted'], result['forecast'])
    print(f"\n  Chart saved: {chart_path}")

    # Export forecast table
    forecast_df = pd.DataFrame({
        'month_year': result['forecast'].index.astype(str),
        'forecasted_revenue': result['forecast'].values.round(2)
    })
    forecast_df.to_csv(os.path.join(EXPORT_DIR, 'revenue_forecast.csv'), index=False)

    return result


if __name__ == '__main__':
    run()
