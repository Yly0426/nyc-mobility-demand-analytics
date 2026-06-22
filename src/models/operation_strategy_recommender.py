"""Generate evidence-backed platform operations recommendations.

This module is intentionally a rules-based recommender rather than a black-box
optimizer. It turns the policy-analysis outputs into small, measurable operating
trials and keeps the evidence for every recommendation in the output.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.analysis_utils import read_panel, save_json, save_table
from src.utils.project import OUTPUTS_DIR, ensure_output_dirs, resolve_project_path


LOGGER = logging.getLogger(__name__)


def read_csv_or_empty(path: str) -> pd.DataFrame:
    """Read an optional CSV input and warn instead of breaking the workflow."""
    resolved = resolve_project_path(path)
    if not resolved.exists():
        LOGGER.warning("Optional input is unavailable: %s", resolved)
        return pd.DataFrame()
    return pd.read_csv(resolved)


def minmax(series: pd.Series) -> pd.Series:
    """Return a stable 0-1 score when a metric has little or no variation."""
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    low, high = values.min(), values.max()
    if np.isclose(low, high):
        return pd.Series(0.5 if high else 0.0, index=values.index)
    return (values - low) / (high - low)


def safe_rate(post: pd.Series, pre: pd.Series) -> pd.Series:
    """Calculate percentage movement while preserving missing baselines as zero."""
    return (post - pre) / pre.replace(0, np.nan)


def priority(score: float) -> str:
    """Translate the combined action score into a business priority."""
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def confidence(sample_size: float, signals: int) -> str:
    """Grade evidence strength without claiming causal certainty for every route."""
    if sample_size >= 200 and signals >= 3:
        return "High"
    if sample_size >= 50 and signals >= 2:
        return "Medium"
    return "Low"


def hour_window(hour: int | float | None) -> str:
    """Convert an hour to a readable four-hour operating window."""
    if pd.isna(hour):
        return "按小时监控"
    start = int(hour)
    return f"{start:02d}:00-{(start + 4) % 24:02d}:00"


def zone_context(panel: pd.DataFrame, predictions: pd.DataFrame, spillover: pd.DataFrame) -> pd.DataFrame:
    """Aggregate zone demand, price, driver pressure and counterfactual context."""
    post = panel.loc[panel["post_policy"]].copy()
    pre = panel.loc[~panel["post_policy"]].copy()
    keys = ["zone_id", "zone_name", "zone_group"]
    measures = ["order_count", "avg_fare_per_mile", "avg_driver_pay_per_minute", "avg_tolls", "response_time_p90", "slow_response_rate"]
    post_summary = post.groupby(keys, as_index=False)[measures].mean().rename(columns={value: f"{value}_post" for value in measures})
    pre_summary = pre.groupby(keys, as_index=False)[measures].mean().rename(columns={value: f"{value}_pre" for value in measures})
    context = post_summary.merge(pre_summary, on=keys, how="outer").fillna(0)
    peak = post.groupby(keys + ["hour"], as_index=False)["order_count"].sum().sort_values("order_count", ascending=False).drop_duplicates(keys)
    context = context.merge(peak[keys + ["hour"]], on=keys, how="left")

    if not predictions.empty:
        prediction = predictions.copy()
        prediction["actual_order_count"] = pd.to_numeric(prediction.get("actual_order_count", prediction.get("order_count", 0)), errors="coerce").fillna(0)
        prediction["predicted_counterfactual_order_count"] = pd.to_numeric(prediction.get("predicted_counterfactual_order_count", prediction.get("counterfactual_order_count", 0)), errors="coerce").fillna(0)
        prediction["demand_gap"] = prediction["predicted_counterfactual_order_count"] - prediction["actual_order_count"]
        prediction["demand_gap_rate"] = prediction["demand_gap"] / prediction["predicted_counterfactual_order_count"].replace(0, np.nan)
        gap = prediction.groupby(["zone_id", "zone_name"], as_index=False)[["actual_order_count", "predicted_counterfactual_order_count", "demand_gap", "demand_gap_rate"]].mean()
        context = context.merge(gap, on=["zone_id", "zone_name"], how="left")
    else:
        LOGGER.warning("Counterfactual data missing; demand-gap scores will default to zero.")
        context[["actual_order_count", "predicted_counterfactual_order_count", "demand_gap", "demand_gap_rate"]] = 0.0

    if not spillover.empty:
        context = context.merge(spillover[["zone_id", "spillover_score"]], on="zone_id", how="left")
    else:
        context["spillover_score"] = 0.0
    context["spillover_score"] = context["spillover_score"].fillna(0.0)
    context["fare_per_mile_change_rate"] = safe_rate(context["avg_fare_per_mile_post"], context["avg_fare_per_mile_pre"]).fillna(0)
    context["driver_pay_per_minute_change_rate"] = safe_rate(context["avg_driver_pay_per_minute_post"], context["avg_driver_pay_per_minute_pre"]).fillna(0)
    context["tolls_change_rate"] = safe_rate(context["avg_tolls_post"], context["avg_tolls_pre"]).fillna(0)
    context["response_time_p90_change"] = (context["response_time_p90_post"] - context["response_time_p90_pre"]).fillna(0)
    context["slow_response_rate_change"] = (context["slow_response_rate_post"] - context["slow_response_rate_pre"]).fillna(0)
    context["demand_gap_score"] = minmax(context["demand_gap_rate"].clip(lower=0))
    context["driver_pressure_score"] = (minmax(context["tolls_change_rate"]) - minmax(context["driver_pay_per_minute_change_rate"])).clip(0, 1)
    context["passenger_price_pressure_score"] = minmax(context["fare_per_mile_change_rate"].clip(lower=0))
    context["spillover_score_normalized"] = minmax(context["spillover_score"].clip(lower=0))
    context["final_action_score"] = (
        0.35 * context["demand_gap_score"]
        + 0.25 * context["driver_pressure_score"]
        + 0.20 * context["passenger_price_pressure_score"]
        + 0.20 * context["spillover_score_normalized"]
    )
    return context.fillna(0)


def route_context(pricing: pd.DataFrame) -> pd.DataFrame:
    """Score route-level economic pressure using pre/post OD evidence."""
    if pricing.empty:
        return pd.DataFrame()
    routes = pricing.copy()
    for metric in ("fare_per_mile", "driver_pay_per_minute", "tolls_per_trip"):
        routes[f"{metric}_change_rate"] = safe_rate(routes.get(f"{metric}_post", pd.Series(0, index=routes.index)), routes.get(f"{metric}_pre", pd.Series(0, index=routes.index))).fillna(0)
    routes["demand_gap_rate"] = (-safe_rate(routes.get("trip_count_post", pd.Series(0, index=routes.index)), routes.get("trip_count_pre", pd.Series(0, index=routes.index)))).clip(lower=0).fillna(0)
    routes["demand_gap_score"] = minmax(routes["demand_gap_rate"])
    routes["driver_pressure_score"] = (minmax(routes["tolls_per_trip_change_rate"]) - minmax(routes["driver_pay_per_minute_change_rate"])).clip(0, 1)
    routes["passenger_price_pressure_score"] = minmax(routes["fare_per_mile_change_rate"].clip(lower=0))
    routes["spillover_score"] = minmax(routes.get("demand_change", pd.Series(0, index=routes.index)).clip(lower=0))
    routes["final_action_score"] = (
        0.35 * routes["demand_gap_score"]
        + 0.25 * routes["driver_pressure_score"]
        + 0.20 * routes["passenger_price_pressure_score"]
        + 0.20 * routes["spillover_score"]
    )
    return routes.fillna(0)


def card(strategy_type: str, index: int, *, zone: str | None, zone_group: str | None, od: str | None, window: str, problem: str, evidence: dict, action: str, impact: str, score: float, sample_size: float, signals: int) -> dict:
    """Create one dashboard-safe strategy card with a consistent evidence contract."""
    return {
        "strategy_id": f"STRAT_{index:04d}",
        "strategy_type": strategy_type,
        "target_zone": zone or "",
        "target_zone_group": zone_group or "",
        "target_od_pair": od or "",
        "target_time_window": window,
        "problem_detected": problem,
        "evidence_metric": evidence,
        "recommended_action": action,
        "expected_business_impact": impact,
        "final_action_score": round(float(score), 3),
        "priority": priority(float(score)),
        "confidence_level": confidence(float(sample_size), signals),
        "created_at": datetime.now(UTC).isoformat(),
    }


def generate_recommendations(zones: pd.DataFrame, routes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Produce supply, driver incentive, passenger discount and card outputs."""
    supply = zones.loc[(zones["zone_group"] == "spillover_zones") & (zones["spillover_score"] > 0)].nlargest(8, "final_action_score").copy()
    if supply.empty:
        LOGGER.warning("No configured spillover zone met the rule; using the strongest available zone as a low-confidence fallback.")
        supply = zones.nlargest(3, "spillover_score").copy()
    supply["recommended_action"] = "在目标时段前预部署司机，并按实时请求量动态调整区域推荐权重。"
    supply["target_time_window"] = supply["hour"].map(hour_window)
    supply["expected_business_impact"] = "缩短边界区接驾时间，减少核心区无效等待。"

    high_value = routes.loc[(routes["trip_count_post"] > 0) & ((routes["is_airport_trip"].astype(bool)) | (routes["trip_count_post"] >= routes["trip_count_post"].quantile(0.75)))].copy() if not routes.empty else pd.DataFrame()
    incentives = high_value.loc[high_value["driver_pressure_score"] > 0].nlargest(12, "final_action_score").copy()
    if incentives.empty and not high_value.empty:
        LOGGER.warning("No route matched the full driver-pressure rule; returning the strongest high-value routes for review.")
        incentives = high_value.nlargest(6, "final_action_score").copy()
    if not incentives.empty:
        incentives["target_od_pair"] = incentives["pickup_zone_name"] + " -> " + incentives["dropoff_zone_name"]
        incentives["recommended_action"] = "对该路线试行司机侧定向激励，并以接单率和取消率作为扩量门槛。"
        incentives["expected_business_impact"] = "稳定高价值路线供给，降低司机因通行成本和时间成本带来的拒单风险。"

    discounts = zones.loc[(zones["demand_gap_rate"] > 0) & (zones["fare_per_mile_change_rate"] > 0)].nlargest(8, "final_action_score").copy()
    if discounts.empty:
        LOGGER.warning("No zone matched the full passenger-price rule; returning largest modeled gaps for review.")
        discounts = zones.loc[zones["demand_gap"] > 0].nlargest(5, "final_action_score").copy()
    discounts["recommended_action"] = "在目标区域和时段测试乘客侧价格减免，并设置预算上限与对照组。"
    discounts["target_time_window"] = discounts["hour"].map(hour_window)
    discounts["expected_business_impact"] = "验证价格干预能否恢复需求，而不在司机收益已受压的路线重复补贴。"

    cards: list[dict] = []
    sequence = 1
    for _, row in supply.head(3).iterrows():
        cards.append(card("driver_supply_reallocation", sequence, zone=row.zone_name, zone_group=row.zone_group, od=None, window=row.target_time_window, problem="边界区域的外溢评分和政策后需求表明，该区域可能承接了核心区转移需求；响应时长代理用于判断供给是否跟上。", evidence={"spillover_score": round(row.spillover_score, 3), "demand_gap_rate": round(row.demand_gap_rate, 3), "post_policy_average_orders": round(row.order_count_post, 2), "response_time_p90_change_min": round(row.response_time_p90_change, 2), "slow_response_rate_change": round(row.slow_response_rate_change, 3)}, action=row.recommended_action, impact=row.expected_business_impact, score=row.final_action_score, sample_size=row.order_count_post, signals=3)); sequence += 1
    for _, row in incentives.loc[~incentives["is_airport_trip"].astype(bool)].head(2).iterrows() if not incentives.empty else []:
        cards.append(card("route_level_driver_incentive", sequence, zone=None, zone_group=None, od=row.target_od_pair, window="晚高峰优先", problem="该高价值路线的通行成本压力高于司机单位时间收入变化，需要先验证供给侧激励。", evidence={"post_policy_order_count": int(row.trip_count_post), "tolls_change_rate": round(row.tolls_per_trip_change_rate, 3), "driver_pay_per_minute_change_rate": round(row.driver_pay_per_minute_change_rate, 3), "fare_per_mile_change_rate": round(row.fare_per_mile_change_rate, 3)}, action=row.recommended_action, impact=row.expected_business_impact, score=row.final_action_score, sample_size=row.trip_count_post, signals=3)); sequence += 1
    for _, row in incentives.loc[incentives["is_airport_trip"].astype(bool)].head(2).iterrows() if not incentives.empty else []:
        cards.append(card("airport_route_strategy", sequence, zone=None, zone_group=None, od=row.target_od_pair, window="航班到达高峰", problem="机场路线仍有订单量，但通行成本与司机单位时间收益的组合需要专项运营，而非通用优惠。", evidence={"post_policy_order_count": int(row.trip_count_post), "tolls_change_rate": round(row.tolls_per_trip_change_rate, 3), "driver_pay_per_minute_change_rate": round(row.driver_pay_per_minute_change_rate, 3)}, action="为机场至核心区路线设置优先派单和司机激励试点。", impact="降低机场高价值路线的供给波动并稳定服务可得性。", score=row.final_action_score, sample_size=row.trip_count_post, signals=3)); sequence += 1
    for _, row in discounts.head(2).iterrows():
        cards.append(card("passenger_discount", sequence, zone=row.zone_name, zone_group=row.zone_group, od=None, window=row.target_time_window, problem="该区域实际需求低于无政策基线，同时乘客单位里程价格上升。", evidence={"demand_gap_rate": round(row.demand_gap_rate, 3), "fare_per_mile_change_rate": round(row.fare_per_mile_change_rate, 3), "driver_pay_per_minute_change_rate": round(row.driver_pay_per_minute_change_rate, 3)}, action=row.recommended_action, impact=row.expected_business_impact, score=row.final_action_score, sample_size=row.actual_order_count, signals=3)); sequence += 1
    for _, row in supply.head(2).iterrows():
        cards.append(card("boundary_zone_strategy", sequence, zone=row.zone_name, zone_group=row.zone_group, od=None, window=row.target_time_window, problem="收费区边界附近出现可能的需求承接，应将其作为新的调度节点而不是沿用旧热区。", evidence={"spillover_score": round(row.spillover_score, 3), "post_policy_average_orders": round(row.order_count_post, 2), "response_time_p90_change_min": round(row.response_time_p90_change, 2)}, action="将边界区加入高峰调度热区，并按小时复核供给响应。", impact="在需求转移发生时提升匹配效率，避免核心区运力惯性滞留。", score=row.final_action_score, sample_size=row.order_count_post, signals=3)); sequence += 1
    low_value = zones.loc[(zones["zone_group"] == "other") & (zones["driver_pay_per_minute_change_rate"] < 0)].nsmallest(2, "final_action_score")
    for _, row in low_value.iterrows():
        cards.append(card("reduce_low_value_supply", sequence, zone=row.zone_name, zone_group=row.zone_group, od=None, window=hour_window(row.hour), problem="该非机场区域的司机单位时间收益走弱，且没有明显外溢承接信号。", evidence={"driver_pay_per_minute_change_rate": round(row.driver_pay_per_minute_change_rate, 3), "spillover_score": round(row.spillover_score, 3), "demand_gap_rate": round(row.demand_gap_rate, 3)}, action="下调该区域的司机推荐权重，避免在低价值时段扩大无效等待。", impact="减少低收益供给占用，把运力释放给需求更强的区域或路线。", score=row.final_action_score, sample_size=row.order_count_post, signals=2)); sequence += 1
    return supply, incentives, discounts, pd.DataFrame(cards)


def main() -> int:
    """Run the strategy recommender against full or sample-mode result files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone-panel", default="data/processed/zone_hour_policy_panel.parquet")
    parser.add_argument("--predictions", default="data/outputs/counterfactual_predictions.csv")
    parser.add_argument("--spillover", default="reports/tables/spillover_zone_ranking.csv")
    parser.add_argument("--pricing", default="reports/tables/pricing_driver_impact.csv")
    parser.add_argument("--sample", action="store_true", help="Use the same bounded sample outputs used by the dashboard.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    zones = zone_context(read_panel(args.zone_panel), read_csv_or_empty(args.predictions), read_csv_or_empty(args.spillover))
    routes = route_context(read_csv_or_empty(args.pricing))
    supply, incentives, discounts, cards = generate_recommendations(zones, routes)
    supply.to_csv(OUTPUTS_DIR / "driver_supply_reallocation.csv", index=False)
    incentives.to_csv(OUTPUTS_DIR / "route_incentive_recommendation.csv", index=False)
    discounts.to_csv(OUTPUTS_DIR / "passenger_discount_recommendation.csv", index=False)
    save_table(cards, "operation_strategy_cards.csv")
    save_json(cards.to_dict(orient="records"), "operation_strategy_cards.json")
    LOGGER.info("Generated %s cards, %s supply actions, %s route incentives and %s discounts", len(cards), len(supply), len(incentives), len(discounts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
