from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.utils.paths import RAW_DIR, REPORTS_DIR, TABLES_DIR, ensure_project_dirs


SERVICE_PATTERNS = {
    "yellow": ("yellow", "yellow_tripdata_*.parquet"),
    "fhvhv": ("fhvhv", "fhvhv_tripdata_*.parquet"),
}


def list_files(service: str, sample_files: int | None) -> list[Path]:
    folder, pattern = SERVICE_PATTERNS[service]
    files = sorted((RAW_DIR / folder).glob(pattern))
    if sample_files:
        files = files[:sample_files]
    if not files:
        raise FileNotFoundError(f"No raw files found for service={service}")
    return files


def count_rows(file_path: Path) -> int:
    return pq.ParquetFile(file_path).metadata.num_rows


def schema_report(files: list[Path]) -> pd.DataFrame:
    rows = []
    for file_path in files:
        schema = pq.read_schema(file_path)
        for field in schema:
            rows.append(
                {
                    "file": file_path.name,
                    "column": field.name,
                    "type": str(field.type),
                }
            )
    return pd.DataFrame(rows)


def sample_quality(service: str, files: list[Path], max_rows: int) -> dict:
    dataset = ds.dataset([str(path) for path in files], format="parquet")
    scanner = dataset.scanner(batch_size=65536)
    batches = []
    rows_seen = 0
    for batch in scanner.to_batches():
        batches.append(batch)
        rows_seen += batch.num_rows
        if rows_seen >= max_rows:
            break
    sample = pd.concat([batch.to_pandas() for batch in batches], ignore_index=True).head(max_rows)

    if service == "yellow":
        start_col = "tpep_pickup_datetime"
        end_col = "tpep_dropoff_datetime"
        distance_col = "trip_distance"
        fare_col = "fare_amount"
        total_col = "total_amount"
        pickup_col = "PULocationID"
        dropoff_col = "DOLocationID"
    else:
        start_col = "pickup_datetime"
        end_col = "dropoff_datetime"
        distance_col = "trip_miles"
        fare_col = "base_passenger_fare"
        total_col = "driver_pay"
        pickup_col = "PULocationID"
        dropoff_col = "DOLocationID"

    sample[start_col] = pd.to_datetime(sample[start_col], errors="coerce")
    sample[end_col] = pd.to_datetime(sample[end_col], errors="coerce")
    duration_min = (sample[end_col] - sample[start_col]).dt.total_seconds() / 60

    metrics = {
        "service": service,
        "sample_rows": int(len(sample)),
        "null_pickup_time": int(sample[start_col].isna().sum()),
        "null_dropoff_time": int(sample[end_col].isna().sum()),
        "negative_or_zero_duration": int((duration_min <= 0).sum()),
        "duration_over_8h": int((duration_min > 8 * 60).sum()),
        "missing_pickup_zone": int(sample[pickup_col].isna().sum()),
        "missing_dropoff_zone": int(sample[dropoff_col].isna().sum()),
        "non_positive_distance": int((sample[distance_col] <= 0).sum()),
        "distance_over_200": int((sample[distance_col] > 200).sum()),
    }
    if fare_col in sample:
        metrics["negative_fare"] = int((sample[fare_col] < 0).sum())
    if total_col in sample:
        metrics["negative_total_or_pay"] = int((sample[total_col] < 0).sum())
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=sorted(SERVICE_PATTERNS), default="fhvhv")
    parser.add_argument("--sample-files", type=int, default=None)
    parser.add_argument("--quality-sample-rows", type=int, default=250_000)
    args = parser.parse_args()

    ensure_project_dirs()
    files = list_files(args.service, args.sample_files)

    inventory = pd.DataFrame(
        [
            {
                "service": args.service,
                "file": path.name,
                "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
                "rows": count_rows(path),
            }
            for path in files
        ]
    )
    schema = schema_report(files)
    quality = sample_quality(args.service, files, args.quality_sample_rows)

    inventory_path = TABLES_DIR / f"{args.service}_raw_inventory.csv"
    schema_path = TABLES_DIR / f"{args.service}_raw_schema.csv"
    quality_path = REPORTS_DIR / f"{args.service}_quality_sample.json"
    inventory.to_csv(inventory_path, index=False)
    schema.to_csv(schema_path, index=False)
    quality_path.write_text(json.dumps(quality, indent=2), encoding="utf-8")

    print(inventory)
    print(json.dumps(quality, indent=2))
    print(f"Wrote {inventory_path}")
    print(f"Wrote {schema_path}")
    print(f"Wrote {quality_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

