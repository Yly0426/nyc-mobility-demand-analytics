"""Run the sample-mode report pipeline from raw data to Markdown report."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

from src.utils.project import load_yaml, resolve_project_path


MODULES = [
    "src.etl.run_etl_pipeline",
    "src.analysis.demand_shift_analysis",
    "src.analysis.temporal_pattern_analysis",
    "src.analysis.od_flow_analysis",
    "src.analysis.pricing_pressure_analysis",
    "src.analysis.driver_pressure_analysis",
    "src.analysis.airport_route_analysis",
    "src.analysis.response_time_analysis",
    "src.analysis.did_policy_impact",
    "src.analysis.event_study_congestion",
    "src.analysis.spillover_analysis",
    "src.analysis.pricing_driver_impact",
    "src.analysis.heterogeneity_analysis",
    "src.models.counterfactual_demand_baseline",
    "src.models.operation_strategy_recommender",
    "src.reports.generate_business_report",
]


def main() -> int:
    """Execute every reproducible report step using the configured sample size."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/analysis_config.yaml")
    parser.add_argument("--sample", action="store_true", help="Force bounded real-data sample mode.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_yaml(resolve_project_path(args.config))
    rows = int(config.get("sample", {}).get("rows_per_file", 60000))
    for module in MODULES:
        command = [sys.executable, "-m", module, "--sample"]
        if module == "src.etl.run_etl_pipeline":
            command.extend(["--rows-per-file", str(rows)])
        logging.info("Running %s", module)
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
