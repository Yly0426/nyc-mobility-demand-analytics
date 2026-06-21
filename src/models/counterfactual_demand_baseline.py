"""Train a pre-policy demand baseline for counterfactual operational context."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.analysis.analysis_utils import read_panel, save_plot, save_table
from src.utils.project import OUTPUTS_DIR, ensure_output_dirs


def prepare(panel):
    """Create demand lags and calendar features without using post-policy labels."""
    data = panel.sort_values(["zone_id", "trip_date", "hour"]).copy()
    data["lag_1"] = data.groupby("zone_id")["order_count"].shift(1)
    # Sample panels can be sparse, so each longer lag falls back to a shorter one.
    data["lag_24"] = data.groupby("zone_id")["order_count"].shift(24).fillna(data["lag_1"])
    data["lag_7_day"] = data.groupby("zone_id")["order_count"].shift(168).fillna(data["lag_24"])
    data["month"] = data["trip_date"].dt.month
    return data.dropna(subset=["lag_1"])


def main() -> int:
    """Fit on pre-policy observations and estimate post-policy demand gaps."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    parser.add_argument("--sample", action="store_true", help="Run against the bounded sample panel when supplied.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    data = prepare(read_panel(args.input))
    features = ["zone_id", "hour", "weekday", "is_weekend", "month", "lag_1", "lag_24", "lag_7_day"]
    train = data.loc[~data["post_policy"]]
    test = data.loc[data["post_policy"]]
    if train.empty or test.empty:
        raise ValueError("Counterfactual baseline needs both pre-policy and post-policy observations")
    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(train[features], train["order_count"])
    test = test.copy()
    test["predicted_counterfactual_order_count"] = model.predict(test[features]).clip(0)
    test["actual_order_count"] = test["order_count"]
    # Positive values represent demand missing relative to the no-policy benchmark.
    test["demand_gap"] = test["predicted_counterfactual_order_count"] - test["actual_order_count"]
    test["demand_gap_rate"] = test["demand_gap"] / test["predicted_counterfactual_order_count"].replace(0, np.nan)
    output = test[["zone_id", "zone_name", "trip_date", "hour", "actual_order_count", "predicted_counterfactual_order_count", "demand_gap", "demand_gap_rate"]].rename(columns={"trip_date": "date"})
    output.to_csv(OUTPUTS_DIR / "counterfactual_predictions.csv", index=False)
    metrics = {"MAE_pre_policy": float(mean_absolute_error(train["order_count"], model.predict(train[features]))), "RMSE_pre_policy": float(mean_squared_error(train["order_count"], model.predict(train[features])) ** 0.5), "mean_post_policy_demand_gap": float(test["demand_gap"].mean())}
    save_table(__import__("pandas").DataFrame([metrics]), "model_metrics.csv")
    daily = output.groupby("date")[["actual_order_count", "predicted_counterfactual_order_count"]].sum().reset_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(daily["date"], daily["actual_order_count"], label="Actual demand", color="#0b6e99")
    ax.plot(daily["date"], daily["predicted_counterfactual_order_count"], label="No-policy baseline", color="#bd3c2f", linestyle="--")
    ax.set_title("Actual versus counterfactual post-policy demand")
    ax.legend()
    save_plot(fig, "counterfactual_vs_actual.png")
    logging.info("Counterfactual baseline complete: %s", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
