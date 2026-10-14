#!/usr/bin/env python3
"""
Hadoop MapReduce Streaming Reducer: Historical Taxi Pickup Aggregator
Reads sorted tab-separated (PULocationID, hour, 1) entries from sys.stdin,
sums pickup counts per (PULocationID, hour) pair, and emits:
    <PULocationID>\t<hour>\t<total_pickups>
"""

import sys


def reduce_pickups():
    current_key = None
    current_count = 0

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) != 3:
            continue

        pu_location_str, hour_str, count_str = parts

        try:
            pu_location_id = int(pu_location_str)
            hour = int(hour_str)
            count = int(count_str)
        except ValueError:
            continue

        key = (pu_location_id, hour)

        # Standard Hadoop streaming key boundary detection
        if current_key == key:
            current_count += count
        else:
            if current_key is not None:
                # Emit aggregated pickup count for previous key
                print(f"{current_key[0]}\t{current_key[1]}\t{current_count}")
            current_key = key
            current_count = count

    # Emit final key accumulation
    if current_key is not None:
        print(f"{current_key[0]}\t{current_key[1]}\t{current_count}")


if __name__ == "__main__":
    reduce_pickups()
