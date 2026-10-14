"""
Module: mapreduce/run_mapreduce_local.py
Description: Executes the Python MapReduce streaming workflow locally (mapper | sort | reducer)
             simulating Hadoop Streaming mechanics, generating the historical baseline table.
Author: Big Data Senior Engineer & Project Mentor
"""

import sys
import subprocess
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def run_local_streaming_pipeline(
    sample_csv_path: Path,
    output_baseline_csv: Path,
    mapper_script: Path,
    reducer_script: Path
) -> Path:
    """
    Simulates the exact Unix pipeline used by Hadoop Streaming:
      python mapper.py < sample_csv | sort | python reducer.py > baseline.tsv
    And converts the output into structured, documented CSV format.
    """
    logger.info("Executing MapReduce Streaming pipeline locally...")
    logger.info(f"  Input: {sample_csv_path.name}")
    logger.info(f"  Mapper: {mapper_script.name}")
    logger.info(f"  Reducer: {reducer_script.name}")

    if not sample_csv_path.exists():
        raise FileNotFoundError(f"Input sample CSV not found at: {sample_csv_path}")

    python_executable = sys.executable

    # 1. Run Mapper reading from sample CSV
    with open(sample_csv_path, "r", encoding="utf-8") as in_f:
        p_mapper = subprocess.Popen(
            [python_executable, str(mapper_script)],
            stdin=in_f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        mapper_out, mapper_err = p_mapper.communicate()

    if p_mapper.returncode != 0:
        raise RuntimeError(f"Mapper failed with error:\n{mapper_err}")

    # 2. Simulate Hadoop framework shuffle & sort
    lines = [line.strip() for line in mapper_out.splitlines() if line.strip()]
    sorted_lines = sorted(
        lines,
        key=lambda x: (int(x.split("\t")[0]), int(x.split("\t")[1]))
    )
    sorted_input = "\n".join(sorted_lines) + "\n"

    # 3. Run Reducer reading from sorted mapper lines
    p_reducer = subprocess.Popen(
        [python_executable, str(reducer_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    reducer_out, reducer_err = p_reducer.communicate(input=sorted_input)

    if p_reducer.returncode != 0:
        raise RuntimeError(f"Reducer failed with error:\n{reducer_err}")

    # 4. Parse Reducer TSV and build baseline dataframe
    records = []
    for line in reducer_out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            loc_id, hr, total = int(parts[0]), int(parts[1]), int(parts[2])
            # Sample spans ~1.5 days; compute robust normalized baseline per hour
            baseline_avg = round(total / 1.5, 2)
            records.append({
                "LocationID": loc_id,
                "hour": hr,
                "total_pickups": total,
                "baseline_pickups": baseline_avg
            })

    baseline_df = pd.DataFrame(records)
    output_baseline_csv.parent.mkdir(parents=True, exist_ok=True)
    baseline_df.to_csv(output_baseline_csv, index=False)

    logger.info(f"Historical baseline generated successfully: {output_baseline_csv.name}")
    logger.info(f"  Total baseline pairs: {len(baseline_df):,}")
    logger.info(f"  Unique zones covered: {baseline_df['LocationID'].nunique()}")
    logger.info(f"  Sum of all pickups aggregated: {baseline_df['total_pickups'].sum():,}")

    return output_baseline_csv


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    sample_csv = base_dir / "data" / "sample" / "yellow_tripdata_sample_100k.csv"
    output_csv = base_dir / "data" / "processed" / "historical_baseline.csv"
    mapper = base_dir / "mapreduce" / "mapper.py"
    reducer = base_dir / "mapreduce" / "reducer.py"

    run_local_streaming_pipeline(sample_csv, output_csv, mapper, reducer)
