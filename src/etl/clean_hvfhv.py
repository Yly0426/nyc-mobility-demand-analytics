"""Clean High Volume For-Hire Vehicle records for policy analysis."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.etl.policy_data import normalize_hvfhv
from src.utils.project import ensure_output_dirs, resolve_project_path


def read_bounded_parquet(path: Path, max_rows: int) -> pd.DataFrame:
    """Read up to max_rows from a Parquet file by record batch."""
    pieces: list[pd.DataFrame] = []
    remaining = max_rows
    for batch in pq.ParquetFile(path).iter_batches(batch_size=min(100_000, max_rows)):
        piece = batch.to_pandas().head(remaining)
        pieces.append(piece)
        remaining -= len(piece)
        if remaining <= 0:
            break
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def clean_files(files: list[Path], rows_per_file: int) -> pd.DataFrame:
    """Read and normalize a bounded sample from each requested monthly file."""
    cleaned: list[pd.DataFrame] = []
    for path in files:
        logging.info("Reading sample from %s", path.name)
        cleaned.append(normalize_hvfhv(read_bounded_parquet(path, rows_per_file)))
    return pd.concat(cleaned, ignore_index=True)


def main() -> int:
    """Clean supplied files or selected policy-window raw files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", default="data/raw/nyc_tlc/fhvhv/fhvhv_tripdata_*.parquet")
    parser.add_argument("--months", nargs="*", default=["2024-11", "2024-12", "2025-01", "2025-02", "2025-03"])
    parser.add_argument("--rows-per-file", type=int, default=100_000)
    parser.add_argument("--output", default="data/processed/trips_clean_policy_sample.parquet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    files = [path for path in sorted(resolve_project_path(args.input_glob).parent.glob(Path(args.input_glob).name)) if any(month in path.name for month in args.months)]
    if not files:
        raise FileNotFoundError("No HVFHV Parquet files matched the selected months")
    clean_files(files, args.rows_per_file).to_parquet(resolve_project_path(args.output), index=False)
    logging.info("Wrote cleaned policy sample to %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
