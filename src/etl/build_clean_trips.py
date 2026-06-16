from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.utils.paths import PROCESSED_DIR, RAW_DIR, ensure_project_dirs


SERVICE_PATTERNS = {
    "yellow": ("yellow", "yellow_tripdata_*.parquet"),
    "fhvhv": ("fhvhv", "fhvhv_tripdata_*.parquet"),
}


STANDARD_COLUMNS = [
    "service_type",
    "pickup_datetime",
    "dropoff_datetime",
    "pickup_date",
    "pickup_hour",
    "pickup_weekday",
    "pickup_month",
    "pickup_location_id",
    "dropoff_location_id",
    "trip_distance",
    "trip_duration_min",
    "fare_amount",
    "total_amount",
    "driver_pay",
    "tips",
    "payment_type",
    "shared_match_flag",
    "wav_request_flag",
    "is_valid_trip",
    "invalid_reason",
]


def list_files(service: str, sample_files: int | None) -> list[Path]:
    folder, pattern = SERVICE_PATTERNS[service]
    files = sorted((RAW_DIR / folder).glob(pattern))
    if sample_files:
        files = files[:sample_files]
    if not files:
        raise FileNotFoundError(f"No raw files found for service={service}")
    return files


def normalize_yellow(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["service_type"] = "yellow_taxi"
    out["pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"], errors="coerce")
    out["dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"], errors="coerce")
    out["pickup_location_id"] = pd.to_numeric(df["PULocationID"], errors="coerce").astype("Int64")
    out["dropoff_location_id"] = pd.to_numeric(df["DOLocationID"], errors="coerce").astype("Int64")
    out["trip_distance"] = pd.to_numeric(df["trip_distance"], errors="coerce")
    out["fare_amount"] = pd.to_numeric(df["fare_amount"], errors="coerce")
    out["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")
    out["driver_pay"] = pd.NA
    out["tips"] = pd.to_numeric(df.get("tip_amount"), errors="coerce")
    out["payment_type"] = pd.to_numeric(df.get("payment_type"), errors="coerce").astype("Int64")
    out["shared_match_flag"] = pd.NA
    out["wav_request_flag"] = pd.NA
    return out


def normalize_fhvhv(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["service_type"] = "high_volume_fhv"
    out["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"], errors="coerce")
    out["dropoff_datetime"] = pd.to_datetime(df["dropoff_datetime"], errors="coerce")
    out["pickup_location_id"] = pd.to_numeric(df["PULocationID"], errors="coerce").astype("Int64")
    out["dropoff_location_id"] = pd.to_numeric(df["DOLocationID"], errors="coerce").astype("Int64")
    out["trip_distance"] = pd.to_numeric(df["trip_miles"], errors="coerce")
    out["fare_amount"] = pd.to_numeric(df.get("base_passenger_fare"), errors="coerce")
    out["total_amount"] = pd.to_numeric(df.get("base_passenger_fare"), errors="coerce")
    out["driver_pay"] = pd.to_numeric(df.get("driver_pay"), errors="coerce")
    out["tips"] = pd.to_numeric(df.get("tips"), errors="coerce")
    out["payment_type"] = pd.NA
    out["shared_match_flag"] = df.get("shared_match_flag")
    out["wav_request_flag"] = df.get("wav_request_flag")
    return out


def add_features_and_rules(out: pd.DataFrame) -> pd.DataFrame:
    out["trip_duration_min"] = (
        out["dropoff_datetime"] - out["pickup_datetime"]
    ).dt.total_seconds() / 60
    out["pickup_date"] = out["pickup_datetime"].dt.date.astype("string")
    out["pickup_hour"] = out["pickup_datetime"].dt.hour.astype("Int64")
    out["pickup_weekday"] = out["pickup_datetime"].dt.dayofweek.astype("Int64")
    out["pickup_month"] = out["pickup_datetime"].dt.to_period("M").astype("string")

    invalid = pd.Series("", index=out.index, dtype="string")
    rules = [
        (out["pickup_datetime"].isna() | out["dropoff_datetime"].isna(), "missing_time"),
        (out["trip_duration_min"] <= 0, "non_positive_duration"),
        (out["trip_duration_min"] > 8 * 60, "duration_over_8h"),
        (out["trip_distance"].isna() | (out["trip_distance"] <= 0.01), "non_positive_distance"),
        (out["trip_distance"] > 200, "distance_over_200"),
        (out["pickup_location_id"].isna() | out["dropoff_location_id"].isna(), "missing_zone"),
        (out["fare_amount"].notna() & (out["fare_amount"] < 0), "negative_fare"),
        (out["total_amount"].notna() & (out["total_amount"] > 1000), "total_amount_over_1000"),
    ]
    for mask, reason in rules:
        invalid = invalid.mask(mask & (invalid == ""), reason)
    out["invalid_reason"] = invalid.replace("", pd.NA)
    out["is_valid_trip"] = out["invalid_reason"].isna()
    return out[STANDARD_COLUMNS]


def process_file(service: str, path: Path, writer: pq.ParquetWriter | None) -> pq.ParquetWriter:
    dataset = ds.dataset(str(path), format="parquet")
    for batch in dataset.to_batches(batch_size=250_000):
        raw = batch.to_pandas()
        normalized = normalize_yellow(raw) if service == "yellow" else normalize_fhvhv(raw)
        clean = add_features_and_rules(normalized)
        table = pa.Table.from_pandas(clean, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(str(process_file.output_path), table.schema, compression="snappy")
        writer.write_table(table)
    return writer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=sorted(SERVICE_PATTERNS), default="fhvhv")
    parser.add_argument("--sample-files", type=int, default=None)
    args = parser.parse_args()

    ensure_project_dirs()
    files = list_files(args.service, args.sample_files)
    suffix = f"sample_{args.sample_files}" if args.sample_files else "full"
    output_path = PROCESSED_DIR / f"clean_trips_{args.service}_{suffix}.parquet"
    if output_path.exists():
        output_path.unlink()
    process_file.output_path = output_path

    writer = None
    try:
        for path in files:
            print(f"Processing {path.name}")
            writer = process_file(args.service, path, writer)
    finally:
        if writer is not None:
            writer.close()

    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
