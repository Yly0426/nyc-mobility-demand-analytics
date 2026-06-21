"""Build an OD-hour panel for policy and route strategy analysis."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.etl.policy_data import build_od_panel
from src.utils.project import ensure_output_dirs, resolve_project_path


def main() -> int:
    """Aggregate policy-enriched trips to the origin-destination grain."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/trip_policy_features.parquet")
    parser.add_argument("--output", default="data/processed/od_policy_panel.parquet")
    parser.add_argument("--sample", action="store_true", help="Declare that the bounded sample input is being used.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    panel = build_od_panel(pd.read_parquet(resolve_project_path(args.input)))
    output = resolve_project_path(args.output)
    panel.to_parquet(output, index=False)
    logging.info("Wrote %s OD-hour observations", len(panel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
