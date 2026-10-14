"""
Module: dashboard/app.py
Description: Main Plotly Dash application server entrypoint.
             Assembles layouts, registers reactive callbacks, and runs the web server.
Author: Big Data Senior Engineer & Project Mentor
"""

import sys
from pathlib import Path
import dash
import yaml

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from dashboard.layouts import build_dashboard_layout
from dashboard.callbacks import register_callbacks


def load_config() -> dict:
    """Loads configuration from configs/app_config.yaml."""
    config_path = base_dir / "configs" / "app_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_app(config: dict = None) -> dash.Dash:
    """Factory function to build and configure the Dash application."""
    if config is None:
        config = load_config()

    app = dash.Dash(
        __name__,
        title="Taxi Demand Heatmap & Surge Monitor",
        update_title=None,
        suppress_callback_exceptions=True
    )

    app.layout = build_dashboard_layout(config)
    register_callbacks(app, config)

    return app


if __name__ == "__main__":
    cfg = load_config()
    host = cfg["dashboard"].get("host", "127.0.0.1")
    port = int(cfg["dashboard"].get("port", 8050))
    debug = bool(cfg["dashboard"].get("debug_mode", False))

    print("=" * 60)
    print(" STARTING TAXI DEMAND HEATMAP DASHBOARD")
    print("=" * 60)
    print(f" URL: http://{host}:{port}")
    print(f" Auto-refresh interval: 10 minutes (600,000 ms)")
    print(" Press Ctrl+C in terminal to stop.")
    print("=" * 60)

    application = create_app(cfg)
    application.run(host=host, port=port, debug=debug)
