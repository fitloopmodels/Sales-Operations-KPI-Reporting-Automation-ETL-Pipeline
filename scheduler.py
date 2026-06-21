"""
scheduler.py
------------
Automates weekly ETL + reporting using the `schedule` library.
In production, replace with Airflow, Prefect, or a cron job.

Schedule:
  - Every Monday 06:00 → Full ETL pipeline
  - Every Monday 06:30 → Generate KPI reports
  - Every Monday 07:00 → Run A/B tests
"""

import sys
import os
import schedule
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'etl'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'reports'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'analysis'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log'),
    ]
)
log = logging.getLogger(__name__)


def job_etl():
    log.info("── JOB: ETL Pipeline ─────────────────────────")
    try:
        import pipeline
        pipeline.run_pipeline()
        log.info("ETL pipeline completed successfully")
    except Exception as e:
        log.error(f"ETL pipeline FAILED: {e}", exc_info=True)


def job_reports():
    log.info("── JOB: Report Generation ────────────────────")
    try:
        import report_generator
        excel, pptx = report_generator.run()
        log.info(f"Reports generated: {excel}, {pptx}")
    except Exception as e:
        log.error(f"Report generation FAILED: {e}", exc_info=True)


def job_ab_test():
    log.info("── JOB: A/B Test Analysis ────────────────────")
    try:
        import ab_testing
        ab_testing.run()
        log.info("A/B test analysis completed")
    except Exception as e:
        log.error(f"A/B test FAILED: {e}", exc_info=True)


def setup_schedule():
    # Weekly on Monday
    schedule.every().monday.at("06:00").do(job_etl)
    schedule.every().monday.at("06:30").do(job_reports)
    schedule.every().monday.at("07:00").do(job_ab_test)

    # Also run immediately on start (useful for testing)
    log.info("Scheduler started. Running initial jobs now...")
    job_etl()
    job_reports()
    job_ab_test()

    log.info("Schedule set: ETL Mon 06:00 | Reports Mon 06:30 | A/B Mon 07:00")
    log.info("Waiting for next scheduled run... (Ctrl+C to stop)")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == '__main__':
    setup_schedule()
