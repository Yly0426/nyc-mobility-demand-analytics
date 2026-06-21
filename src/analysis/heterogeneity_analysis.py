"""Break policy effects down by time, distance, zone group and airport flag."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.analysis_utils import read_panel, save_plot, save_table


def add_segments(data: pd.DataFrame) -> pd.DataFrame:
    """Create business-readable time and distance segments."""
    out = data.copy()
    out["hour_group"] = pd.cut(out["trip_hour"], [-1, 6, 10, 16, 20, 24], labels=["night", "morning_peak", "noon", "evening_peak", "late_evening"])
    out["day_type"] = out["is_weekend"].map({True: "weekend", False: "weekday"})
    out["distance_group"] = pd.cut(out["trip_miles"], [0, 2, 8, float("inf")], labels=["short", "medium", "long"])
    out["airport_flag"] = out["is_airport_trip"].map({True: "airport", False: "non_airport"})
    return out


def main() -> int:
    """Write segmented pre/post demand changes and summary charts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/trip_policy_features.parquet")
    parser.add_argument("--sample", action="store_true", help="Run the same analysis against bounded trip records.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = add_segments(read_panel(args.input))
    segments = ["hour_group", "day_type", "distance_group", "pickup_zone_group", "airport_flag"]
    rows = []
    for segment in segments:
        table = data.groupby([segment, "post_policy"]).size().unstack(fill_value=0)
        for label, values in table.iterrows():
            pre, post = values.get(False, 0), values.get(True, 0)
            rows.append({"dimension": segment, "segment": str(label), "pre_order_count": pre, "post_order_count": post, "absolute_change": post - pre, "relative_change": (post - pre) / pre if pre else None})
    result = pd.DataFrame(rows)
    save_table(result, "heterogeneity_summary.csv")
    hour = result.loc[result["dimension"].eq("hour_group")]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(hour["segment"], hour["relative_change"].fillna(0), color="#8c5ba7")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Demand change by operating time window")
    save_plot(fig, "heterogeneity_by_hour.png")
    zone = result.loc[result["dimension"].eq("pickup_zone_group")]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(zone["segment"], zone["relative_change"].fillna(0), color="#d0842f")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Demand change by policy-zone group")
    save_plot(fig, "heterogeneity_by_zone_group.png")
    logging.info("Wrote %s heterogeneity rows", len(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
