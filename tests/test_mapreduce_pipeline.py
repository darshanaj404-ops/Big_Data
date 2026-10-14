"""
Phase 3 Acceptance Test: MapReduce Streaming & Baseline Aggregation
Tests mapper logic, reducer aggregation, key sorting, and baseline output.
"""

import sys
import subprocess
from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def base_dir():
    return Path(__file__).resolve().parent.parent


def test_mapper_unit_logic(base_dir):
    """Test mapper with controlled mock CSV lines."""
    mapper_path = base_dir / "mapreduce" / "mapper.py"

    test_input = (
        "tpep_pickup_datetime,tpep_dropoff_datetime,PULocationID,DOLocationID,passenger_count,trip_distance,fare_amount\n"
        "2024-01-01 14:05:00,2024-01-01 14:20:00,237,161,1,2.5,12.5\n"
        "2024-01-01 14:45:00,2024-01-01 15:00:00,237,236,2,1.2,8.0\n"
        "2024-01-01 15:10:00,2024-01-01 15:25:00,161,237,1,3.0,15.0\n"
        "invalid_date_row,invalid,999,999,1,0.0,0.0\n" # invalid zone & date
    )

    proc = subprocess.Popen(
        [sys.executable, str(mapper_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=test_input)

    assert proc.returncode == 0
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]

    # Expected 3 valid rows: two for (237, 14) and one for (161, 15)
    assert len(lines) == 3
    assert "237\t14\t1" in lines
    assert "161\t15\t1" in lines


def test_reducer_unit_logic(base_dir):
    """Test reducer with sorted key-value pairs."""
    reducer_path = base_dir / "mapreduce" / "reducer.py"

    sorted_input = (
        "161\t15\t1\n"
        "237\t14\t1\n"
        "237\t14\t1\n"
        "237\t14\t1\n"
    )

    proc = subprocess.Popen(
        [sys.executable, str(reducer_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=sorted_input)

    assert proc.returncode == 0
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]

    assert len(lines) == 2
    assert "161\t15\t1" in lines
    assert "237\t14\t3" in lines


def test_historical_baseline_output_file(base_dir):
    """Verify historical_baseline.csv structure and mathematical consistency."""
    baseline_path = base_dir / "data" / "processed" / "historical_baseline.csv"
    assert baseline_path.exists(), "historical_baseline.csv has not been generated"
    assert baseline_path.stat().st_size > 0, "historical_baseline.csv is empty"

    df = pd.read_csv(baseline_path)
    required_cols = {"LocationID", "hour", "total_pickups", "baseline_pickups"}
    assert required_cols.issubset(set(df.columns))

    assert (df["hour"] >= 0).all() and (df["hour"] <= 23).all()
    assert (df["total_pickups"] > 0).all()
    assert (df["baseline_pickups"] > 0).all()
    assert df["total_pickups"].sum() == 100000, "Sum of all pickups must equal the 100,000 sample count"
