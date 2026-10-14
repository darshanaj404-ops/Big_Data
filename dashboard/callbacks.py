"""
Module: dashboard/callbacks.py
Description: Interactive Dash callback functions for auto-refresh, metric selection,
             choropleth map updates, and Top 10 leaderboard re-ranking.
Author: Big Data Senior Engineer & Project Mentor
"""

import json
from pathlib import Path
from datetime import datetime
from dash import Input, Output, html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from analytics.surge_calculator import SurgeAnalyticsEngine


def load_geojson(base_dir: Path) -> dict:
    """Loads optimized NYC taxi zones GeoJSON from disk."""
    geojson_path = base_dir / "data" / "geo" / "nyc_taxi_zones.geojson"
    if not geojson_path.exists():
        raise FileNotFoundError(f"Missing GeoJSON file at: {geojson_path}")
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_dashboard_figures_and_kpis(
    engine: SurgeAnalyticsEngine,
    geojson_data: dict,
    target_hour: int = 0,
    metric_column: str = "surge_ratio"
):
    """
    Core functional pipeline generating status badge, KPI cards,
    Mapbox choropleth figure, and Top 10 horizontal bar chart.
    """
    master_df, top_10_df = engine.compute_surge_metrics(target_hour=target_hour)
    snapshot = engine.load_streaming_window()

    freshness = snapshot.get("data_freshness", "IDLE")
    now_str = datetime.now().strftime("%H:%M:%S")

    # Status Badge
    badge_color = "#10b981" if freshness == "ACTIVE" else "#f59e0b"
    status_badge = html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
            "backgroundColor": "#1e293b",
            "padding": "6px 14px",
            "borderRadius": "20px",
            "border": f"1px solid {badge_color}"
        },
        children=[
            html.Span(
                style={"height": "8px", "width": "8px", "borderRadius": "50%", "backgroundColor": badge_color, "display": "inline-block"}
            ),
            html.Span(f"Stream: {freshness}", style={"fontSize": "12px", "fontWeight": "600", "color": badge_color}),
            html.Span(f"(Refreshed {now_str})", style={"fontSize": "11px", "color": "#94a3b8"})
        ]
    )

    # KPI Cards
    total_live_events = snapshot.get("total_window_events", 0)
    active_zones_count = snapshot.get("active_zones_count", 0)
    high_surge_count = int((master_df["surge_category"] == "High Pickup Surge").sum())
    peak_zone = top_10_df.iloc[0] if len(top_10_df) > 0 else None

    kpi_cards = [
        # Card 1: Active Window Events
        html.Div(
            style={"backgroundColor": "#1e293b", "padding": "16px", "borderRadius": "8px", "border": "1px solid #334155"},
            children=[
                html.P("Live Window Pickups", style={"margin": "0", "fontSize": "12px", "color": "#94a3b8", "fontWeight": "600"}),
                html.H2(f"{total_live_events:,}", style={"margin": "8px 0 0 0", "fontSize": "26px", "color": "#38bdf8", "fontWeight": "700"}),
                html.Span(f"Across {active_zones_count} active zones (15-min window)", style={"fontSize": "11px", "color": "#64748b"})
            ]
        ),
        # Card 2: High Surge Zones
        html.Div(
            style={"backgroundColor": "#1e293b", "padding": "16px", "borderRadius": "8px", "border": "1px solid #334155"},
            children=[
                html.P("High Surge Zones", style={"margin": "0", "fontSize": "12px", "color": "#94a3b8", "fontWeight": "600"}),
                html.H2(f"{high_surge_count}", style={"margin": "8px 0 0 0", "fontSize": "26px", "color": "#ef4444" if high_surge_count > 0 else "#10b981", "fontWeight": "700"}),
                html.Span("Surge ratio ≥ 1.5x with ≥ 3 pickups", style={"fontSize": "11px", "color": "#64748b"})
            ]
        ),
        # Card 3: Peak Demand Zone
        html.Div(
            style={"backgroundColor": "#1e293b", "padding": "16px", "borderRadius": "8px", "border": "1px solid #334155"},
            children=[
                html.P("Top Surge Zone", style={"margin": "0", "fontSize": "12px", "color": "#94a3b8", "fontWeight": "600"}),
                html.H2(f"{peak_zone['surge_ratio']}x" if peak_zone is not None else "N/A", style={"margin": "8px 0 0 0", "fontSize": "26px", "color": "#f59e0b", "fontWeight": "700"}),
                html.Span(f"{peak_zone['Zone']} ({peak_zone['Borough']})" if peak_zone is not None else "No data", style={"fontSize": "11px", "color": "#94a3b8", "fontWeight": "500"})
            ]
        ),
        # Card 4: Historical Baseline Context
        html.Div(
            style={"backgroundColor": "#1e293b", "padding": "16px", "borderRadius": "8px", "border": "1px solid #334155"},
            children=[
                html.P("MapReduce Baseline Hour", style={"margin": "0", "fontSize": "12px", "color": "#94a3b8", "fontWeight": "600"}),
                html.H2(f"{target_hour:02d}:00", style={"margin": "8px 0 0 0", "fontSize": "26px", "color": "#a855f7", "fontWeight": "700"}),
                html.Span("Historical expected hourly rate", style={"fontSize": "11px", "color": "#64748b"})
            ]
        ),
    ]

    # Mapbox Choropleth Heatmap Figure
    metric_title_map = {
        "surge_ratio": "Estimated Unmet Demand (Surge Ratio)",
        "live_window_pickups": "Live Pickups (15-min)",
        "expected_window_pickups": "Expected Baseline (15-min)"
    }
    metric_title = metric_title_map.get(metric_column, metric_column)

    color_scale = "Viridis" if metric_column != "surge_ratio" else "YlOrRd"

    fig_map = px.choropleth_mapbox(
        master_df,
        geojson=geojson_data,
        locations="LocationID",
        featureidkey="properties.location_id",
        color=metric_column,
        color_continuous_scale=color_scale,
        range_color=[0, max(2.5, master_df[metric_column].quantile(0.98))],
        mapbox_style="open-street-map",
        zoom=9.8,
        center={"lat": 40.730610, "lon": -73.935242},
        hover_name="Zone",
        hover_data={
            "Borough": True,
            "live_window_pickups": True,
            "expected_window_pickups": True,
            "surge_ratio": True,
            "surge_category": True,
            "LocationID": False
        },
        labels={
            "surge_ratio": "Surge Ratio",
            "live_window_pickups": "Live Pickups",
            "expected_window_pickups": "Expected"
        }
    )

    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        coloraxis_colorbar={
            "title": metric_title,
            "title_font_color": "#cbd5e1",
            "tickfont": {"color": "#cbd5e1"},
            "thickness": 14,
            "len": 0.85
        }
    )

    # Top 10 Leaderboard Horizontal Bar Chart
    top_10_sorted = top_10_df.iloc[::-1].copy()

    fig_chart = px.bar(
        top_10_sorted,
        x=metric_column,
        y="Zone",
        orientation="h",
        color="surge_ratio",
        color_continuous_scale="Plasma",
        hover_data={
            "Borough": True,
            "live_window_pickups": True,
            "expected_window_pickups": True,
            "surge_ratio": True
        },
        labels={
            metric_column: metric_title,
            "Zone": "Taxi Zone",
            "surge_ratio": "Surge"
        }
    )

    fig_chart.update_layout(
        margin={"r": 15, "t": 20, "l": 10, "b": 10},
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font={"color": "#cbd5e1", "size": 11},
        xaxis={"gridcolor": "#334155", "title": metric_title},
        yaxis={"gridcolor": "#334155", "title": ""},
        coloraxis_showscale=False
    )

    return status_badge, kpi_cards, fig_map, fig_chart


def register_callbacks(app, config: dict):
    """Registers all reactive Dash callbacks to the application."""
    base_dir = Path(__file__).resolve().parent.parent
    geojson_data = load_geojson(base_dir)
    engine = SurgeAnalyticsEngine(config=config)

    @app.callback(
        Output("hour-slider-label", "children"),
        Input("target-hour-slider", "value")
    )
    def update_hour_label(hour_val):
        return f"Selected: {hour_val:02d}:00"

    @app.callback(
        [
            Output("status-badge-container", "children"),
            Output("kpi-cards-container", "children"),
            Output("nyc-choropleth-map", "figure"),
            Output("top-10-leaderboard-chart", "figure")
        ],
        [
            Input("interval-component", "n_intervals"),
            Input("manual-refresh-btn", "n_clicks"),
            Input("target-hour-slider", "value"),
            Input("metric-selector", "value")
        ]
    )
    def refresh_dashboard_state(n_intervals, n_clicks, target_hour, metric_column):
        return build_dashboard_figures_and_kpis(
            engine=engine,
            geojson_data=geojson_data,
            target_hour=target_hour,
            metric_column=metric_column
        )
