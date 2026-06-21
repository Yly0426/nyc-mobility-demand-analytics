"""Build trip-level NYC congestion-relief-zone policy features."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.etl.policy_data import build_policy_features, load_policy_config
from src.utils.project import PROCESSED_DIR, ensure_output_dirs, resolve_project_path


def main() -> int:
    """Run the trip-level geographic and policy feature transformation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/trips_clean_policy_sample.parquet")
    parser.add_argument("--zones", default="data/raw/nyc_tlc/taxi_zone_lookup.csv")
    parser.add_argument("--config", default="config/policy_zones.yaml")
    parser.add_argument("--output", default="data/processed/trip_policy_features.parquet")
    parser.add_argument("--sample", action="store_true", help="Declare that the bounded sample input is being used.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    features = build_policy_features(pd.read_parquet(resolve_project_path(args.input)), pd.read_csv(resolve_project_path(args.zones)), load_policy_config(resolve_project_path(args.config)))
    output = resolve_project_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output, index=False)
    logging.info("Wrote %s rows to %s", len(features), output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
