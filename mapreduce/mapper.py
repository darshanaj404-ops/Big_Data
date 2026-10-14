#!/usr/bin/env python3
"""
Hadoop MapReduce Streaming Mapper: Historical Taxi Pickup Aggregator
Reads raw or sampled CSV lines from sys.stdin, parses pickup timestamp and zone ID,
and emits tab-separated key-value pairs:
    <PULocationID>\t<hour>\t1
"""

import sys
from datetime import datetime


def parse_and_emit():
    for line_idx, line in enumerate(sys.stdin):
        line = line.strip()
        if not line:
            continue

        # Skip header row if present
        if line.startswith("tpep_pickup_datetime") or "PULocationID" in line:
            continue

        parts = line.split(",")
        if len(parts) < 7:
            continue

        # Extract pickup timestamp (col 0) and PULocationID (col 2 in standard sample)
        pickup_str = parts[0].strip()
        pu_location_str = parts[2].strip()

        try:
            pu_location_id = int(pu_location_str)
            # Filter valid NYC TLC zone IDs (1 to 265)
            if pu_location_id < 1 or pu_location_id > 265:
                continue

            # Parse hour from timestamp (e.g. "2024-01-01 00:00:08")
            dt = datetime.strptime(pickup_str, "%Y-%m-%d %H:%M:%S")
            hour = dt.hour

            # Emit tab-delimited key and count value
            # Key: (PULocationID, hour), Value: 1
            print(f"{pu_location_id}\t{hour}\t1")
        except (ValueError, IndexError):
            # Gracefully ignore malformed datetime or integer rows
            continue


if __name__ == "__main__":
    parse_and_emit()
