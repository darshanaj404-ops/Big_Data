"""
Module: mapreduce/verify_baseline.py
Description: Independently verifies the mathematical correctness of MapReduce baseline
             aggregations by comparing against direct pandas group-by computations.
Author: Big Data Senior Engineer & Project Mentor
"""

import sys
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def verify_baseline_accuracy(sample_csv_path: Path, baseline_csv_path: Path) -> bool:
    """
    Computes ground truth directly from sample CSV and asserts 100% equivalence
    with the MapReduce output.
    """
    logger.info("Starting independent mathematical verification of MapReduce output...")

    if not sample_csv_path.exists():
        raise FileNotFoundError(f"Missing sample file: {sample_csv_path}")
    if not baseline_csv_path.exists():
        raise FileNotFoundError(f"Missing baseline file: {baseline_csv_path}")

    # 1. Ground truth calculation
    raw_df = pd.read_csv(sample_csv_path)
    raw_df["hour"] = pd.to_datetime(raw_df["tpep_pickup_datetime"]).dt.hour
    ground_truth = (
        raw_df.groupby(["PULocationID", "hour"])
        .size()
        .reset_index(name="expected_pickups")
    )

    # 2. MapReduce baseline output
    baseline_df = pd.read_csv(baseline_csv_path)

    # 3. Merge and compare
    merged = pd.merge(
        ground_truth,
        baseline_df,
        left_on=["PULocationID", "hour"],
        right_on=["LocationID", "hour"],
        how="outer"
    )

    # Assertions
    mismatches = merged[merged["expected_pickups"] != merged["total_pickups"]]
    if len(mismatches) > 0:
        logger.error(f"Found {len(mismatches)} mismatched zone/hour aggregations!")
        logger.error(f"\n{mismatches.head()}")
        return False

    total_expected = ground_truth["expected_pickups"].sum()
    total_mr = baseline_df["total_pickups"].sum()

    logger.info(f"Verification Successful!")
    logger.info(f"  Ground truth total pickups: {total_expected:,}")
    logger.info(f"  MapReduce total pickups:    {total_mr:,}")
    logger.info(f"  Aggregated zone-hour pairs: {len(baseline_df):,}")
    logger.info("  Zero discrepancies found between MapReduce output and ground truth.")
    return True


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    sample_csv = base_dir / "data" / "sample" / "yellow_tripdata_sample_100k.csv"
    baseline_csv = base_dir / "data" / "processed" / "historical_baseline.csv"

    success = verify_baseline_accuracy(sample_csv, baseline_csv)
    sys.exit(0 if success else 1)
