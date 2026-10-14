"""
Module: dashboard/layouts.py
Description: Dash HTML and Core Components layout definition with modern styling,
             KPI cards, interactive controls, Mapbox choropleth, and 10-minute interval timer.
Author: Big Data Senior Engineer & Project Mentor
"""

from dash import html, dcc


def build_dashboard_layout(config: dict) -> html.Div:
    """Builds the complete single-page dashboard layout."""
    refresh_interval_ms = config["dashboard"].get("refresh_interval_ms", 600000)

    return html.Div(
        style={
            "backgroundColor": "#0f172a",
            "color": "#f8fafc",
            "fontFamily": "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
            "minHeight": "100vh",
            "padding": "20px 30px"
        },
        children=[
            # 1. 10-Minute Auto-Refresh Interval Component (600,000 ms = 10 minutes)
            dcc.Interval(
                id="interval-component",
                interval=refresh_interval_ms,
                n_intervals=0
            ),

            # 2. Header Section
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "borderBottom": "1px solid #334155",
                    "paddingBottom": "15px",
                    "marginBottom": "20px"
                },
                children=[
                    html.Div([
                        html.H1(
                            "NYC Taxi Demand Heatmap & Surge Monitor",
                            style={"margin": "0", "fontSize": "26px", "fontWeight": "700", "color": "#38bdf8"}
                        ),
                        html.P(
                            "Hybrid Big Data Architecture: Hadoop HDFS/MapReduce (Batch) + Apache Kafka (Stream)",
                            style={"margin": "5px 0 0 0", "fontSize": "14px", "color": "#94a3b8"}
                        )
                    ]),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "15px"},
                        children=[
                            html.Div(id="status-badge-container"),
                            html.Button(
                                "🔄 Refresh Now",
                                id="manual-refresh-btn",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "#0284c7",
                                    "color": "#ffffff",
                                    "border": "none",
                                    "borderRadius": "6px",
                                    "padding": "10px 18px",
                                    "fontSize": "13px",
                                    "fontWeight": "600",
                                    "cursor": "pointer",
                                    "transition": "background 0.2s"
                                }
                            )
                        ]
                    )
                ]
            ),

            # 3. Analytics Integrity Disclaimer Banner
            html.Div(
                style={
                    "backgroundColor": "#1e293b",
                    "borderLeft": "4px solid #f59e0b",
                    "padding": "12px 18px",
                    "borderRadius": "4px",
                    "marginBottom": "20px",
                    "fontSize": "13px",
                    "color": "#cbd5e1"
                },
                children=[
                    html.Strong("⚠️ Transparency & Domain Integrity Notice: ", style={"color": "#fbbf24"}),
                    "Pickup-demand surge ratios are calculated by comparing observed streaming trip-starts against historical Hadoop MapReduce hourly baselines. ",
                    html.Span(
                        "Passenger wait times and idle driver counts are strictly UNMEASURED ",
                        style={"fontWeight": "600", "color": "#f8fafc"}
                    ),
                    "as NYC TLC trip records only capture served (started) trips without real-time vehicle telematics/AVL data."
                ]
            ),

            # 4. Top KPI Cards Row
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
                    "gap": "15px",
                    "marginBottom": "20px"
                },
                id="kpi-cards-container"
            ),

            # 5. Interactive Filter & Controls Bar
            html.Div(
                style={
                    "backgroundColor": "#1e293b",
                    "padding": "15px 20px",
                    "borderRadius": "8px",
                    "marginBottom": "20px",
                    "display": "flex",
                    "flexWrap": "wrap",
                    "gap": "25px",
                    "alignItems": "center"
                },
                children=[
                    html.Div(
                        style={"flex": "1", "minWidth": "250px"},
                        children=[
                            html.Label(
                                "Visualized Metric:",
                                style={"fontSize": "13px", "fontWeight": "600", "color": "#94a3b8", "display": "block", "marginBottom": "5px"}
                            ),
                            dcc.Dropdown(
                                id="metric-selector",
                                options=[
                                    {"label": "📈 Estimated Unmet Demand (Pickup Surge Ratio vs Baseline)", "value": "surge_ratio"},
                                    {"label": "🚖 Live Streaming Pickups (Current 15-min Window)", "value": "live_window_pickups"},
                                    {"label": "📊 Expected Baseline Pickups (MapReduce Historical)", "value": "expected_window_pickups"}
                                ],
                                value="surge_ratio",
                                clearable=False,
                                style={"color": "#0f172a", "fontSize": "13px"}
                            )
                        ]
                    ),
                    html.Div(
                        style={"flex": "1.5", "minWidth": "300px"},
                        children=[
                            html.Div(
                                style={"display": "flex", "justifyContent": "space-between"},
                                children=[
                                    html.Label(
                                        "Target Baseline Hour (0–23):",
                                        style={"fontSize": "13px", "fontWeight": "600", "color": "#94a3b8"}
                                    ),
                                    html.Span(id="hour-slider-label", style={"fontSize": "13px", "color": "#38bdf8", "fontWeight": "600"})
                                ]
                            ),
                            dcc.Slider(
                                id="target-hour-slider",
                                min=0,
                                max=23,
                                step=1,
                                value=0,  # Matches streaming sample target hour
                                marks={h: f"{h:02d}:00" for h in range(0, 24, 3)},
                                tooltip={"placement": "bottom", "always_visible": False}
                            )
                        ]
                    )
                ]
            ),

            # 6. Main Visualizations Grid
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1.8fr 1.2fr",
                    "gap": "20px",
                    "marginBottom": "20px"
                },
                children=[
                    # Geographic Choropleth Heatmap
                    html.Div(
                        style={
                            "backgroundColor": "#1e293b",
                            "padding": "18px",
                            "borderRadius": "8px",
                            "border": "1px solid #334155"
                        },
                        children=[
                            html.H3(
                                "NYC Taxi Zones Demand Heatmap",
                                style={"margin": "0 0 12px 0", "fontSize": "16px", "fontWeight": "600", "color": "#f8fafc"}
                            ),
                            dcc.Loading(
                                type="default",
                                children=dcc.Graph(
                                    id="nyc-choropleth-map",
                                    style={"height": "560px"}
                                )
                            )
                        ]
                    ),

                    # Top 10 High-Demand Zones Leaderboard Chart
                    html.Div(
                        style={
                            "backgroundColor": "#1e293b",
                            "padding": "18px",
                            "borderRadius": "8px",
                            "border": "1px solid #334155"
                        },
                        children=[
                            html.H3(
                                "Top 10 High-Demand Taxi Zones",
                                style={"margin": "0 0 12px 0", "fontSize": "16px", "fontWeight": "600", "color": "#f8fafc"}
                            ),
                            dcc.Loading(
                                type="default",
                                children=dcc.Graph(
                                    id="top-10-leaderboard-chart",
                                    style={"height": "560px"}
                                )
                            )
                        ]
                    )
                ]
            ),

            # 7. Bottom Informational Footer
            html.Div(
                style={
                    "borderTop": "1px solid #334155",
                    "paddingTop": "15px",
                    "display": "flex",
                    "justifyContent": "space-between",
                    "fontSize": "12px",
                    "color": "#64748b"
                },
                children=[
                    html.Span("Big Data Analytics Project • Apache Kafka • Hadoop HDFS • MapReduce • Plotly Dash"),
                    html.Span("Auto-refresh active every 10 minutes • Host: http://127.0.0.1:8050")
                ]
            )
        ]
    )
