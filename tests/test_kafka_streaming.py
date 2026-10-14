"""
Phase 4 Acceptance Test: Kafka Streaming & Rolling Window Micro-Aggregation
Tests event payload schema, window addition and eviction logic, and snapshot persistence.
"""

import sys
import json
from pathlib import Path
import pandas as pd
import pytest

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from streaming.kafka_producer import build_event_payload, stream_trip_starts
from streaming.kafka_consumer import RollingWindowAggregator, consume_trip_starts


@pytest.fixture(scope="module")
def base_dir():
    return Path(__file__).resolve().parent.parent


def test_event_payload_schema():
    """Verify trip-start streaming event payload has all required schema fields."""
    mock_row = pd.Series({
        "tpep_pickup_datetime": "2024-01-01 14:05:00",
        "PULocationID": 237,
        "DOLocationID": 161,
        "passenger_count": 2,
        "trip_distance": 3.4,
        "fare_amount": 15.0
    })

    payload = build_event_payload(mock_row)

    assert payload["event_type"] == "trip_start"
    assert "event_id" in payload and len(payload["event_id"]) > 10
    assert payload["timestamp"] == "2024-01-01 14:05:00"
    assert payload["pickup_location_id"] == 237
    assert payload["dropoff_location_id"] == 161
    assert payload["passenger_count"] == 2
    assert payload["trip_distance"] == 3.4
    assert payload["fare_amount"] == 15.0


def test_rolling_window_aggregator_eviction():
    """Verify rolling window adds new events and evicts expired events past the cutoff."""
    agg = RollingWindowAggregator(window_minutes=15)

    # Event 1 at 14:00 (Zone 237)
    agg.add_event("2024-01-01 14:00:00", 237)
    # Event 2 at 14:10 (Zone 237)
    agg.add_event("2024-01-01 14:10:00", 237)
    # Event 3 at 14:10 (Zone 161)
    agg.add_event("2024-01-01 14:10:00", 161)

    snap1 = agg.get_snapshot()
    assert snap1["total_window_events"] == 3
    assert snap1["zone_counts"]["237"] == 2
    assert snap1["zone_counts"]["161"] == 1

    # Event 4 at 14:16: event at 14:00 should now be evicted (16 mins old > 15 mins window)
    agg.add_event("2024-01-01 14:16:00", 237)
    snap2 = agg.get_snapshot()

    assert snap2["total_window_events"] == 3  # (event at 14:00 evicted, new one added)
    assert snap2["zone_counts"]["237"] == 2  # 14:10 and 14:16
    assert snap2["zone_counts"]["161"] == 1  # 14:10


def test_streaming_produce_and_consume_cycle(base_dir):
    """Verify end-to-end event production and rolling-window consumption cycle."""
    sample_csv = base_dir / "data" / "sample" / "yellow_tripdata_sample_100k.csv"
    snapshot_output = base_dir / "data" / "processed" / "test_live_window.json"

    # 1. Produce 100 events in dry-run mode
    produced = stream_trip_starts(
        sample_csv_path=sample_csv,
        delay_seconds=0.0,
        max_events=100,
        dry_run=True
    )
    assert produced == 100

    # 2. Consume events
    snapshot = consume_trip_starts(
        output_snapshot_path=snapshot_output,
        window_minutes=30,
        max_events=100,
        read_buffer_fallback=True
    )

    # Because the 100 sample events span across ~35 minutes, a 30-min window will evict
    # events older than the cutoff, resulting in ~95-100 active events
    assert 90 <= snapshot["total_window_events"] <= 100
    assert snapshot["active_zones_count"] > 0
    assert snapshot["data_freshness"] == "ACTIVE"
    assert snapshot_output.exists()
