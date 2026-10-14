"""
Script: 02_download_and_sample_data.py
Description: Memory-safe acquisition and preprocessing of NYC Yellow Taxi records,
             taxi zone lookup reference table, and GeoJSON zone boundary polygons.
Author: Big Data Senior Engineer & Project Mentor
"""

import os
import sys
import json
import zipfile
import logging
from pathlib import Path
import requests
import yaml
import pyarrow.parquet as pq
import pandas as pd
import geopandas as gpd

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


def download_file_streamed(url: str, dest_path: Path, chunk_size: int = 1024 * 1024) -> None:
    """
    Download an external file in streaming chunks to prevent memory spikes.
    Avoids loading full network response into RAM.
    """
    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info(f"File already exists: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    logger.info(f"Starting streamed download: {url}")
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        total_bytes = 0
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
                    if total_bytes % (10 * 1024 * 1024) == 0:
                        logger.info(f"  Downloaded {total_bytes / 1024 / 1024:.1f} MB...")

        # Atomically rename on completion
        temp_path.replace(dest_path)
        logger.info(f"Download complete: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Failed to download {url}: {e}")
        raise e


def process_zone_lookup(config: dict, base_dir: Path) -> Path:
    """Download and verify official NYC TLC Taxi Zone Lookup CSV."""
    url = config["dataset"]["zone_lookup_url"]
    dest_path = base_dir / config["storage"]["lookup_csv"]

    download_file_streamed(url, dest_path)

    # Validate header & contents
    df = pd.read_csv(dest_path)
    required_cols = {"LocationID", "Borough", "Zone", "service_zone"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"taxi_zone_lookup.csv missing expected columns: {required_cols - set(df.columns)}")

    logger.info(f"Zone lookup verified: {len(df)} official zones loaded.")
    return dest_path


def process_zone_geojson(config: dict, base_dir: Path) -> Path:
    """
    Download official NYC TLC Taxi Zone shapefile, extract it, project to WGS84,
    simplify geometries, and save as optimized GeoJSON for Plotly.
    """
    url = config["dataset"]["zone_shapefile_url"]
    zip_path = base_dir / "data" / "raw" / "taxi_zones.zip"
    extract_dir = base_dir / "data" / "raw" / "taxi_zones"
    dest_geojson_path = base_dir / config["storage"]["zones_geojson"]

    # 1. Download zip archive
    download_file_streamed(url, zip_path)

    if dest_geojson_path.exists() and dest_geojson_path.stat().st_size > 0:
        logger.info(f"Optimized GeoJSON already exists: {dest_geojson_path.name}")
        return dest_geojson_path

    # 2. Extract shapefile
    logger.info("Extracting shapefile archive...")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    # Locate .shp file
    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError("No .shp file found inside extracted taxi_zones archive.")
    shp_path = shp_files[0]

    logger.info(f"Reading shapefile via pyogrio: {shp_path.name}...")
    gdf = gpd.read_file(shp_path, engine="pyogrio")

    # 3. Identify and normalize location ID column
    loc_col = None
    for col in ["LocationID", "location_id", "OBJECTID"]:
        if col in gdf.columns:
            loc_col = col
            break

    if not loc_col:
        raise KeyError(f"Location ID column not found. Available: {gdf.columns.tolist()}")

    gdf["location_id"] = gdf[loc_col].astype(int)

    # 4. Transform coordinate reference system to standard WGS84 (EPSG:4326)
    if gdf.crs != "EPSG:4326":
        logger.info(f"Converting CRS from {gdf.crs} to EPSG:4326 (WGS84)...")
        gdf = gdf.to_crs(epsg=4326)

    # 5. Simplify polygons to ensure fast rendering in Dash
    logger.info("Simplifying polygon geometry (tolerance=0.0005)...")
    gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.0005, preserve_topology=True)

    # Keep only essential columns to reduce GeoJSON file size
    keep_cols = ["location_id", "zone", "borough", "geometry"]
    existing_keep_cols = [c for c in keep_cols if c in gdf.columns]
    gdf = gdf[existing_keep_cols]

    # 6. Save optimized GeoJSON
    dest_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(dest_geojson_path, driver="GeoJSON")
    logger.info(f"Optimized GeoJSON saved: {dest_geojson_path.name} ({dest_geojson_path.stat().st_size / 1024 / 1024:.2f} MB, {len(gdf)} zones)")
    return dest_geojson_path


def sample_trip_records_memory_safe(
    config: dict,
    base_dir: Path,
    target_sample_size: int = 100000
) -> Path:
    """
    Reads the downloaded Parquet dataset in small batches (iter_batches)
    to keep RAM usage strictly below 100 MB. Extracts clean, validated sample records.
    """
    url = config["dataset"]["trip_records_url"]
    parquet_path = base_dir / "data" / "raw" / "yellow_tripdata_2024-01.parquet"
    sample_csv_path = base_dir / config["storage"]["sample_dir"] / "yellow_tripdata_sample_100k.csv"

    # Step 1: Download raw Parquet file
    download_file_streamed(url, parquet_path)

    if sample_csv_path.exists() and sample_csv_path.stat().st_size > 0:
        logger.info(f"Sample CSV already exists: {sample_csv_path.name}")
        return sample_csv_path

    logger.info(f"Streaming Parquet batches to build {target_sample_size:,} row sample CSV...")
    parquet_file = pq.ParquetFile(parquet_path)

    required_cols = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "PULocationID",
        "DOLocationID",
        "passenger_count",
        "trip_distance",
        "fare_amount",
    ]

    collected_rows = []
    total_scanned = 0

    # Stream in 15,000-row chunks to strictly cap RAM usage
    for batch in parquet_file.iter_batches(batch_size=15000, columns=required_cols):
        batch_df = batch.to_pandas()
        total_scanned += len(batch_df)

        # Basic filtering: valid pickup datetime and valid zone IDs (1 to 265)
        batch_df = batch_df.dropna(subset=["tpep_pickup_datetime", "PULocationID"])
        batch_df["PULocationID"] = batch_df["PULocationID"].astype(int)
        batch_df = batch_df[(batch_df["PULocationID"] >= 1) & (batch_df["PULocationID"] <= 265)]

        # Fill default passenger count
        batch_df["passenger_count"] = batch_df["passenger_count"].fillna(1).astype(int)

        collected_rows.append(batch_df)
        current_count = sum(len(b) for b in collected_rows)

        if current_count >= target_sample_size:
            break

    combined_df = pd.concat(collected_rows, ignore_index=True).iloc[:target_sample_size]

    # Format datetime strings to standard ISO format
    combined_df["tpep_pickup_datetime"] = pd.to_datetime(combined_df["tpep_pickup_datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    combined_df["tpep_dropoff_datetime"] = pd.to_datetime(combined_df["tpep_dropoff_datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Sort deterministically by pickup datetime
    combined_df = combined_df.sort_values(by="tpep_pickup_datetime").reset_index(drop=True)

    sample_csv_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(sample_csv_path, index=False)

    logger.info(f"Sample CSV created successfully at: {sample_csv_path.name}")
    logger.info(f"  Total records: {len(combined_df):,}")
    logger.info(f"  File size: {sample_csv_path.stat().st_size / 1024 / 1024:.2f} MB")

    # Save validation metadata
    metadata = {
        "dataset_name": "yellow_tripdata_2024-01.parquet",
        "sample_row_count": len(combined_df),
        "columns": list(combined_df.columns),
        "min_pickup_datetime": str(combined_df["tpep_pickup_datetime"].min()),
        "max_pickup_datetime": str(combined_df["tpep_pickup_datetime"].max()),
        "unique_pickup_zones": int(combined_df["PULocationID"].nunique()),
        "total_scanned_rows": total_scanned,
    }

    meta_path = base_dir / config["storage"]["sample_dir"] / "sample_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Validation metadata written to: {meta_path.name}")
    return sample_csv_path


def main():
    logger.info("==========================================================")
    logger.info("PHASE 2: DATASET ACQUISITION & VERIFIED SAMPLING")
    logger.info("==========================================================")

    base_dir = Path(__file__).resolve().parent.parent
    config = load_config()

    # 1. Taxi Zone Lookup
    logger.info("[Step 1/3] Processing Taxi Zone Reference Lookup...")
    process_zone_lookup(config, base_dir)

    # 2. Taxi Zone GeoJSON
    logger.info("[Step 2/3] Processing NYC Taxi Zone GeoJSON Polygons...")
    process_zone_geojson(config, base_dir)

    # 3. Yellow Taxi Trip Records & Sample CSV
    logger.info("[Step 3/3] Streaming & Sampling Yellow Taxi Trip Records...")
    sample_trip_records_memory_safe(config, base_dir, target_sample_size=config["dataset"]["sample_size_rows"])

    logger.info("==========================================================")
    logger.info("PHASE 2 DATASET ACQUISITION COMPLETE AND VERIFIED")
    logger.info("==========================================================")


if __name__ == "__main__":
    main()
