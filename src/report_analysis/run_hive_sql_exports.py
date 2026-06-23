"""Export Hive-SQL-equivalent DWS metrics locally with Pandas.

The SQL scripts under sql/hive remain the warehouse contract. This module keeps
the portfolio pipeline runnable on a laptop without claiming a Hive connection.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from src.analysis.analysis_utils import save_table
from src.utils.project import resolve_project_path


def _distance_group(series: pd.Series) -> pd.Series:
    return pd.cut(series, [0, 2, 8, np.inf], labels=["短途(0-2英里)", "中途(2-8英里)", "长途(8+英里)"], right=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/dwd_hvfhv_trip_clean.parquet")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = pd.read_parquet(resolve_project_path(args.input)).copy()
    data["hour_group"] = pd.cut(data["trip_hour"], [-1, 5, 9, 16, 20, 23], labels=["夜间", "早高峰", "日间", "晚高峰", "深夜"])
    data["trip_distance_group"] = _distance_group(data["trip_miles"])

    time = data.groupby(["trip_date", "trip_hour", "weekday", "is_weekend"], observed=True).agg(
        order_count=("trip_id", "size"), avg_trip_miles=("trip_miles", "mean"),
        avg_base_passenger_fare=("base_passenger_fare", "mean"), avg_driver_pay=("driver_pay", "mean"),
    ).reset_index().rename(columns={"trip_date": "date", "trip_hour": "hour"})
    save_table(time, "time_demand_metrics.csv")

    pickup = data.groupby(["pickup_zone", "pickup_borough"], dropna=False).agg(
        pickup_order_count=("trip_id", "size"), avg_fare_per_mile=("fare_per_mile", "mean"),
        avg_driver_pay_per_minute=("driver_pay_per_minute", "mean"), avg_response_time_min=("response_time_min", "mean"),
    ).reset_index()
    dropoff = data.groupby(["dropoff_zone", "dropoff_borough"], dropna=False).size().reset_index(name="dropoff_order_count")
    zone = pickup.merge(dropoff, left_on=["pickup_zone", "pickup_borough"], right_on=["dropoff_zone", "dropoff_borough"], how="outer")
    save_table(zone, "zone_demand_metrics.csv")
    save_table(pickup.nlargest(20, "pickup_order_count"), "top_pickup_zones.csv")
    save_table(dropoff.nlargest(20, "dropoff_order_count"), "top_dropoff_zones.csv")

    od = data.groupby(["pickup_zone", "dropoff_zone", "pickup_borough", "dropoff_borough"], dropna=False).agg(
        order_count=("trip_id", "size"), avg_trip_miles=("trip_miles", "mean"), avg_trip_time_min=("trip_time_min", "mean"),
        avg_base_passenger_fare=("base_passenger_fare", "mean"), avg_fare_per_mile=("fare_per_mile", "mean"),
        avg_driver_pay=("driver_pay", "mean"), avg_driver_pay_per_minute=("driver_pay_per_minute", "mean"),
        avg_response_time_min=("response_time_min", "mean"),
    ).reset_index()
    save_table(od, "od_route_metrics.csv")
    save_table(od.nlargest(30, "order_count"), "top_od_routes.csv")

    price = data.groupby(["trip_distance_group", "hour_group", "policy_period"], observed=True).agg(
        order_count=("trip_id", "size"), avg_fare_per_mile=("fare_per_mile", "mean"), avg_fare_per_minute=("fare_per_minute", "mean"),
        avg_tolls=("tolls", "mean"), avg_cbd_congestion_fee=("cbd_congestion_fee", "mean"),
        avg_driver_pay_per_mile=("driver_pay_per_mile", "mean"), avg_driver_pay_per_minute=("driver_pay_per_minute", "mean"),
        driver_pay_to_fare_ratio=("driver_pay_per_mile", lambda x: np.nan),
    ).reset_index()
    ratio = data.groupby(["trip_distance_group", "hour_group", "policy_period"], observed=True)["driver_pay"].mean() / data.groupby(["trip_distance_group", "hour_group", "policy_period"], observed=True)["base_passenger_fare"].mean()
    price["driver_pay_to_fare_ratio"] = ratio.to_numpy()
    save_table(price, "price_driver_metrics.csv")

    response = data.dropna(subset=["response_time_min"]).groupby(["pickup_zone", "trip_hour"], dropna=False).agg(
        order_count=("trip_id", "size"), avg_response_time_min=("response_time_min", "mean"),
        p50_response_time_min=("response_time_min", "median"), p90_response_time_min=("response_time_min", lambda x: x.quantile(.9)),
        slow_response_rate=("response_time_min", lambda x: (x > 10).mean()),
    ).reset_index().rename(columns={"trip_hour": "hour"})
    save_table(response, "response_metrics.csv")
    # Four report-level recommendations. These are transparent candidates, not an execution engine.
    # The pickup metric already contains the zone-level response proxy.
    zone_scores = pickup.copy()
    high_supply = zone_scores.nlargest(4, "avg_response_time_min").assign(
        recommendation_type="driver_supply_reallocation", target_zone_or_route=lambda x: x["pickup_zone"],
        evidence_metric=lambda x: "平均响应代理 " + x["avg_response_time_min"].round(2).astype(str) + " 分钟",
        recommended_action="在高需求时段前预部署司机并监控响应代理", business_value="降低可能的供给滞后", confidence_level="低",
    )
    route_priority = od.nlargest(4, "order_count").assign(
        recommendation_type="route_priority", target_zone_or_route=lambda x: x["pickup_zone"] + " → " + x["dropoff_zone"],
        evidence_metric=lambda x: "订单量 " + x["order_count"].astype(int).astype(str),
        recommended_action="将高频路线纳入重点保障与运力观察", business_value="保障核心出行场景", confidence_level="中",
    )
    driver_incentive = od.nlargest(20, "order_count").nsmallest(4, "avg_driver_pay_per_minute").assign(
        recommendation_type="driver_incentive", target_zone_or_route=lambda x: x["pickup_zone"] + " → " + x["dropoff_zone"],
        evidence_metric=lambda x: "司机每分钟收益 " + x["avg_driver_pay_per_minute"].round(2).astype(str),
        recommended_action="先以小范围激励测试接单与履约变化", business_value="缓解高频低收益路线供给压力", confidence_level="低",
    )
    passenger_discount = od.nlargest(20, "order_count").nlargest(4, "avg_fare_per_mile").assign(
        recommendation_type="passenger_discount", target_zone_or_route=lambda x: x["pickup_zone"] + " → " + x["dropoff_zone"],
        evidence_metric=lambda x: "每英里票价 " + x["avg_fare_per_mile"].round(2).astype(str),
        recommended_action="在验证需求弹性后测试定向优惠", business_value="降低高价格路线的需求流失风险", confidence_level="低",
    )
    recommendations = pd.concat([high_supply, route_priority, driver_incentive, passenger_discount], ignore_index=True)
    save_table(recommendations[["recommendation_type", "target_zone_or_route", "evidence_metric", "recommended_action", "business_value", "confidence_level"]], "business_recommendations.csv")
    logging.info("Exported Hive-compatible metric tables from %s trips", len(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
