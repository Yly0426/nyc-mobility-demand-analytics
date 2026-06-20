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
    # Sparse sample panels may not have seven prior observations per zone.
    data["lag_7"] = data.groupby("zone_id")["order_count"].shift(7).fillna(data["lag_1"])
    data["month"] = data["trip_date"].dt.month
    return data.dropna(subset=["lag_1"])


def main() -> int:
    """Fit on pre-policy observations and estimate post-policy demand gaps."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    data = prepare(read_panel(args.input))
    features = ["zone_id", "hour", "weekday", "is_weekend", "month", "lag_1", "lag_7"]
    train = data.loc[~data["post_policy"]]
    test = data.loc[data["post_policy"]]
    if train.empty or test.empty:
        raise ValueError("Counterfactual baseline needs both pre-policy and post-policy observations")
    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(train[features], train["order_count"])
    test = test.copy()
    test["counterfactual_order_count"] = model.predict(test[features]).clip(0)
    test["counterfactual_gap"] = test["order_count"] - test["counterfactual_order_count"]
    output = test[["zone_id", "zone_name", "trip_date", "hour", "order_count", "counterfactual_order_count", "counterfactual_gap"]]
    output.to_csv(OUTPUTS_DIR / "counterfactual_predictions.csv", index=False)
    metrics = {"MAE_pre_policy": float(mean_absolute_error(train["order_count"], model.predict(train[features]))), "RMSE_pre_policy": float(mean_squared_error(train["order_count"], model.predict(train[features])) ** 0.5), "mean_post_policy_counterfactual_gap": float(test["counterfactual_gap"].mean())}
    save_table(__import__("pandas").DataFrame([metrics]), "model_metrics.csv")
    daily = output.groupby("trip_date")[["order_count", "counterfactual_order_count"]].sum().reset_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(daily["trip_date"], daily["order_count"], label="Actual demand", color="#0b6e99")
    ax.plot(daily["trip_date"], daily["counterfactual_order_count"], label="No-policy baseline", color="#bd3c2f", linestyle="--")
    ax.set_title("Actual versus counterfactual post-policy demand")
    ax.legend()
    save_plot(fig, "counterfactual_vs_actual.png")
    logging.info("Counterfactual baseline complete: %s", metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
