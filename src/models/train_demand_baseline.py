from __future__ import annotations

import argparse
import json

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.utils.paths import REPORTS_DIR, WAREHOUSE_DIR, ensure_project_dirs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="fhvhv")
    parser.add_argument("--suffix", default="sample_2")
    args = parser.parse_args()

    ensure_project_dirs()
    path = WAREHOUSE_DIR / f"zone_hourly_demand_{args.service}_{args.suffix}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Run build_metrics first: {path}")

    df = pd.read_csv(path)
    df["pickup_date"] = pd.to_datetime(df["pickup_date"], errors="coerce")
    df = df.dropna(subset=["pickup_date", "pickup_hour", "pickup_location_id", "trip_count"])
    df["weekday"] = df["pickup_date"].dt.dayofweek
    df["day"] = df["pickup_date"].dt.day
    df["is_weekend"] = df["weekday"].isin([5, 6]).astype(int)

    features = ["pickup_hour", "weekday", "day", "is_weekend", "pickup_location_id", "pickup_borough"]
    target = "trip_count"
    model_df = df[features + [target]].dropna()
    train, test = train_test_split(model_df, test_size=0.2, random_state=42)

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["pickup_borough"]),
        ],
        remainder="passthrough",
    )
    model = Pipeline(
        steps=[
            ("features", preprocessor),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=120,
                    max_depth=14,
                    min_samples_leaf=3,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(train[features], train[target])
    pred = model.predict(test[features])
    metrics = {
        "service": args.service,
        "suffix": args.suffix,
        "rows": int(len(model_df)),
        "mae": float(mean_absolute_error(test[target], pred)),
        "rmse": float(mean_squared_error(test[target], pred) ** 0.5),
        "r2": float(r2_score(test[target], pred)),
    }
    output_path = REPORTS_DIR / f"demand_baseline_metrics_{args.service}_{args.suffix}.json"
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

