"""
Phase 7 Acceptance Test: Full End-to-End Pipeline Integration Test
Validates the complete pipeline from sample dataset ingestion, MapReduce aggregation,
Kafka event streaming, demand surge synthesis, to dashboard figure generation.
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import plotly.graph_objects as go

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from analytics.surge_calculator import SurgeAnalyticsEngine
from dashboard.callbacks import build_dashboard_figures_and_kpis, load_geojson
from dashboard.app import load_config


def test_end_to_end_pipeline_dataflow():
    """Verify data transforms correctly through all layers of the Big Data stack."""
    cfg = load_config()

    # 1. Verify Sample Dataset
    sample_csv = base_dir / cfg["storage"]["sample_dir"] / "yellow_tripdata_sample_100k.csv"
    assert sample_csv.exists(), "Sample CSV is missing"
    assert sample_csv.stat().st_size > 1024 * 1024, "Sample CSV is too small"

    # 2. Verify MapReduce Baseline Output
    baseline_csv = base_dir / cfg["storage"]["historical_baseline_csv"]
    assert baseline_csv.exists(), "MapReduce historical baseline is missing"
    baseline_df = pd.read_csv(baseline_csv)
    assert len(baseline_df) >= 2000, "MapReduce baseline should contain over 2,000 zone-hour pairs"

    # 3. Verify Streaming Window Snapshot
    snapshot_json = base_dir / "data" / "processed" / "live_window_pickups.json"
    assert snapshot_json.exists(), "Streaming window snapshot is missing"

    # 4. Execute Surge Analytics Engine
    engine = SurgeAnalyticsEngine(config=cfg)
    master_csv, top10_csv = engine.run_synthesis_pipeline(target_hour=1)
    assert master_csv.exists(), "Synthesized demand heatmap CSV is missing"
    assert top10_csv.exists(), "Top 10 leaderboard CSV is missing"

    # Validate output schema
    master_df = pd.read_csv(master_csv)
    assert len(master_df) == 265, "All 265 official TLC zones must be present in the heatmap"
    assert "surge_ratio" in master_df.columns
    assert "live_window_pickups" in master_df.columns
    assert "expected_window_pickups" in master_df.columns
    assert "surge_category" in master_df.columns

    top10_df = pd.read_csv(top10_csv)
    assert len(top10_df) == 10, "Top 10 leaderboard must contain exactly 10 zones"

    # 5. Verify Dash Dashboard Render Pipeline
    geo_data = load_geojson(base_dir)
    status_badge, kpi_cards, fig_map, fig_chart = build_dashboard_figures_and_kpis(
        engine=engine,
        geojson_data=geo_data,
        target_hour=1,
        metric_column="surge_ratio"
    )

    assert status_badge is not None
    assert len(kpi_cards) == 4
    assert isinstance(fig_map, go.Figure)
    assert isinstance(fig_chart, go.Figure)

    # Validate Mapbox Trace properties
    map_data = fig_map.to_dict()["data"][0]
    assert map_data["type"] == "choroplethmapbox"
    assert len(map_data["locations"]) == 265
