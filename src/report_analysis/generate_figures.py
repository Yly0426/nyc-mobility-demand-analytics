"""Generate the core report figures from the Hive-compatible metric exports."""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.analysis_utils import save_plot
from src.utils.project import TABLES_DIR


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--sample", action="store_true"); parser.parse_args()
    time = pd.read_csv(TABLES_DIR / "time_demand_metrics.csv", parse_dates=["date"])
    zone = pd.read_csv(TABLES_DIR / "top_pickup_zones.csv")
    od = pd.read_csv(TABLES_DIR / "top_od_routes.csv")
    price = pd.read_csv(TABLES_DIR / "price_driver_metrics.csv")
    response = pd.read_csv(TABLES_DIR / "response_metrics.csv")

    daily = time.groupby("date")["order_count"].sum().reset_index(); fig, ax = plt.subplots(figsize=(9, 4)); ax.plot(daily["date"], daily["order_count"], color="#2378b5"); ax.set_title("每日订单趋势（有界样本）"); ax.set_ylabel("订单量"); save_plot(fig, "daily_order_trend.png")
    hourly = time.groupby("hour")["order_count"].sum(); fig, ax = plt.subplots(figsize=(8, 4)); ax.bar(hourly.index, hourly.values, color="#2378b5"); ax.set_title("小时订单分布"); ax.set_xlabel("小时"); ax.set_ylabel("订单量"); save_plot(fig, "hourly_order_pattern.png")
    weekday = time.groupby("weekday")["order_count"].sum(); fig, ax = plt.subplots(figsize=(8, 4)); ax.bar(["周一","周二","周三","周四","周五","周六","周日"], weekday.reindex(range(7), fill_value=0), color="#5c9e6f"); ax.set_title("星期订单分布"); ax.set_ylabel("订单量"); save_plot(fig, "weekday_order_pattern.png")
    plot_zone = zone.head(15).sort_values("pickup_order_count"); fig, ax = plt.subplots(figsize=(9, 5)); ax.barh(plot_zone["pickup_zone"], plot_zone["pickup_order_count"], color="#2378b5"); ax.set_title("订单量最高的上车区域"); ax.set_xlabel("订单量"); save_plot(fig, "top_pickup_zones.png")
    plot_od = od.head(15).copy(); plot_od["route"] = plot_od["pickup_zone"] + " → " + plot_od["dropoff_zone"]; plot_od = plot_od.sort_values("order_count"); fig, ax = plt.subplots(figsize=(10, 5)); ax.barh(plot_od["route"], plot_od["order_count"], color="#5c9e6f"); ax.set_title("高频 OD 路线"); ax.set_xlabel("订单量"); save_plot(fig, "top_od_routes.png")
    dist = price.groupby("trip_distance_group", observed=True)["avg_fare_per_mile"].mean(); fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(dist.index.astype(str), dist.values, color="#e07a3f"); ax.set_title("不同距离段的每英里基础票价"); ax.set_ylabel("美元/英里"); save_plot(fig, "fare_per_mile_distribution.png")
    driver = price.groupby("hour_group", observed=True)["avg_driver_pay_per_minute"].mean(); fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(driver.index.astype(str), driver.values, color="#815ac0"); ax.set_title("不同时段的司机每分钟收益"); ax.set_ylabel("美元/分钟"); save_plot(fig, "driver_pay_per_minute_distribution.png")
    resp = response.groupby("hour")["avg_response_time_min"].mean(); fig, ax = plt.subplots(figsize=(8, 4)); ax.plot(resp.index, resp.values, marker="o", color="#bd3c2f"); ax.set_title("小时接驾响应时长代理"); ax.set_xlabel("小时"); ax.set_ylabel("分钟"); save_plot(fig, "response_time_by_hour.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
