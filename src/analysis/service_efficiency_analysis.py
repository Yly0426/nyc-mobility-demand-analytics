"""Analyze request-to-arrival time as a public-data service-efficiency proxy."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.analysis_utils import read_panel, save_plot, save_table


LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Compare pre/post response proxies by policy zone group."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    parser.add_argument("--sample", action="store_true", help="Run against the bounded sample panel.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    panel = read_panel(args.input)
    required = {"avg_response_time_min", "response_time_p90", "slow_response_rate", "valid_response_count"}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"Zone-hour panel lacks service-efficiency fields: {sorted(missing)}")

    grouped = panel.groupby(["zone_group", "post_policy"], as_index=False).agg(
        average_response_time_min=("avg_response_time_min", "mean"),
        response_time_p90=("response_time_p90", "mean"),
        slow_response_rate=("slow_response_rate", "mean"),
        valid_response_count=("valid_response_count", "sum"),
        order_count=("order_count", "sum"),
    )
    wide = grouped.pivot(index="zone_group", columns="post_policy", values=["average_response_time_min", "response_time_p90", "slow_response_rate", "valid_response_count", "order_count"])
    wide.columns = [f"{metric}_{'post' if period else 'pre'}" for metric, period in wide.columns]
    result = wide.reset_index().fillna(0)
    result["response_time_p90_change"] = result["response_time_p90_post"] - result["response_time_p90_pre"]
    result["slow_response_rate_change"] = result["slow_response_rate_post"] - result["slow_response_rate_pre"]
    result["response_coverage_rate"] = result["valid_response_count_post"] / result["order_count_post"].replace(0, pd.NA)
    save_table(result, "response_time_analysis.csv")

    chart = result.melt(id_vars="zone_group", value_vars=["response_time_p90_pre", "response_time_p90_post"], var_name="period", value_name="response_time_p90")
    chart["period"] = chart["period"].map({"response_time_p90_pre": "政策前", "response_time_p90_post": "政策后"})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for period, frame in chart.groupby("period"):
        ax.bar(frame["zone_group"], frame["response_time_p90"], label=period, alpha=0.82)
    ax.set_title("Request-to-arrival P90 proxy by policy zone group")
    ax.set_ylabel("Minutes")
    ax.legend()
    save_plot(fig, "response_time_p90_change.png")
    LOGGER.info("Wrote service-efficiency analysis for %s zone groups", len(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
