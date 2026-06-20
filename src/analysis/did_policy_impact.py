"""Estimate congestion-pricing effects with a fixed-effects DiD model."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf

from src.analysis.analysis_utils import read_panel, save_json, save_plot, save_table


METRICS = ["log_order_count", "avg_fare_per_mile", "avg_driver_pay_per_minute", "airport_trip_count", "short_trip_count"]


def estimate_did(panel: pd.DataFrame, metric: str) -> dict:
    """Fit a zone, hour and weekday fixed-effects DiD regression."""
    data = panel.loc[panel["zone_group"].isin(["treated_zones", "control_zones"])].dropna(subset=[metric]).copy()
    data["treated_zone"] = data["zone_group"].eq("treated_zones").astype(int)
    data["post_policy"] = data["post_policy"].astype(int)
    fit = smf.ols(f"{metric} ~ treated_zone * post_policy + C(zone_id) + C(hour) + C(weekday)", data=data).fit(cov_type="HC1")
    term = "treated_zone:post_policy"
    interval = fit.conf_int().loc[term]
    coef = float(fit.params[term])
    return {
        "metric_name": metric,
        "coef_treated_post": coef,
        "std_error": float(fit.bse[term]),
        "p_value": float(fit.pvalues[term]),
        "confidence_interval_low": float(interval.iloc[0]),
        "confidence_interval_high": float(interval.iloc[1]),
        "n_observations": int(fit.nobs),
        "business_interpretation": "Policy-period treated-zone change relative to control zones; negative demand coefficients indicate a relative demand contraction." if metric == "log_order_count" else "Policy-period treated-zone price or driver-side metric change relative to control zones.",
    }


def main() -> int:
    """Run DiD for demand, price and driver-side proxy outcomes."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    panel = read_panel(args.input)
    rows = [estimate_did(panel, metric) for metric in METRICS if metric in panel and panel[metric].notna().sum() > 20]
    results = pd.DataFrame(rows)
    save_table(results, "did_results.csv")
    save_json(results.to_dict(orient="records"), "did_results.json")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.errorbar(results["metric_name"], results["coef_treated_post"], yerr=1.96 * results["std_error"], fmt="o", color="#0b6e99")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("DiD estimates: congestion-pricing effect relative to control zones")
    ax.tick_params(axis="x", rotation=25)
    save_plot(fig, "did_summary.png")
    logging.info("Wrote %s DiD estimates", len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
