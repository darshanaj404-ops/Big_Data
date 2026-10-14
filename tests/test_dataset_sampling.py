"""
Phase 2 Acceptance Test: Dataset Acquisition & Sample Verification
Validates the downloaded TLC lookup table, GeoJSON polygons, and sampled CSV.
"""

from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
import pytest


@pytest.fixture(scope="module")
def base_dir():
    return Path(__file__).resolve().parent.parent


def test_zone_lookup_file(base_dir):
    """Verify official taxi zone lookup CSV is populated and structurally valid."""
    lookup_path = base_dir / "data" / "geo" / "taxi_zone_lookup.csv"
    assert lookup_path.exists(), "data/geo/taxi_zone_lookup.csv is missing"
    assert lookup_path.stat().st_size > 0, "Lookup file is empty"

    df = pd.read_csv(lookup_path)
    expected_cols = {"LocationID", "Borough", "Zone", "service_zone"}
    assert expected_cols.issubset(set(df.columns)), f"Missing columns in lookup CSV: {expected_cols - set(df.columns)}"
    assert len(df) >= 260, f"Expected at least 260 official zones, found {len(df)}"
    assert df["LocationID"].is_unique, "LocationID must be unique"


def test_zone_geojson_geometry(base_dir):
    """Verify optimized GeoJSON polygon dataset is present and valid."""
    geojson_path = base_dir / "data" / "geo" / "nyc_taxi_zones.geojson"
    assert geojson_path.exists(), "data/geo/nyc_taxi_zones.geojson is missing"
    assert geojson_path.stat().st_size > 0, "GeoJSON file is empty"

    gdf = gpd.read_file(geojson_path, engine="pyogrio")
    assert "location_id" in gdf.columns, "location_id column must exist in GeoJSON properties"
    assert len(gdf) >= 250, f"Expected at least 250 zone polygons, found {len(gdf)}"
    assert not gdf["geometry"].is_empty.any(), "Empty geometries found in GeoJSON"


def test_sample_trip_records_csv(base_dir):
    """Verify 100k sample CSV is complete, non-empty, and satisfies schema rules."""
    sample_path = base_dir / "data" / "sample" / "yellow_tripdata_sample_100k.csv"
    assert sample_path.exists(), "data/sample/yellow_tripdata_sample_100k.csv is missing"

    df = pd.read_csv(sample_path)
    assert len(df) == 100000, f"Expected exactly 100,000 rows, found {len(df)}"

    # Required columns for downstream MapReduce and Kafka streaming
    required_cols = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "PULocationID",
        "DOLocationID",
        "passenger_count",
        "trip_distance",
        "fare_amount",
    ]
    for col in required_cols:
        assert col in df.columns, f"Required column missing: {col}"

    # Critical data quality assertions
    assert df["PULocationID"].isnull().sum() == 0, "Found null PULocationID in sample"
    assert (df["PULocationID"] >= 1).all() and (df["PULocationID"] <= 265).all(), "PULocationID out of bounds"
    assert df["tpep_pickup_datetime"].isnull().sum() == 0, "Found null pickup datetime"


def test_sample_metadata_json(base_dir):
    """Verify sample metadata JSON accurately describes the sample."""
    meta_path = base_dir / "data" / "sample" / "sample_metadata.json"
    assert meta_path.exists(), "data/sample/sample_metadata.json is missing"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["sample_row_count"] == 100000
    assert meta["unique_pickup_zones"] > 50
    assert "tpep_pickup_datetime" in meta["columns"]
