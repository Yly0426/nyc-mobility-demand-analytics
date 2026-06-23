"""Create weekly event-study estimates around NYC congestion pricing."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.analysis_utils import read_panel, save_plot, save_table
from src.utils.project import CONFIG_DIR, load_yaml


def event_estimates(panel: pd.DataFrame, metric: str, start: pd.Timestamp, lower: int, upper: int) -> pd.DataFrame:
    """Estimate weekly treated-control gaps relative to the week before policy."""
    data = panel.loc[panel["zone_group"].isin(["treated_zones", "control_zones"])].copy()
    data["event_week"] = ((data["trip_date"] - start).dt.days // 7).clip(lower, upper)
    weekly = data.groupby(["event_week", "zone_group"])[metric].agg(["mean", "var", "count"]).reset_index()
    pivot = weekly.pivot(index="event_week", columns="zone_group", values="mean")
    gap = pivot["treated_zones"] - pivot["control_zones"]
    reference = gap.get(-1, gap.iloc[0])
    output = pd.DataFrame({"event_week": gap.index, "metric_name": metric, "estimated_effect": gap.values - reference})
    output["std_error"] = data.groupby("event_week")[metric].sem().reindex(output["event_week"]).fillna(0).to_numpy()
    output["ci_low"] = output["estimated_effect"] - 1.96 * output["std_error"]
    output["ci_high"] = output["estimated_effect"] + 1.96 * output["std_error"]
    return output


def plot_event(data: pd.DataFrame, title: str, name: str) -> None:
    """Render policy-week event estimates with confidence intervals."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(data["event_week"], data["estimated_effect"], marker="o", color="#0b6e99")
    ax.fill_between(data["event_week"], data["ci_low"], data["ci_high"], color="#0b6e99", alpha=0.18)
    ax.axvline(0, color="#bd3c2f", linestyle="--", label="Policy week")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("Weeks relative to congestion-pricing launch")
    ax.legend()
    save_plot(fig, name)


def main() -> int:
    """Generate demand and fare event-study tables and figures."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    parser.add_argument("--config", default="config/policy_zones.yaml")
    parser.add_argument("--sample", action="store_true", help="Run the same analysis against the bounded sample panel.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_yaml(CONFIG_DIR / "policy_zones.yaml") if args.config == "config/policy_zones.yaml" else load_yaml(args.config)
    panel = read_panel(args.input)
    start = pd.Timestamp(cfg["policy"]["start_date"])
    before, after = cfg["policy"]["event_window_weeks_before"], cfg["policy"]["event_window_weeks_after"]
    demand = event_estimates(panel, "log_order_count", start, -before, after)
    fare = event_estimates(panel.dropna(subset=["avg_fare_per_mile"]), "avg_fare_per_mile", start, -before, after)
    driver = event_estimates(panel.dropna(subset=["avg_driver_pay_per_minute"]), "avg_driver_pay_per_minute", start, -before, after)
    results = pd.concat([demand, fare, driver], ignore_index=True)
    save_table(results, "event_study_results.csv")
    plot_event(demand, "Weekly relative demand shift in treated zones", "event_study_order_count.png")
    plot_event(fare, "Weekly relative fare-per-mile shift in treated zones", "event_study_fare_per_mile.png")
    plot_event(driver, "Weekly relative driver-pay-per-minute shift in treated zones", "event_study_driver_pay.png")
    logging.info("Wrote %s weekly event estimates", len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
