"""Compatibility entry point for Yellow Taxi policy-data cleaning."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.etl.policy_data import normalize_yellow
from src.utils.project import ensure_output_dirs, resolve_project_path


def main() -> int:
    """Normalize a Yellow Taxi Parquet source for the policy schema."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="data/processed/yellow_clean_policy.parquet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    normalize_yellow(pd.read_parquet(resolve_project_path(args.input))).to_parquet(resolve_project_path(args.output), index=False)
    logging.info("Wrote %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
