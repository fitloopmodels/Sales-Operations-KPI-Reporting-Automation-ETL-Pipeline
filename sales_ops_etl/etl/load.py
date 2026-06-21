"""
load.py
-------
Loads cleaned, processed data into the SQLite data warehouse.
In production, swap sqlite:/// connection string for:
  - PostgreSQL: postgresql://user:pw@host/db
  - Snowflake:  snowflake://user:pw@account/db/schema
"""

import os
import sqlite3
import pandas as pd

PROC_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
DB_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales_ops.db')
SQL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'sql')


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _execute_sql_file(conn: sqlite3.Connection, filepath: str):
    with open(filepath, 'r') as f:
        sql = f.read()
    conn.executescript(sql)


def create_schema(conn: sqlite3.Connection):
    _execute_sql_file(conn, os.path.join(SQL_DIR, 'schema.sql'))
    _execute_sql_file(conn, os.path.join(SQL_DIR, 'views.sql'))
    conn.commit()
    print("  Schema + views created")


def load_table(conn: sqlite3.Connection, df: pd.DataFrame, table: str, mode: str = 'replace'):
    """Load a DataFrame into a SQLite table."""
    df.to_sql(table, conn, if_exists=mode, index=False)
    print(f"  Loaded {len(df):>6,} rows → {table}")


def run():
    print("── Loading to warehouse ─────────────────────────────────")

    conn = get_connection()
    create_schema(conn)

    tables = {
        'dim_reps':            'dim_reps.csv',
        'dim_products':        'dim_products.csv',
        'dim_campaigns':       'dim_campaigns.csv',
        'dim_date':            'dim_date.csv',
        'fact_opportunities':  'fact_opportunities.csv',
        'fact_revenue':        'fact_revenue.csv',
        'fact_quotas':         'fact_quotas.csv',
        'fact_forecasts':      'fact_forecasts.csv',
    }

    for table_name, csv_file in tables.items():
        df = pd.read_csv(os.path.join(PROC_DIR, csv_file))
        load_table(conn, df, table_name)

    conn.commit()
    conn.close()
    print(f"\n  Warehouse: {DB_PATH}")


def query(sql: str) -> pd.DataFrame:
    """Utility: run a SQL query and return a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df


if __name__ == '__main__':
    run()
