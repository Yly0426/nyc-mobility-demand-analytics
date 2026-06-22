"""Run the reproducible policy-data pipeline, including a bounded sample mode."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.analysis.analysis_utils import save_table
from src.etl.clean_hvfhv import clean_files
from src.etl.policy_data import build_od_panel, build_policy_features, build_zone_hour_panel, load_policy_config
from src.utils.project import PROCESSED_DIR, PROJECT_ROOT, ensure_output_dirs


def selected_sample_files() -> list:
    """Select a compact pre/post policy window from raw HVFHV data."""
    root = PROJECT_ROOT / "data/raw/nyc_tlc/fhvhv"
    months = ("2024-11", "2024-12", "2025-01", "2025-02", "2025-03")
    return [path for path in sorted(root.glob("fhvhv_tripdata_*.parquet")) if any(month in path.name for month in months)]


def main() -> int:
    """Create cleaned trips, policy features, zone-hour and OD panels."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="Read bounded samples from policy-window months")
    parser.add_argument("--rows-per-file", type=int, default=100_000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    files = selected_sample_files()
    if not files:
        raise FileNotFoundError("Policy-window raw files are not available")
    rows = args.rows_per_file if args.sample else 1_000_000
    trips = clean_files(files, rows)
    trips.to_parquet(PROCESSED_DIR / "trips_clean_policy_sample.parquet", index=False)
    config = load_policy_config(PROJECT_ROOT / "config/policy_zones.yaml")
    zones = pd.read_csv(PROJECT_ROOT / "data/raw/nyc_tlc/taxi_zone_lookup.csv")
    features = build_policy_features(trips, zones, config)
    features.to_parquet(PROCESSED_DIR / "trip_policy_features.parquet", index=False)
    zone_panel = build_zone_hour_panel(features)
    od_panel = build_od_panel(features)
    zone_panel.to_parquet(PROCESSED_DIR / "zone_hour_policy_panel.parquet", index=False)
    od_panel.to_parquet(PROCESSED_DIR / "od_policy_panel.parquet", index=False)
    zone_panel.head(5000).to_csv(PROJECT_ROOT / "data/outputs/zone_hour_policy_panel_sample.csv", index=False)
    sample_input_count = len(files) * rows
    quality = pd.DataFrame([{
        "source_table": "HVFHV bounded sample input",
        "raw_count": sample_input_count,
        "valid_count": len(features),
        "dropped_count": max(sample_input_count - len(features), 0),
        "drop_rate": max(sample_input_count - len(features), 0) / sample_input_count if sample_input_count else 0,
        "drop_reason": "invalid time, location, distance, duration or fare values",
    }])
    save_table(quality, "data_quality_summary.csv")
    logging.info("Pipeline complete: %s trips, %s zone-hours, %s OD-hours", len(features), len(zone_panel), len(od_panel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
