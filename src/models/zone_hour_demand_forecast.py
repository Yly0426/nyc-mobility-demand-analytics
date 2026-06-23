"""Train report-oriented zone-hour demand forecasting baselines."""

from __future__ import annotations

import argparse
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.analysis.analysis_utils import save_plot, save_table
from src.utils.project import OUTPUTS_DIR, resolve_project_path


def _features(panel: pd.DataFrame) -> pd.DataFrame:
    data = panel.sort_values(["zone_id", "trip_date", "hour"]).copy()
    data["month"] = data["trip_date"].dt.month
    data["lag_1_hour_order_count"] = data.groupby("zone_id")["order_count"].shift(1)
    data["lag_24_hour_order_count"] = data.groupby("zone_id")["order_count"].shift(24).fillna(data["lag_1_hour_order_count"])
    data["lag_7_day_order_count"] = data.groupby("zone_id")["order_count"].shift(168).fillna(data["lag_24_hour_order_count"])
    data["rolling_3_hour_order_count"] = data.groupby("zone_id")["order_count"].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    data["rolling_24_hour_order_count"] = data.groupby("zone_id")["order_count"].transform(lambda x: x.shift(1).rolling(24, min_periods=1).mean())
    return data.dropna(subset=["lag_1_hour_order_count"])


def _fit_xgboost(train_x: pd.DataFrame, train_y: pd.Series):
    try:
        from xgboost import XGBRegressor
    except ImportError:
        return None
    model = XGBRegressor(n_estimators=180, max_depth=7, learning_rate=.06, subsample=.85, colsample_bytree=.9, random_state=42, n_jobs=1)
    model.fit(train_x, train_y)
    return model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/zone_hour_policy_panel.parquet")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = _features(pd.read_parquet(resolve_project_path(args.input)))
    cols = ["zone_id", "hour", "weekday", "is_weekend", "month", "avg_trip_miles", "avg_fare_per_mile", "avg_driver_pay_per_minute", "avg_response_time_min", "lag_1_hour_order_count", "lag_24_hour_order_count", "lag_7_day_order_count", "rolling_3_hour_order_count", "rolling_24_hour_order_count"]
    data[cols] = data[cols].fillna(0)
    cutoff = data["trip_date"].quantile(.8)
    train, test = data[data["trip_date"] <= cutoff], data[data["trip_date"] > cutoff]
    if test.empty:
        raise ValueError("Forecast requires a chronological holdout window")
    models = {"random_forest": RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=42, n_jobs=-1)}
    xgb = _fit_xgboost(train[cols], train["order_count"])
    if xgb is not None:
        models["xgboost"] = xgb
    metrics, predictions = [], []
    for name, model in models.items():
        model.fit(train[cols], train["order_count"])
        pred = np.clip(model.predict(test[cols]), 0, None)
        metrics.append({"model_name": name, "mae": mean_absolute_error(test["order_count"], pred), "rmse": mean_squared_error(test["order_count"], pred) ** .5, "mape": float(np.mean(np.abs((test["order_count"] - pred) / np.maximum(test["order_count"], 1)))), "r2_score": r2_score(test["order_count"], pred), "train_start_date": train["trip_date"].min().date(), "train_end_date": train["trip_date"].max().date(), "test_start_date": test["trip_date"].min().date(), "test_end_date": test["trip_date"].max().date()})
        if name == list(models)[-1]:
            predictions = test[["trip_date", "hour", "zone_name", "order_count"]].copy()
            predictions["predicted_order_count"] = pred
            predictions["prediction_error"] = predictions["order_count"] - pred
            predictions["abs_prediction_error"] = np.abs(predictions["prediction_error"])
            predictions = predictions.rename(columns={"trip_date": "date", "zone_name": "pickup_zone", "order_count": "actual_order_count"})
    metric_frame = pd.DataFrame(metrics)
    save_table(metric_frame, "model_metrics.csv")
    importance = pd.DataFrame({"feature": cols, "importance": getattr(models[list(models)[-1]], "feature_importances_", np.zeros(len(cols))) }).sort_values("importance", ascending=False)
    save_table(importance, "feature_importance.csv")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUTS_DIR / "zone_hour_demand_predictions.csv", index=False)
    daily = predictions.groupby("date")[["actual_order_count", "predicted_order_count"]].sum().reset_index()
    fig, ax = plt.subplots(figsize=(9, 4)); ax.plot(daily["date"], daily["actual_order_count"], label="实际订单", color="#2378b5"); ax.plot(daily["date"], daily["predicted_order_count"], label="预测订单", color="#e07a3f", linestyle="--"); ax.set_title("区域小时需求预测：实际值与预测值"); ax.set_ylabel("订单量"); ax.legend(); save_plot(fig, "demand_forecast_actual_vs_predicted.png")
    fig, ax = plt.subplots(figsize=(8, 4)); top = importance.head(12).sort_values("importance"); ax.barh(top["feature"], top["importance"], color="#2378b5"); ax.set_title("需求预测特征重要性"); save_plot(fig, "feature_importance.png")
    logging.info("Forecast complete with models: %s", ", ".join(models))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
