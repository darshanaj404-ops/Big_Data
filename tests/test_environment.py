"""
Phase 1 Acceptance Test: Environment & Skeleton Verification
Validates project directory structure, config integrity, and package imports.
"""

import os
from pathlib import Path
import pytest
import yaml


def test_directory_structure():
    """Verify all required project directories are created."""
    base_dir = Path(__file__).resolve().parent.parent

    required_dirs = [
        base_dir / "configs",
        base_dir / "docker",
        base_dir / "docker" / "hadoop",
        base_dir / "data" / "raw",
        base_dir / "data" / "sample",
        base_dir / "data" / "geo",
        base_dir / "data" / "processed",
        base_dir / "mapreduce",
        base_dir / "streaming",
        base_dir / "analytics",
        base_dir / "dashboard",
        base_dir / "scripts",
        base_dir / "tests",
    ]

    for d in required_dirs:
        assert d.exists(), f"Required directory missing: {d}"
        assert d.is_dir(), f"Path is not a directory: {d}"


def test_configuration_file():
    """Verify app_config.yaml exists and parses with mandatory keys."""
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "configs" / "app_config.yaml"

    assert config_path.exists(), "configs/app_config.yaml does not exist"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    expected_sections = [
        "app",
        "system",
        "storage",
        "dataset",
        "kafka",
        "hadoop",
        "analytics",
        "dashboard",
    ]

    for section in expected_sections:
        assert section in config, f"Missing section '{section}' in app_config.yaml"

    # Validate specific critical parameters
    assert config["dashboard"]["refresh_interval_ms"] == 600000, "Dashboard interval must be 600,000 ms (10 min)"
    assert config["analytics"]["top_n_rank_count"] == 10, "Top N rank count must be 10"
    assert config["system"]["total_system_ram_mb"] == 8192, "System memory budget must be 8192 MB"


def test_docker_assets_exist():
    """Verify docker-compose.yml and Hadoop container assets exist."""
    base_dir = Path(__file__).resolve().parent.parent
    docker_compose = base_dir / "docker" / "docker-compose.yml"
    hadoop_dockerfile = base_dir / "docker" / "hadoop" / "Dockerfile"
    entrypoint = base_dir / "docker" / "hadoop" / "entrypoint.sh"

    assert docker_compose.exists(), "docker/docker-compose.yml is missing"
    assert hadoop_dockerfile.exists(), "docker/hadoop/Dockerfile is missing"
    assert entrypoint.exists(), "docker/hadoop/entrypoint.sh is missing"


def test_core_library_imports():
    """Verify Python can import standard libraries and YAML parser."""
    import sys
    import json
    import csv
    import logging

    assert sys.version_info >= (3, 10), "Python 3.10+ required"
    assert yaml.__version__ is not None
