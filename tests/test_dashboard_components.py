"""
Phase 6 Acceptance Test: Plotly Dash Heatmap & Leaderboard Dashboard
Tests application initialization, 10-minute interval timer configuration,
transparency banner presence, and callback figure generation.
"""

import sys
from pathlib import Path
import pytest
import plotly.graph_objects as go

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from dashboard.app import create_app, load_config
from dashboard.layouts import build_dashboard_layout
from dashboard.callbacks import build_dashboard_figures_and_kpis, load_geojson
from analytics.surge_calculator import SurgeAnalyticsEngine


@pytest.fixture(scope="module")
def app_instance():
    cfg = load_config()
    return create_app(cfg)


def test_dash_app_initialization(app_instance):
    """Verify Dash app initializes cleanly."""
    assert app_instance is not None
    assert app_instance.title == "Taxi Demand Heatmap & Surge Monitor"
    assert app_instance.layout is not None


def test_interval_component_configuration():
    """Verify that the auto-refresh interval is configured to exactly 10 minutes (600,000 ms)."""
    cfg = load_config()
    layout = build_dashboard_layout(cfg)

    # Search for dcc.Interval component in layout children
    interval_comp = None
    for child in layout.children:
        if getattr(child, "id", None) == "interval-component":
            interval_comp = child
            break

    assert interval_comp is not None, "dcc.Interval component missing from layout"
    assert interval_comp.interval == 600000, f"Expected 600,000 ms (10 min), found {interval_comp.interval}"


def test_transparency_disclaimer_banner():
    """Verify the layout includes the mandatory analytics transparency notice."""
    cfg = load_config()
    layout = build_dashboard_layout(cfg)

    layout_str = str(layout)
    assert "Transparency" in layout_str or "UNMEASURED" in layout_str
    assert "wait times" in layout_str or "idle driver" in layout_str


def test_dashboard_figures_and_kpi_generation():
    """Verify figure generator produces valid Plotly Mapbox and Bar chart figure objects."""
    cfg = load_config()
    engine = SurgeAnalyticsEngine(config=cfg)
    geo_data = load_geojson(base_dir)

    status_badge, kpi_cards, fig_map, fig_chart = build_dashboard_figures_and_kpis(
        engine=engine,
        geojson_data=geo_data,
        target_hour=0,
        metric_column="surge_ratio"
    )

    # Verify status badge and KPI cards
    assert status_badge is not None
    assert len(kpi_cards) == 4

    # Verify figures are valid Plotly figures
    assert isinstance(fig_map, go.Figure)
    assert isinstance(fig_chart, go.Figure)

    # Check that map contains choropleth data
    data_dict = fig_map.to_dict()
    assert len(data_dict.get("data", [])) > 0
    assert data_dict["data"][0]["type"] == "choroplethmapbox"

    # Check that bar chart contains valid traces
    chart_dict = fig_chart.to_dict()
    assert len(chart_dict.get("data", [])) > 0
    assert chart_dict["data"][0]["type"] == "bar"
