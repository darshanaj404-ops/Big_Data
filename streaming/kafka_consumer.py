"""
Module: streaming/kafka_consumer.py
Description: Ingests real-time taxi trip-start events from Apache Kafka,
             maintains a rolling micro-aggregation window, and outputs live zone counts.
Author: Big Data Senior Engineer & Project Mentor
"""

import sys
import time
import json
import argparse
import logging
from collections import deque, Counter
from datetime import datetime, timedelta
from pathlib import Path
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "configs" / "app_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class RollingWindowAggregator:
    """
    Maintains a time-based rolling window of trip starts.
    Evicts expired events to compute real-time pickup velocity per taxi zone.
    """
    def __init__(self, window_minutes: int = 15):
        self.window_minutes = window_minutes
        self.window_delta = timedelta(minutes=window_minutes)
        self.events = deque()  # stores tuples: (datetime_obj, zone_id)
        self.zone_counts = Counter()
        self.latest_timestamp = None

    def add_event(self, timestamp_str: str, zone_id: int):
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return

        self.events.append((dt, zone_id))
        self.zone_counts[zone_id] += 1

        if self.latest_timestamp is None or dt > self.latest_timestamp:
            self.latest_timestamp = dt

        self._evict_expired(dt)

    def _evict_expired(self, current_dt: datetime):
        """Evicts events that have aged out of the rolling time window."""
        cutoff = current_dt - self.window_delta
        while self.events and self.events[0][0] < cutoff:
            old_dt, old_zone = self.events.popleft()
            self.zone_counts[old_zone] -= 1
            if self.zone_counts[old_zone] <= 0:
                del self.zone_counts[old_zone]

    def get_snapshot(self) -> dict:
        """Returns the current window metrics snapshot."""
        return {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_window_latest_time": self.latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.latest_timestamp else None,
            "window_duration_minutes": self.window_minutes,
            "total_window_events": sum(self.zone_counts.values()),
            "active_zones_count": len(self.zone_counts),
            "data_freshness": "ACTIVE" if self.events else "IDLE",
            "zone_counts": {str(k): int(v) for k, v in self.zone_counts.items()}
        }


def save_snapshot(snapshot: dict, output_path: Path):
    """Atomically saves the current window snapshot to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    temp_path.replace(output_path)


def consume_trip_starts(
    topic_name: str = "taxi-trip-starts",
    bootstrap_servers: str = "localhost:9092",
    output_snapshot_path: Path = None,
    window_minutes: int = 15,
    max_events: int = 0,
    poll_timeout_sec: float = 3.0,
    read_buffer_fallback: bool = True
) -> dict:
    """
    Consumes events from Kafka or local fallback buffer, maintaining rolling window.
    """
    logger.info(f"Starting trip-start stream consumer (topic='{topic_name}', window={window_minutes}m)...")
    aggregator = RollingWindowAggregator(window_minutes=window_minutes)

    consumer = None
    use_fallback = False

    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="taxi-demand-group",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=int(poll_timeout_sec * 1000)
        )
        logger.info(f"Connected to Kafka broker at {bootstrap_servers}. Listening for messages...")
    except Exception as e:
        logger.warning(f"Could not connect Kafka consumer to {bootstrap_servers}: {e}")
        if read_buffer_fallback:
            logger.info("Switching to local stream buffer reading mode.")
            use_fallback = True
        else:
            raise e

    events_processed = 0

    if not use_fallback and consumer:
        try:
            for message in consumer:
                payload = message.value
                ts = payload.get("timestamp")
                zone = payload.get("pickup_location_id")
                if ts and zone:
                    aggregator.add_event(ts, int(zone))
                    events_processed += 1

                if events_processed % 100 == 0:
                    snapshot = aggregator.get_snapshot()
                    if output_snapshot_path:
                        save_snapshot(snapshot, output_snapshot_path)
                    logger.info(f"  Consumed {events_processed:,} events | Active zones: {snapshot['active_zones_count']} | Window events: {snapshot['total_window_events']:,}")

                if max_events > 0 and events_processed >= max_events:
                    break
        finally:
            consumer.close()

    elif use_fallback:
        base_dir = Path(__file__).resolve().parent.parent
        buffer_path = base_dir / "data" / "processed" / "stream_buffer.jsonl"
        if buffer_path.exists():
            with open(buffer_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    ts = payload.get("timestamp")
                    zone = payload.get("pickup_location_id")
                    if ts and zone:
                        aggregator.add_event(ts, int(zone))
                        events_processed += 1
                    if max_events > 0 and events_processed >= max_events:
                        break

    snapshot = aggregator.get_snapshot()
    if output_snapshot_path:
        save_snapshot(snapshot, output_snapshot_path)
        logger.info(f"Final rolling window snapshot saved to: {output_snapshot_path.name}")

    logger.info(f"Consumer complete. Processed {events_processed:,} events. Active zones: {snapshot['active_zones_count']}.")
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NYC Taxi Trip-Start Kafka Event Consumer")
    parser.add_argument("--max-events", type=int, default=500, help="Stop after consuming N events (default: 500, 0 for continuous)")
    parser.add_argument("--window", type=int, default=15, help="Rolling window size in minutes (default: 15)")
    args = parser.parse_args()

    cfg = load_config()
    base_dir = Path(__file__).resolve().parent.parent
    snapshot_file = base_dir / "data" / "processed" / "live_window_pickups.json"

    consume_trip_starts(
        topic_name=cfg["kafka"]["topic_name"],
        bootstrap_servers=cfg["kafka"]["bootstrap_servers"],
        output_snapshot_path=snapshot_file,
        window_minutes=args.window,
        max_events=args.max_events,
        read_buffer_fallback=True
    )
