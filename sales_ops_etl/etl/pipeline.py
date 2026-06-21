"""
pipeline.py
-----------
Orchestrates the full ETL run in sequence:
  Extract → Transform → Load

Run this file to rebuild the entire warehouse from scratch.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import extract
import transform
import load


def run_pipeline():
    start = time.time()
    print("=" * 56)
    print("  SALES OPS ETL PIPELINE")
    print("=" * 56)

    # Step 1: Extract
    extract.run()

    # Step 2: Transform
    transform.run()

    # Step 3: Load
    load.run()

    elapsed = time.time() - start
    print("\n" + "=" * 56)
    print(f"  Pipeline complete in {elapsed:.2f}s")
    print("=" * 56)


if __name__ == '__main__':
    run_pipeline()
