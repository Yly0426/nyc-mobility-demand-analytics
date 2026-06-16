from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

from src.utils.paths import PROCESSED_DIR, RAW_DIR, TABLES_DIR, WAREHOUSE_DIR, ensure_project_dirs


def find_clean_file(service: str, sample_files: int | None) -> Path:
    suffix = f"sample_{sample_files}" if sample_files else "full"
    path = PROCESSED_DIR / f"clean_trips_{service}_{suffix}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Clean file does not exist: {path}")
    return path


def add_group(store: list[pd.DataFrame], df: pd.DataFrame, keys: list[str], values: dict[str, str]) -> None:
    grouped = df.groupby(keys, dropna=False).agg(**values).reset_index()
    store.append(grouped)


def combine_groups(groups: list[pd.DataFrame], keys: list[str]) -> pd.DataFrame:
    if not groups:
        return pd.DataFrame()
    frame = pd.concat(groups, ignore_index=True)
    numeric_cols = [col for col in frame.columns if col not in keys]
    return frame.groupby(keys, dropna=False)[numeric_cols].sum().reset_index()


def load_zones() -> pd.DataFrame:
    zones = pd.read_csv(RAW_DIR / "taxi_zone_lookup.csv")
    zones = zones.rename(
        columns={
            "LocationID": "pickup_location_id",
            "Borough": "pickup_borough",
            "Zone": "pickup_zone",
            "service_zone": "pickup_service_zone",
        }
    )
    return zones


def build_metrics(clean_path: Path, service: str, output_suffix: str) -> None:
    dataset = ds.dataset(str(clean_path), format="parquet")
    hourly_groups: list[pd.DataFrame] = []
    zone_hourly_groups: list[pd.DataFrame] = []
    od_groups: list[pd.DataFrame] = []
    invalid_groups: list[pd.DataFrame] = []

    for batch in dataset.to_batches(batch_size=300_000):
        df = batch.to_pandas()
        valid = df[df["is_valid_trip"]].copy()

        if not valid.empty:
            valid["distance_sum"] = valid["trip_distance"].fillna(0)
            valid["duration_sum"] = valid["trip_duration_min"].fillna(0)
            valid["fare_sum"] = valid["fare_amount"].fillna(0)
            valid["tips_sum"] = valid["tips"].fillna(0)
            valid["driver_pay_sum"] = valid["driver_pay"].fillna(0)

            add_group(
                hourly_groups,
                valid,
                ["service_type", "pickup_date", "pickup_hour", "pickup_weekday", "pickup_month"],
                {
                    "trip_count": ("service_type", "size"),
                    "distance_sum": ("distance_sum", "sum"),
                    "duration_sum": ("duration_sum", "sum"),
                    "fare_sum": ("fare_sum", "sum"),
                    "tips_sum": ("tips_sum", "sum"),
                    "driver_pay_sum": ("driver_pay_sum", "sum"),
                },
            )
            add_group(
                zone_hourly_groups,
                valid,
                ["service_type", "pickup_date", "pickup_hour", "pickup_location_id"],
                {
                    "trip_count": ("service_type", "size"),
                    "distance_sum": ("distance_sum", "sum"),
                    "duration_sum": ("duration_sum", "sum"),
                    "fare_sum": ("fare_sum", "sum"),
                },
            )
            add_group(
                od_groups,
                valid,
                ["service_type", "pickup_location_id", "dropoff_location_id"],
                {
                    "trip_count": ("service_type", "size"),
                    "distance_sum": ("distance_sum", "sum"),
                    "duration_sum": ("duration_sum", "sum"),
                    "fare_sum": ("fare_sum", "sum"),
                },
            )

        invalid = df[~df["is_valid_trip"]].copy()
        if not invalid.empty:
            add_group(
                invalid_groups,
                invalid,
                ["service_type", "invalid_reason"],
                {"record_count": ("service_type", "size")},
            )

    hourly = combine_groups(
        hourly_groups,
        ["service_type", "pickup_date", "pickup_hour", "pickup_weekday", "pickup_month"],
    )
    zone_hourly = combine_groups(
        zone_hourly_groups,
        ["service_type", "pickup_date", "pickup_hour", "pickup_location_id"],
    )
    od = combine_groups(
        od_groups,
        ["service_type", "pickup_location_id", "dropoff_location_id"],
    )
    invalid_summary = combine_groups(invalid_groups, ["service_type", "invalid_reason"])

    for frame in [hourly, zone_hourly, od]:
        if frame.empty:
            continue
        frame["avg_distance"] = frame["distance_sum"] / frame["trip_count"]
        frame["avg_duration_min"] = frame["duration_sum"] / frame["trip_count"]
        frame["avg_fare"] = frame["fare_sum"] / frame["trip_count"]
        frame["fare_per_mile"] = frame["fare_sum"] / frame["distance_sum"].replace(0, pd.NA)

    zones = load_zones()
    zone_hourly = zone_hourly.merge(zones, on="pickup_location_id", how="left")
    top_od = od.sort_values("trip_count", ascending=False).head(5000)

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(WAREHOUSE_DIR / f"hourly_demand_{service}_{output_suffix}.csv", index=False)
    zone_hourly.to_csv(WAREHOUSE_DIR / f"zone_hourly_demand_{service}_{output_suffix}.csv", index=False)
    top_od.to_csv(WAREHOUSE_DIR / f"top_od_flows_{service}_{output_suffix}.csv", index=False)
    invalid_summary.to_csv(WAREHOUSE_DIR / f"invalid_trip_summary_{service}_{output_suffix}.csv", index=False)

    # Small report-friendly copies.
    hourly.sort_values("trip_count", ascending=False).head(100).to_csv(
        TABLES_DIR / f"top_hourly_demand_{service}_{output_suffix}.csv", index=False
    )
    zone_hourly.sort_values("trip_count", ascending=False).head(100).to_csv(
        TABLES_DIR / f"top_zone_hourly_demand_{service}_{output_suffix}.csv", index=False
    )

    print(f"Wrote warehouse metrics for {service}_{output_suffix}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=["yellow", "fhvhv"], default="fhvhv")
    parser.add_argument("--sample-files", type=int, default=None)
    args = parser.parse_args()

    ensure_project_dirs()
    suffix = f"sample_{args.sample_files}" if args.sample_files else "full"
    build_metrics(find_clean_file(args.service, args.sample_files), args.service, suffix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

