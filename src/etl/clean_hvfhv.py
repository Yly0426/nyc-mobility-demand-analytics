"""Clean High Volume For-Hire Vehicle records for policy analysis."""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.etl.policy_data import normalize_hvfhv
from src.utils.project import ensure_output_dirs, resolve_project_path


def read_bounded_parquet(path: Path, max_rows: int) -> pd.DataFrame:
    """Read a time-spread sample across a monthly Parquet file's row groups."""
    parquet_file = pq.ParquetFile(path)
    group_count = min(parquet_file.num_row_groups, 12)
    if group_count == 0:
        return pd.DataFrame()
    if group_count == 1:
        selected_groups = [0]
    else:
        selected_groups = sorted({round(index * (parquet_file.num_row_groups - 1) / (group_count - 1)) for index in range(group_count)})
    rows_per_group = math.ceil(max_rows / len(selected_groups))
    pieces: list[pd.DataFrame] = []
    for position, group_index in enumerate(selected_groups):
        piece = parquet_file.read_row_group(group_index).to_pandas()
        if len(piece) > rows_per_group:
            piece = piece.sample(n=rows_per_group, random_state=42 + position)
        pieces.append(piece)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).sample(frac=1, random_state=42).head(max_rows).reset_index(drop=True)


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
