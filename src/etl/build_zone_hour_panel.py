"""Build a zone-hour panel for policy-impact analysis."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.etl.policy_data import build_zone_hour_panel
from src.utils.project import ensure_output_dirs, resolve_project_path


def main() -> int:
    """Aggregate trip policy features into the reusable zone-hour panel."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/trip_policy_features.parquet")
    parser.add_argument("--output", default="data/processed/zone_hour_policy_panel.parquet")
    parser.add_argument("--sample-output", default="data/outputs/zone_hour_policy_panel_sample.csv")
    parser.add_argument("--sample", action="store_true", help="Declare that the bounded sample input is being used.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    panel = build_zone_hour_panel(pd.read_parquet(resolve_project_path(args.input)))
    panel.to_parquet(resolve_project_path(args.output), index=False)
    panel.head(5000).to_csv(resolve_project_path(args.sample_output), index=False)
    logging.info("Wrote %s zone-hour observations", len(panel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
