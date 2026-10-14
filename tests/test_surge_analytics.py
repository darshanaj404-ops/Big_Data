"""
Phase 5 Acceptance Test: Demand Surge Analytics & Synthesis Engine
Tests surge ratio mathematics, cold-start zone coverage, top 10 ranking, and metric integrity.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from analytics.surge_calculator import SurgeAnalyticsEngine


@pytest.fixture(scope="module")
def analytics_engine():
    return SurgeAnalyticsEngine()


def test_cold_start_and_full_zone_coverage(analytics_engine):
    """Verify that all 265 TLC zones are preserved, even with zero activity."""
    mock_snapshot = {
        "last_updated": "2024-01-01 14:00:00",
        "window_duration_minutes": 15,
        "total_window_events": 0,
        "active_zones_count": 0,
        "data_freshness": "ACTIVE",
        "zone_counts": {}  # No active events
    }

    master_df, top_10_df = analytics_engine.compute_surge_metrics(
        target_hour=14,
        streaming_snapshot=mock_snapshot
    )

    # Must preserve all 265 official TLC zones
    assert len(master_df) == 265
    assert (master_df["live_window_pickups"] == 0).all()
    assert (master_df["surge_category"] == "No Observed Pickups").all()
    assert (master_df["surge_ratio"] == 0.0).all()
    assert len(top_10_df) == 10


def test_surge_ratio_formula_and_smoothing_epsilon(analytics_engine):
    """Verify surge calculation formula with smoothing epsilon against division-by-zero."""
    # Test case 1: Active zone with 30 live pickups, expected 10 pickups
    mock_snapshot = {
        "window_duration_minutes": 15,
        "zone_counts": {
            "237": 60,  # Zone 237 has strong live surge (expected ~26, live 60 => ratio > 2.0)
            "999": 5    # Non-standard zone ID test
        }
    }

    master_df, _ = analytics_engine.compute_surge_metrics(
        target_hour=14,
        streaming_snapshot=mock_snapshot
    )

    z237 = master_df[master_df["LocationID"] == 237].iloc[0]
    expected_exp = z237["expected_window_pickups"]
    expected_ratio = round(60.0 / (expected_exp + 1.0), 2)

    assert z237["live_window_pickups"] == 60
    assert z237["surge_ratio"] == expected_ratio
    assert z237["surge_category"] == "High Pickup Surge"


def test_unmet_demand_labeling_transparency(analytics_engine):
    """Verify that supply gap / idle wait times are explicitly disclaimed."""
    master_df, top_10_df = analytics_engine.compute_surge_metrics(target_hour=14)

    assert "unmet_demand_status" in master_df.columns
    assert "UNMEASURED" in master_df["unmet_demand_status"].iloc[0]
    assert "UNMEASURED" in top_10_df["unmet_demand_status"].iloc[0]


def test_top_10_ranking_order(analytics_engine):
    """Verify Top 10 zones are strictly sorted by surge ratio and live volume."""
    master_df, top_10_df = analytics_engine.compute_surge_metrics(target_hour=14)

    assert len(top_10_df) == 10
    ratios = top_10_df["surge_ratio"].tolist()
    # Check descending or equal ordering
    assert ratios == sorted(ratios, reverse=True)
    assert list(top_10_df["surge_rank"]) == list(range(1, 11))
