"""Turn policy evidence into prioritized platform-operation strategy cards."""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from src.analysis.analysis_utils import save_json, save_table
from src.utils.project import TABLES_DIR


def main() -> int:
    """Generate evidence-backed actions for supply, OD and boundary operations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--spillover", default="reports/tables/spillover_zone_ranking.csv")
    parser.add_argument("--pricing", default="reports/tables/pricing_driver_impact.csv")
    parser.add_argument("--heterogeneity", default="reports/tables/heterogeneity_summary.csv")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    spillover = pd.read_csv(args.spillover)
    pricing = pd.read_csv(args.pricing)
    heterogeneity = pd.read_csv(args.heterogeneity)
    cards: list[dict] = []
    for _, row in spillover.loc[spillover["zone_group"].eq("spillover_zones")].head(3).iterrows():
        cards.append({"strategy_id": f"boundary_{row.zone_id}", "strategy_type": "boundary_zone_strategy", "target_zone": row.zone_name, "target_od_pair": None, "target_time_window": "Monitor by hour", "problem_detected": "Boundary-zone demand may be absorbing trips displaced from the congestion zone.", "evidence_metric": f"spillover_score={row.spillover_score:.3f}; post orders={int(row.post_order_count)}", "recommended_action": "Pre-position drivers and cap idle time through zone-level dispatch nudges.", "expected_business_impact": "Improve pickup reliability while avoiding excess waiting in the core.", "priority": "high"})
    for _, row in pricing.loc[pricing["subsidy_signal"]].head(3).iterrows():
        cards.append({"strategy_id": f"route_{len(cards)+1}", "strategy_type": "route_level_incentive", "target_zone": None, "target_od_pair": f"{row.pickup_zone_name} -> {row.dropoff_zone_name}", "target_time_window": "Policy-period route", "problem_detected": "Passenger price increased while driver pay per minute did not keep pace.", "evidence_metric": f"fare/mile change={row.fare_per_mile_change:.2f}; driver-pay/min change={row.driver_pay_per_minute_change:.2f}", "recommended_action": "Test targeted driver incentive with holdout measurement before broad subsidy rollout.", "expected_business_impact": "Protect route supply on economically unattractive trips.", "priority": "high"})
    hour = heterogeneity.loc[heterogeneity["dimension"].eq("hour_group")].sort_values("relative_change")
    if not hour.empty:
        row = hour.iloc[0]
        cards.append({"strategy_id": "peak_hour_1", "strategy_type": "peak_hour_operation", "target_zone": "treated zones", "target_od_pair": None, "target_time_window": str(row.segment), "problem_detected": "This operating window had the largest observed demand contraction.", "evidence_metric": f"relative demand change={row.relative_change:.1%}", "recommended_action": "Reduce blanket driver positioning and use demand-triggered dispatch thresholds.", "expected_business_impact": "Lower unproductive driver time while preserving service where requests remain.", "priority": "medium"})
    result = pd.DataFrame(cards)
    save_table(result, "operation_strategy_cards.csv")
    save_json(result.to_dict(orient="records"), "operation_strategy_cards.json")
    logging.info("Generated %s strategy cards", len(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
