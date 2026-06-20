"""Rank zones receiving potential demand displaced by congestion pricing."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import numpy as np

from src.analysis.analysis_utils import read_panel, save_plot, save_table


def main() -> int:
    """Compare pre/post zone demand and rank configured spillover zones."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    panel = read_panel(args.input)
    keys = ["zone_id", "zone_name", "zone_group"]
    pre = panel.loc[~panel["post_policy"]].groupby(keys)["order_count"].sum().rename("pre_order_count")
    post = panel.loc[panel["post_policy"]].groupby(keys)["order_count"].sum().rename("post_order_count")
    result = pre.to_frame().join(post, how="outer").fillna(0).reset_index()
    result["absolute_change"] = result["post_order_count"] - result["pre_order_count"]
    result["relative_change"] = result["absolute_change"] / result["pre_order_count"].replace(0, np.nan)
    result["spillover_score"] = result["relative_change"].fillna(0) * np.log1p(result["post_order_count"])
    result = result.sort_values("spillover_score", ascending=False)
    save_table(result, "spillover_zone_ranking.csv")
    top = result.loc[result["zone_group"].eq("spillover_zones")].head(15)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top["zone_name"], top["spillover_score"], color="#1c8c74")
    ax.invert_yaxis()
    ax.set_title("Potential boundary demand spillover after congestion pricing")
    ax.set_xlabel("Spillover score")
    save_plot(fig, "spillover_heatmap.png")
    logging.info("Ranked %s zones", len(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
