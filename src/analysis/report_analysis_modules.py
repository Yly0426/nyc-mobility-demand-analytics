"""Reusable report-oriented analyses for the congestion-pricing project."""

from __future__ import annotations

import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.analysis_utils import save_plot, save_table


LOGGER = logging.getLogger(__name__)


def pct_change(post: pd.Series, pre: pd.Series) -> pd.Series:
    """Return guarded percentage movement."""
    return (post - pre) / pre.replace(0, np.nan)


def time_window(hours: pd.Series) -> pd.Series:
    """Map hours to operational windows used in the report."""
    return pd.cut(hours, [-1, 5, 10, 14, 20, 24], labels=["凌晨", "早高峰", "午间", "晚高峰", "夜间"], include_lowest=True).astype(str)


def pre_post_wide(data: pd.DataFrame, keys: list[str], aggregations: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Aggregate pre/post periods and return a flat comparison table."""
    grouped = data.groupby(keys + ["post_policy"], dropna=False).agg(**aggregations).reset_index()
    wide = grouped.pivot(index=keys, columns="post_policy")
    wide.columns = [f"{name}_{'post' if period else 'pre'}" for name, period in wide.columns]
    return wide.reset_index().fillna(0)


def demand_shift(data: pd.DataFrame) -> None:
    """Write zone-group demand results and two report figures."""
    result = pre_post_wide(data, ["pickup_zone_group"], {"order_count": ("service_type", "size")}).rename(columns={"pickup_zone_group": "zone_group"})
    result["absolute_change"] = result["order_count_post"] - result["order_count_pre"]
    result["change_rate"] = pct_change(result["order_count_post"], result["order_count_pre"])
    result["business_interpretation"] = np.where(result["zone_group"].eq("spillover_zones"), "用于识别可能承接核心区转移需求的区域组。", "用于比较政策前后不同区域组的订单变化。")
    save_table(result, "demand_shift_summary.csv")
    daily = data.groupby(["trip_date", "post_policy"], as_index=False).size().rename(columns={"size": "order_count"})
    fig, ax = plt.subplots(figsize=(9, 4))
    for label, frame in daily.groupby("post_policy"):
        ax.plot(frame["trip_date"], frame["order_count"], label="政策后" if label else "政策前")
    ax.set_title("Daily order trend")
    ax.set_ylabel("Orders")
    ax.legend()
    save_plot(fig, "daily_order_trend.png")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(result["zone_group"], result["change_rate"].fillna(0))
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Demand change by policy zone group")
    ax.tick_params(axis="x", rotation=20)
    save_plot(fig, "zone_group_demand_change.png")


def temporal_pattern(data: pd.DataFrame) -> None:
    """Write hourly and operating-window demand patterns."""
    hourly = pre_post_wide(data, ["trip_hour", "is_weekend"], {"order_count": ("service_type", "size")}).rename(columns={"trip_hour": "hour"})
    hourly["change_rate"] = pct_change(hourly["order_count_post"], hourly["order_count_pre"])
    save_table(hourly, "hourly_demand_pattern.csv")
    frame = data.copy()
    frame["time_window"] = time_window(frame["trip_hour"])
    summary = pre_post_wide(frame, ["time_window", "is_weekend"], {"order_count": ("service_type", "size")})
    summary["change_rate"] = pct_change(summary["order_count_post"], summary["order_count_pre"])
    save_table(summary, "time_window_summary.csv")
    chart = hourly.groupby("hour", as_index=False)[["order_count_pre", "order_count_post"]].sum()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(chart["hour"], chart["order_count_pre"], label="政策前")
    ax.plot(chart["hour"], chart["order_count_post"], label="政策后")
    ax.set_title("Hourly demand pattern")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Orders")
    ax.legend()
    save_plot(fig, "hourly_demand_pattern.png")


def od_flow(data: pd.DataFrame) -> None:
    """Write OD pre/post changes, route types and a top-route figure."""
    keys = ["pickup_zone_name", "dropoff_zone_name", "is_airport_trip", "is_cross_treated_trip"]
    result = pre_post_wide(data, keys, {"orders": ("service_type", "size"), "fare_per_mile": ("fare_per_mile", "mean"), "driver_pay_per_minute": ("driver_pay_per_minute", "mean")})
    result["absolute_change"] = result["orders_post"] - result["orders_pre"]
    result["change_rate"] = pct_change(result["orders_post"], result["orders_pre"])
    result["avg_fare_per_mile_change"] = result["fare_per_mile_post"] - result["fare_per_mile_pre"]
    result["avg_driver_pay_per_minute_change"] = result["driver_pay_per_minute_post"] - result["driver_pay_per_minute_pre"]
    result["route_type"] = np.select([result["is_airport_trip"], result["is_cross_treated_trip"], result["avg_driver_pay_per_minute_change"].lt(0)], ["airport_od", "cross_treated_od", "driver_pressure_od"], default="high_value_od")
    result["business_interpretation"] = "OD 路线用于判断需求变化是乘客侧价格问题还是司机收益压力问题。"
    result = result.sort_values("orders_post", ascending=False)
    save_table(result, "od_flow_change.csv")
    save_table(result.head(50), "top_od_pairs.csv")
    chart = result.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(chart["pickup_zone_name"] + " → " + chart["dropoff_zone_name"], chart["absolute_change"])
    ax.set_title("Top OD flow changes")
    ax.set_xlabel("Post minus pre orders")
    save_plot(fig, "top_od_flow_change.png")


def pricing_pressure(data: pd.DataFrame) -> None:
    """Write passenger price-pressure segments and two figures."""
    frame = data.copy()
    frame["distance_segment"] = pd.cut(frame["trip_miles"], [0, 2, 8, np.inf], labels=["短途", "中途", "长途"])
    result = pre_post_wide(frame, ["distance_segment"], {"fare_per_mile": ("fare_per_mile", "mean"), "policy_fee_burden": ("policy_fee_burden_rate", "mean"), "orders": ("service_type", "size")})
    result["fare_per_mile_change_rate"] = pct_change(result["fare_per_mile_post"], result["fare_per_mile_pre"])
    result["policy_fee_burden_change_rate"] = pct_change(result["policy_fee_burden_post"], result["policy_fee_burden_pre"])
    result["passenger_discount_signal"] = (result["fare_per_mile_change_rate"] > 0) & (result["orders_post"] < result["orders_pre"])
    result["business_interpretation"] = "单位里程价格上升且订单下降的分组，是乘客优惠的候选对象。"
    save_table(result, "pricing_pressure_summary.csv")
    for column, name, title in [("fare_per_mile_change_rate", "fare_per_mile_change.png", "每英里票价政策后相对变化"), ("policy_fee_burden_change_rate", "policy_fee_burden_change.png", "政策费用负担政策后相对变化")]:
        fig, ax = plt.subplots(figsize=(7, 4))
        values = result[column].fillna(0) * 100
        colors = np.where(values >= 0, "#d55e00", "#0072b2")
        bars = ax.bar(result["distance_segment"].astype(str), values, color=colors)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(title)
        ax.set_ylabel("变化率（%）")
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + (0.15 if value >= 0 else -0.45), f"{value:.1f}%", ha="center", va="bottom" if value >= 0 else "top")
        save_plot(fig, name)


def driver_pressure(data: pd.DataFrame) -> None:
    """Write OD-level driver pressure signals and supporting charts."""
    keys = ["pickup_zone_name", "dropoff_zone_name", "is_airport_trip"]
    result = pre_post_wide(data, keys, {"orders": ("service_type", "size"), "driver_pay_per_minute": ("driver_pay_per_minute", "mean"), "tolls": ("tolls", "mean"), "pay_to_fare": ("driver_pay_to_fare_ratio", "mean")})
    result["driver_pay_per_minute_change_rate"] = pct_change(result["driver_pay_per_minute_post"], result["driver_pay_per_minute_pre"])
    result["tolls_change_rate"] = pct_change(result["tolls_post"], result["tolls_pre"])
    result["driver_pay_to_fare_ratio_change"] = result["pay_to_fare_post"] - result["pay_to_fare_pre"]
    toll_score = (result["tolls_change_rate"].fillna(0) - result["tolls_change_rate"].fillna(0).min()) / max(result["tolls_change_rate"].fillna(0).max() - result["tolls_change_rate"].fillna(0).min(), 1e-9)
    pay_score = (result["driver_pay_per_minute_change_rate"].fillna(0).max() - result["driver_pay_per_minute_change_rate"].fillna(0)) / max(result["driver_pay_per_minute_change_rate"].fillna(0).max() - result["driver_pay_per_minute_change_rate"].fillna(0).min(), 1e-9)
    result["driver_pressure_score"] = (toll_score + pay_score) / 2
    result["driver_incentive_signal"] = (result["driver_pressure_score"] >= result["driver_pressure_score"].quantile(0.9)) & (result["orders_post"] >= 10)
    result["business_interpretation"] = "通行费压力上升且司机单位时间收益承压的高订单路线，优先进入司机激励试点。"
    result = result.sort_values("driver_pressure_score", ascending=False)
    save_table(result, "driver_pressure_summary.csv")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(result["driver_pay_per_minute_change_rate"].replace([np.inf, -np.inf], np.nan).dropna(), bins=30)
    ax.set_title("Driver pay per minute change")
    save_plot(fig, "driver_pay_per_minute_change.png")
    chart = result.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(chart["pickup_zone_name"] + " → " + chart["dropoff_zone_name"], chart["driver_pressure_score"])
    ax.set_title("Top driver pressure routes")
    save_plot(fig, "driver_pressure_score_top_routes.png")


def airport_routes(data: pd.DataFrame) -> None:
    """Write airport-specific route analysis using observable FHV metrics."""
    airport = data.loc[data["is_airport_trip"]].copy()
    airport["airport_name"] = np.select([airport["pickup_zone_name"].str.contains("JFK", na=False) | airport["dropoff_zone_name"].str.contains("JFK", na=False), airport["pickup_zone_name"].str.contains("LaGuardia", na=False) | airport["dropoff_zone_name"].str.contains("LaGuardia", na=False), airport["pickup_zone_name"].str.contains("Newark", na=False) | airport["dropoff_zone_name"].str.contains("Newark", na=False)], ["JFK Airport", "LaGuardia Airport", "Newark Airport"], default="Other airport")
    airport["target_area"] = np.where(airport["pickup_zone_group"].eq("treated_zones") | airport["dropoff_zone_group"].eq("treated_zones"), "收费核心区相关", "其他区域")
    result = pre_post_wide(airport, ["airport_name", "target_area"], {"orders": ("service_type", "size"), "fare_per_mile": ("fare_per_mile", "mean"), "driver_pay_per_minute": ("driver_pay_per_minute", "mean"), "response_time_p90": ("response_time_min", lambda x: x.quantile(0.9))})
    for metric in ("orders", "fare_per_mile", "driver_pay_per_minute", "response_time_p90"):
        result[f"{metric}_change_rate"] = pct_change(result[f"{metric}_post"], result[f"{metric}_pre"])
    result["recommended_strategy"] = np.where((result["driver_pay_per_minute_change_rate"] < 0) | (result["response_time_p90_change_rate"] > 0), "优先派单或司机激励试点", "持续监控")
    result["business_interpretation"] = "机场路线客单价高，应同时观察需求、司机收益和响应效率。"
    save_table(result, "airport_route_analysis.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(result["airport_name"] + "\n" + result["target_area"], result["orders_change_rate"].fillna(0))
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Airport route demand change")
    ax.tick_params(axis="x", rotation=20)
    save_plot(fig, "airport_route_change.png")


def response_time(data: pd.DataFrame) -> None:
    """Write request-to-arrival proxy changes by zone group and time window."""
    frame = data.loc[data["response_time_min"].notna()].copy()
    frame["time_window"] = time_window(frame["trip_hour"])
    result = pre_post_wide(frame, ["pickup_zone_group", "time_window"], {"response_time_p50": ("response_time_min", "median"), "response_time_p90": ("response_time_min", lambda x: x.quantile(0.9)), "slow_response_rate": ("slow_response_flag", "mean"), "orders": ("service_type", "size")}).rename(columns={"pickup_zone_group": "zone_group"})
    result["slow_response_rate_change"] = result["slow_response_rate_post"] - result["slow_response_rate_pre"]
    result["supply_reallocation_signal"] = (result["response_time_p90_post"] > result["response_time_p90_pre"]) & result["zone_group"].eq("spillover_zones")
    result["business_interpretation"] = "外溢区订单承接且 P90 响应时长变慢，说明司机供给可能未同步迁移。"
    save_table(result, "response_time_analysis.csv")
    zone_labels = {"control_zones": "对照区", "other": "其他区域", "spillover_zones": "外溢区", "treated_zones": "收费核心区"}
    chart = result.groupby("zone_group", as_index=False)[["response_time_p90_pre", "response_time_p90_post"]].mean()
    chart["zone_label"] = chart["zone_group"].map(zone_labels).fillna(chart["zone_group"])
    fig, ax = plt.subplots(figsize=(8, 4))
    positions = np.arange(len(chart))
    width = 0.36
    ax.bar(positions - width / 2, chart["response_time_p90_pre"], width=width, label="政策前", color="#0072b2")
    ax.bar(positions + width / 2, chart["response_time_p90_post"], width=width, label="政策后", color="#d55e00")
    ax.set_xticks(positions, chart["zone_label"])
    ax.set_title("各区域组 P90 接驾响应时长代理")
    ax.set_ylabel("分钟")
    ax.legend()
    save_plot(fig, "response_time_p90_change.png")
