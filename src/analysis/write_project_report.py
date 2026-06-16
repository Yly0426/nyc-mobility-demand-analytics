from __future__ import annotations

import argparse
import json

import pandas as pd

from src.utils.paths import REPORTS_DIR, TABLES_DIR, WAREHOUSE_DIR, ensure_project_dirs


def fmt_int(value: float | int) -> str:
    return f"{int(value):,}"


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in df.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:,.2f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="fhvhv")
    parser.add_argument("--suffix", default="sample_2")
    args = parser.parse_args()

    ensure_project_dirs()
    hourly = pd.read_csv(WAREHOUSE_DIR / f"hourly_demand_{args.service}_{args.suffix}.csv")
    zone = pd.read_csv(WAREHOUSE_DIR / f"zone_hourly_demand_{args.service}_{args.suffix}.csv")
    od = pd.read_csv(WAREHOUSE_DIR / f"top_od_flows_{args.service}_{args.suffix}.csv")
    invalid = pd.read_csv(WAREHOUSE_DIR / f"invalid_trip_summary_{args.service}_{args.suffix}.csv")
    model_path = REPORTS_DIR / f"demand_baseline_metrics_{args.service}_{args.suffix}.json"
    model_metrics = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else {}

    total_trips = hourly["trip_count"].sum()
    avg_fare = hourly["fare_sum"].sum() / total_trips
    avg_distance = hourly["distance_sum"].sum() / total_trips
    avg_duration = hourly["duration_sum"].sum() / total_trips
    peak_hour = hourly.groupby("pickup_hour")["trip_count"].sum().idxmax()
    peak_weekday = hourly.groupby("pickup_weekday")["trip_count"].sum().idxmax()
    top_borough = zone.groupby("pickup_borough")["trip_count"].sum().sort_values(ascending=False).index[0]

    top_zones = (
        zone.groupby(["pickup_borough", "pickup_zone"], dropna=False)["trip_count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_zones.to_csv(TABLES_DIR / f"executive_top_zones_{args.service}_{args.suffix}.csv", index=False)

    top_od = od.head(10).copy()
    top_od.to_csv(TABLES_DIR / f"executive_top_od_{args.service}_{args.suffix}.csv", index=False)

    invalid_total = invalid["record_count"].sum() if not invalid.empty else 0
    invalid_detail = "\n".join(
        f"- {row.invalid_reason}: {fmt_int(row.record_count)} records"
        for row in invalid.itertuples(index=False)
    )

    report = f"""# NYC Mobility Demand Analytics - Project Summary

## Scope

This report summarizes the `{args.service}_{args.suffix}` run of the NYC TLC mobility analytics pipeline. The validated sample uses the first two months of 2024 High Volume FHV data, covering tens of millions of ride-hailing records.

## Data Quality Findings

The raw data contains realistic operational issues that require cleaning before analysis:

{invalid_detail if invalid_detail else "- No invalid rows were found after applying the current cleaning rules."}

These checks include non-positive duration, non-positive distance, very long trips, missing pickup/dropoff zones, negative fare values, and extreme total amounts.

## Business Metrics

- Valid trips analyzed: {fmt_int(total_trips)}
- Average fare: ${avg_fare:,.2f}
- Average distance: {avg_distance:,.2f} miles
- Average duration: {avg_duration:,.1f} minutes
- Peak pickup hour: {int(peak_hour)}
- Peak pickup weekday index: {int(peak_weekday)} where Monday=0
- Highest-demand pickup borough: {top_borough}

## Top Pickup Zones

{markdown_table(top_zones)}

## Top OD Flows

{markdown_table(top_od)}

## Demand Forecast Baseline

The baseline model predicts zone-hour trip volume using time and pickup-zone features.

- Rows used: {fmt_int(model_metrics.get("rows", 0))}
- MAE: {model_metrics.get("mae", 0):.2f}
- RMSE: {model_metrics.get("rmse", 0):.2f}
- R2: {model_metrics.get("r2", 0):.3f}

## Interpretation

The project shows how a mobility platform can transform raw trip logs into reusable operational indicators. The main value is not only forecasting demand, but also building a data pipeline that exposes dirty records, standardizes multi-service schemas, and creates warehouse-ready metrics for business analysis.
"""

    output = REPORTS_DIR / "project_summary.md"
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
