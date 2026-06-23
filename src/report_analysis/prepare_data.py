"""Prepare the report-ready DWD feature dataset from the bounded HVFHV sample."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.utils.project import PROCESSED_DIR, resolve_project_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/trip_policy_features.parquet")
    parser.add_argument("--output", default="data/processed/dwd_hvfhv_trip_clean.parquet")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    data = pd.read_parquet(resolve_project_path(args.input)).copy()
    data["trip_id"] = range(1, len(data) + 1)
    data["trip_time_min"] = data["trip_time"]
    data["policy_period"] = data["post_policy"].map({False: "政策前", True: "政策后"})
    data["is_core_zone_trip"] = data["is_pickup_treated"]
    data["is_boundary_zone_trip"] = data["is_pickup_spillover"]
    data["pickup_zone"] = data["pickup_zone_name"]
    data["dropoff_zone"] = data["dropoff_zone_name"]
    ordered = [
        "trip_id", "request_datetime", "on_scene_datetime", "pickup_datetime", "dropoff_datetime",
        "trip_date", "trip_hour", "weekday", "is_weekend", "pickup_location_id", "dropoff_location_id",
        "pickup_zone", "dropoff_zone", "pickup_borough", "dropoff_borough", "trip_miles", "trip_time_min",
        "base_passenger_fare", "tolls", "congestion_surcharge", "cbd_congestion_fee", "airport_fee", "driver_pay",
        "fare_per_mile", "fare_per_minute", "driver_pay_per_mile", "driver_pay_per_minute", "response_time_min",
        "is_airport_trip", "is_core_zone_trip", "is_boundary_zone_trip", "policy_period",
    ]
    output = resolve_project_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data[ordered].to_parquet(output, index=False)
    logging.info("Prepared %s DWD trips at %s", len(data), output.relative_to(resolve_project_path(".")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
