"""Reusable transformations for congestion-pricing policy panels."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.utils.project import load_yaml

LOGGER = logging.getLogger(__name__)


def _read_parquet_sample(path: Path, max_rows: int | None) -> pd.DataFrame:
    """Read a bounded Parquet sample without requiring a full monthly load."""
    frame = pd.read_parquet(path)
    if max_rows and len(frame) > max_rows:
        return frame.sample(n=max_rows, random_state=42)
    return frame


def normalize_hvfhv(raw: pd.DataFrame) -> pd.DataFrame:
    """Map HVFHV trip records to the policy-analysis canonical schema."""
    data = pd.DataFrame(index=raw.index)
    data["service_type"] = "high_volume_fhv"
    data["request_datetime"] = pd.to_datetime(raw.get("request_datetime", pd.Series(pd.NaT, index=raw.index)), errors="coerce")
    data["on_scene_datetime"] = pd.to_datetime(raw.get("on_scene_datetime", pd.Series(pd.NaT, index=raw.index)), errors="coerce")
    data["pickup_datetime"] = pd.to_datetime(raw["pickup_datetime"], errors="coerce")
    data["dropoff_datetime"] = pd.to_datetime(raw["dropoff_datetime"], errors="coerce")
    data["pickup_location_id"] = pd.to_numeric(raw["PULocationID"], errors="coerce")
    data["dropoff_location_id"] = pd.to_numeric(raw["DOLocationID"], errors="coerce")
    data["trip_miles"] = pd.to_numeric(raw.get("trip_miles"), errors="coerce")
    data["base_passenger_fare"] = pd.to_numeric(raw.get("base_passenger_fare"), errors="coerce")
    data["total_amount"] = data["base_passenger_fare"]
    data["driver_pay"] = pd.to_numeric(raw.get("driver_pay"), errors="coerce")
    data["tips"] = pd.to_numeric(raw.get("tips"), errors="coerce").fillna(0)
    data["tolls"] = pd.to_numeric(raw.get("tolls"), errors="coerce").fillna(0)
    return _finish_clean(data)


def normalize_yellow(raw: pd.DataFrame) -> pd.DataFrame:
    """Map Yellow Taxi records to the same schema; driver pay is unavailable."""
    data = pd.DataFrame(index=raw.index)
    data["service_type"] = "yellow_taxi"
    # Yellow Taxi data has no equivalent request/arrival timestamps.
    data["request_datetime"] = pd.NaT
    data["on_scene_datetime"] = pd.NaT
    data["pickup_datetime"] = pd.to_datetime(raw["tpep_pickup_datetime"], errors="coerce")
    data["dropoff_datetime"] = pd.to_datetime(raw["tpep_dropoff_datetime"], errors="coerce")
    data["pickup_location_id"] = pd.to_numeric(raw["PULocationID"], errors="coerce")
    data["dropoff_location_id"] = pd.to_numeric(raw["DOLocationID"], errors="coerce")
    data["trip_miles"] = pd.to_numeric(raw.get("trip_distance"), errors="coerce")
    data["base_passenger_fare"] = pd.to_numeric(raw.get("fare_amount"), errors="coerce")
    data["total_amount"] = pd.to_numeric(raw.get("total_amount"), errors="coerce")
    data["driver_pay"] = pd.NA
    data["tips"] = pd.to_numeric(raw.get("tip_amount"), errors="coerce").fillna(0)
    data["tolls"] = pd.to_numeric(raw.get("tolls_amount"), errors="coerce").fillna(0)
    return _finish_clean(data)


def _finish_clean(data: pd.DataFrame) -> pd.DataFrame:
    """Add common time fields and filter trips unsuitable for policy metrics."""
    data["trip_time"] = (data["dropoff_datetime"] - data["pickup_datetime"]).dt.total_seconds() / 60
    data = data.loc[
        data["pickup_datetime"].notna()
        & data["dropoff_datetime"].notna()
        & data["pickup_location_id"].notna()
        & data["dropoff_location_id"].notna()
        & data["trip_miles"].between(0.01, 200)
        & data["trip_time"].between(1, 480)
        & data["base_passenger_fare"].ge(0)
    ].copy()
    data["pickup_location_id"] = data["pickup_location_id"].astype(int)
    data["dropoff_location_id"] = data["dropoff_location_id"].astype(int)
    data["response_time_min"] = (data["on_scene_datetime"] - data["request_datetime"]).dt.total_seconds() / 60
    data["pickup_wait_proxy_min"] = (data["pickup_datetime"] - data["request_datetime"]).dt.total_seconds() / 60
    # Preserve trips with unavailable platform-arrival data, but discard impossible proxy values.
    for column in ("response_time_min", "pickup_wait_proxy_min"):
        data.loc[~data[column].between(0, 240), column] = pd.NA
    data["slow_response_flag"] = data["response_time_min"].gt(10)
    return data


def build_policy_features(trips: pd.DataFrame, zones: pd.DataFrame, policy_config: dict) -> pd.DataFrame:
    """Attach geographic policy groups and policy-period flags to trips."""
    zone_ref = zones.rename(columns={"LocationID": "zone_id", "Zone": "zone_name", "Borough": "borough"})
    group_map = {
        zone: group
        for group, names in policy_config["zone_groups"].items()
        for zone in names
    }
    airport_names = set(policy_config.get("airport_zone_names", []))
    pickup = zone_ref[["zone_id", "zone_name", "borough"]].rename(
        columns={"zone_id": "pickup_location_id", "zone_name": "pickup_zone_name", "borough": "pickup_borough"}
    )
    dropoff = zone_ref[["zone_id", "zone_name", "borough"]].rename(
        columns={"zone_id": "dropoff_location_id", "zone_name": "dropoff_zone_name", "borough": "dropoff_borough"}
    )
    data = trips.merge(pickup, on="pickup_location_id", how="left").merge(dropoff, on="dropoff_location_id", how="left")
    data["pickup_zone_group"] = data["pickup_zone_name"].map(group_map).fillna("other")
    data["dropoff_zone_group"] = data["dropoff_zone_name"].map(group_map).fillna("other")
    for group in ("treated", "spillover", "control"):
        data[f"is_pickup_{group}"] = data["pickup_zone_group"].eq(f"{group}_zones")
        data[f"is_dropoff_{group}"] = data["dropoff_zone_group"].eq(f"{group}_zones")
    data["is_cross_treated_trip"] = data["is_pickup_treated"] ^ data["is_dropoff_treated"]
    data["is_airport_trip"] = data["pickup_zone_name"].isin(airport_names) | data["dropoff_zone_name"].isin(airport_names)
    data["policy_date"] = pd.Timestamp(policy_config["policy"]["start_date"])
    data["trip_date"] = data["pickup_datetime"].dt.normalize()
    data["post_policy"] = data["trip_date"].ge(data["policy_date"])
    data["trip_hour"] = data["pickup_datetime"].dt.hour
    data["weekday"] = data["pickup_datetime"].dt.dayofweek
    data["is_weekend"] = data["weekday"].ge(5)
    data["fare_per_mile"] = data["base_passenger_fare"] / data["trip_miles"].clip(lower=0.01)
    data["fare_per_minute"] = data["base_passenger_fare"] / data["trip_time"].clip(lower=1)
    data["driver_pay_per_mile"] = data["driver_pay"] / data["trip_miles"].clip(lower=0.01)
    data["driver_pay_per_minute"] = data["driver_pay"] / data["trip_time"].clip(lower=1)
    data["tip_rate"] = data["tips"] / data["base_passenger_fare"].clip(lower=0.01)
    data["driver_pay_to_fare_ratio"] = data["driver_pay"] / data["base_passenger_fare"].clip(lower=0.01)
    return data


def build_zone_hour_panel(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate policy features to pickup zone-date-hour observations."""
    group_keys = ["pickup_location_id", "pickup_zone_name", "pickup_borough", "pickup_zone_group", "trip_date", "trip_hour", "weekday", "is_weekend", "post_policy"]
    aggregation = data.groupby(group_keys, dropna=False).agg(
        order_count=("service_type", "size"), avg_trip_miles=("trip_miles", "mean"), avg_trip_time=("trip_time", "mean"),
        avg_base_fare=("base_passenger_fare", "mean"), avg_total_amount=("total_amount", "mean"), avg_driver_pay=("driver_pay", "mean"),
        avg_fare_per_mile=("fare_per_mile", "mean"), avg_driver_pay_per_minute=("driver_pay_per_minute", "mean"),
        avg_tolls=("tolls", "mean"), airport_trip_count=("is_airport_trip", "sum"),
        avg_response_time_min=("response_time_min", "mean"), response_time_p50=("response_time_min", "median"),
        response_time_p90=("response_time_min", lambda values: values.quantile(0.9)),
        slow_response_rate=("slow_response_flag", "mean"), valid_response_count=("response_time_min", "count"),
        short_trip_count=("trip_miles", lambda s: (s < 2).sum()), long_trip_count=("trip_miles", lambda s: (s >= 8).sum()),
        treated_pickup_count=("is_pickup_treated", "sum"), treated_dropoff_count=("is_dropoff_treated", "sum"),
        spillover_pickup_count=("is_pickup_spillover", "sum"), control_pickup_count=("is_pickup_control", "sum"),
    ).reset_index().rename(columns={"pickup_location_id": "zone_id", "pickup_zone_name": "zone_name", "trip_hour": "hour", "pickup_zone_group": "zone_group"})
    aggregation["treated_zone"] = aggregation["zone_group"].eq("treated_zones")
    aggregation["log_order_count"] = (aggregation["order_count"] + 1).map(__import__("numpy").log)
    return aggregation


def build_od_panel(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate policy features to origin-destination-date-hour observations."""
    keys = ["pickup_location_id", "pickup_zone_name", "dropoff_location_id", "dropoff_zone_name", "trip_date", "trip_hour", "post_policy"]
    return data.groupby(keys, dropna=False).agg(
        od_order_count=("service_type", "size"), avg_trip_miles=("trip_miles", "mean"), avg_trip_time=("trip_time", "mean"),
        avg_base_fare=("base_passenger_fare", "mean"), avg_driver_pay=("driver_pay", "mean"), avg_tolls=("tolls", "mean"),
        avg_fare_per_mile=("fare_per_mile", "mean"), avg_driver_pay_per_minute=("driver_pay_per_minute", "mean"),
        avg_response_time_min=("response_time_min", "mean"), response_time_p90=("response_time_min", lambda values: values.quantile(0.9)),
        slow_response_rate=("slow_response_flag", "mean"), valid_response_count=("response_time_min", "count"),
        is_cross_treated_od=("is_cross_treated_trip", "max"), is_airport_od=("is_airport_trip", "max"),
    ).reset_index().rename(columns={"trip_hour": "hour"})


def load_policy_config(path: str | Path) -> dict:
    """Load the policy configuration file."""
    return load_yaml(path)
