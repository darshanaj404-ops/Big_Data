"""
Module: streaming/kafka_manager.py
Description: Kafka administrative and connection utilities.
             Handles connection health checks, topic creation, and fallback buffering.
Author: Big Data Senior Engineer & Project Mentor
"""

import sys
import logging
from typing import Optional
from pathlib import Path
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load settings from configs/app_config.yaml."""
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "configs" / "app_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration not found at {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_kafka_connection(bootstrap_servers: str = "localhost:9092", timeout_sec: int = 3) -> bool:
    """
    Checks if an Apache Kafka broker is reachable at bootstrap_servers.
    Returns True if connected, False otherwise.
    """
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=timeout_sec * 1000,
            api_version_auto_timeout_ms=timeout_sec * 1000
        )
        topics = consumer.topics()
        consumer.close()
        logger.info(f"Kafka connection successful! Available topics: {list(topics)}")
        return True
    except Exception as e:
        logger.warning(f"Kafka broker at {bootstrap_servers} is not reachable: {e}")
        return False


def ensure_topic_exists(
    topic_name: str = "taxi-trip-starts",
    bootstrap_servers: str = "localhost:9092",
    num_partitions: int = 1,
    replication_factor: int = 1
) -> bool:
    """
    Ensures that the target Kafka topic exists. Creates it if missing.
    """
    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        from kafka.errors import TopicAlreadyExistsError

        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=5000
        )

        existing_topics = admin_client.list_topics()
        if topic_name in existing_topics:
            logger.info(f"Topic '{topic_name}' already exists.")
            admin_client.close()
            return True

        topic_list = [NewTopic(name=topic_name, num_partitions=num_partitions, replication_factor=replication_factor)]
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        logger.info(f"Topic '{topic_name}' created successfully with {num_partitions} partition(s).")
        admin_client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to ensure topic '{topic_name}': {e}")
        return False


if __name__ == "__main__":
    cfg = load_config()
    servers = cfg["kafka"]["bootstrap_servers"]
    topic = cfg["kafka"]["topic_name"]

    is_online = check_kafka_connection(servers)
    if is_online:
        ensure_topic_exists(topic, servers)
    else:
        logger.info("Kafka is offline. Use docker compose to start the broker, or use fallback mode for testing.")
