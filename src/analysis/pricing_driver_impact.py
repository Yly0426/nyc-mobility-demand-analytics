"""Assess passenger price and driver-pay proxy changes at OD level."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import numpy as np

from src.analysis.analysis_utils import read_panel, save_plot, save_table


def main() -> int:
    """Produce pre/post OD metrics for pricing and driver-side operations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/trip_policy_features.parquet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = read_panel(args.input)
    keys = ["pickup_zone_name", "dropoff_zone_name", "is_cross_treated_trip", "is_airport_trip", "post_policy"]
    metrics = data.groupby(keys).agg(
        trip_count=("service_type", "size"), fare_per_mile=("fare_per_mile", "mean"), fare_per_minute=("fare_per_minute", "mean"),
        driver_pay_per_mile=("driver_pay_per_mile", "mean"), driver_pay_per_minute=("driver_pay_per_minute", "mean"),
        tolls_per_trip=("tolls", "mean"), tip_rate=("tip_rate", "mean"), driver_pay_to_fare_ratio=("driver_pay_to_fare_ratio", "mean"),
    ).reset_index()
    wide = metrics.pivot_table(index=keys[:-1], columns="post_policy", values=["trip_count", "fare_per_mile", "driver_pay_per_minute", "tolls_per_trip"], aggfunc="first")
    wide.columns = [f"{metric}_{'post' if post else 'pre'}" for metric, post in wide.columns]
    result = wide.reset_index().fillna(0)
    result["fare_per_mile_change"] = result["fare_per_mile_post"] - result["fare_per_mile_pre"]
    result["driver_pay_per_minute_change"] = result["driver_pay_per_minute_post"] - result["driver_pay_per_minute_pre"]
    result["demand_change"] = result["trip_count_post"] - result["trip_count_pre"]
    result["subsidy_signal"] = (result["fare_per_mile_change"] > 0) & (result["driver_pay_per_minute_change"] <= 0)
    result = result.sort_values("demand_change", ascending=False)
    save_table(result, "pricing_driver_impact.csv")
    top = result.nlargest(20, "fare_per_mile_change")
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(top["fare_per_mile_change"], top["driver_pay_per_minute_change"], s=np.maximum(top["trip_count_post"], 1) * 3, alpha=0.65, color="#c54b3c")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Passenger price versus driver-pay proxy change by OD route")
    ax.set_xlabel("Fare per mile change")
    ax.set_ylabel("Driver pay per minute change")
    save_plot(fig, "fare_driver_pay_comparison.png")
    logging.info("Wrote pricing and driver analysis for %s OD pairs", len(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
