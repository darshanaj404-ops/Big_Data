"""
Module: streaming/kafka_producer.py
Description: Replays historical NYC Yellow Taxi trip-starts into Apache Kafka
             as real-time streaming events with simulated inter-arrival delays.
Author: Big Data Senior Engineer & Project Mentor
"""

import sys
import time
import json
import uuid
import argparse
import logging
from pathlib import Path
import pandas as pd
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


def build_event_payload(row: pd.Series) -> dict:
    """Constructs a standardized trip-start streaming event."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "trip_start",
        "timestamp": str(row["tpep_pickup_datetime"]),
        "pickup_location_id": int(row["PULocationID"]),
        "dropoff_location_id": int(row["DOLocationID"]),
        "passenger_count": int(row["passenger_count"]),
        "trip_distance": float(row["trip_distance"]),
        "fare_amount": float(row["fare_amount"]),
    }


def stream_trip_starts(
    sample_csv_path: Path,
    topic_name: str = "taxi-trip-starts",
    bootstrap_servers: str = "localhost:9092",
    delay_seconds: float = 0.02,
    max_events: int = 1000,
    dry_run: bool = False
) -> int:
    """
    Streams trip-start events to Kafka topic or local buffer.
    Returns total events successfully produced.
    """
    logger.info(f"Initiating trip-start streaming (max_events={max_events}, delay={delay_seconds}s, dry_run={dry_run})...")

    if not sample_csv_path.exists():
        raise FileNotFoundError(f"Sample dataset missing at: {sample_csv_path}")

    # Read records
    df = pd.read_csv(sample_csv_path)
    if max_events > 0:
        df = df.iloc[:max_events]

    producer = None
    buffer_file = None

    if not dry_run:
        try:
            from kafka import KafkaProducer
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=5000,
                retries=3
            )
            logger.info(f"Connected to Kafka broker at {bootstrap_servers}. Target topic: '{topic_name}'")
        except Exception as e:
            logger.warning(f"Could not connect to live Kafka broker: {e}")
            logger.info("Falling back to local stream buffer mode for testing.")
            dry_run = True

    if dry_run:
        buffer_path = sample_csv_path.parent.parent / "processed" / "stream_buffer.jsonl"
        buffer_path.parent.mkdir(parents=True, exist_ok=True)
        buffer_file = open(buffer_path, "w", encoding="utf-8")
        logger.info(f"Buffering stream events locally to: {buffer_path.name}")

    events_produced = 0
    start_time = time.time()

    try:
        for idx, row in df.iterrows():
            payload = build_event_payload(row)

            if producer:
                producer.send(topic_name, value=payload)
            elif buffer_file:
                buffer_file.write(json.dumps(payload) + "\n")
                buffer_file.flush()

            events_produced += 1

            if events_produced % 200 == 0:
                elapsed = time.time() - start_time
                rate = events_produced / elapsed if elapsed > 0 else 0
                logger.info(f"  Streamed {events_produced:,}/{len(df):,} events ({rate:.1f} events/sec)...")

            if delay_seconds > 0:
                time.sleep(delay_seconds)

    finally:
        if producer:
            producer.flush()
            producer.close()
            logger.info(f"Kafka producer flushed and closed. Total produced: {events_produced:,}")
        if buffer_file:
            buffer_file.close()
            logger.info(f"Stream buffer file closed. Total buffered: {events_produced:,}")

    return events_produced


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NYC Taxi Trip-Start Kafka Event Producer")
    parser.add_argument("--max-events", type=int, default=500, help="Maximum events to stream (default: 500)")
    parser.add_argument("--delay", type=float, default=0.01, help="Delay in seconds between events (default: 0.01)")
    parser.add_argument("--dry-run", action="store_true", help="Buffer events to disk instead of network broker")
    args = parser.parse_args()

    cfg = load_config()
    base_dir = Path(__file__).resolve().parent.parent
    sample_csv = base_dir / cfg["storage"]["sample_dir"] / "yellow_tripdata_sample_100k.csv"

    stream_trip_starts(
        sample_csv_path=sample_csv,
        topic_name=cfg["kafka"]["topic_name"],
        bootstrap_servers=cfg["kafka"]["bootstrap_servers"],
        delay_seconds=args.delay,
        max_events=args.max_events,
        dry_run=args.dry_run
    )
