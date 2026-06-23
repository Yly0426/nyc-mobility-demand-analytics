"""Single entry point for the report-oriented NYC ride-hailing project."""

from __future__ import annotations

import argparse
import subprocess
import sys


MODULES = [
    "src.etl.run_etl_pipeline", "src.report_analysis.prepare_data", "src.report_analysis.run_hive_sql_exports",
    "src.report_analysis.generate_figures", "src.models.zone_hour_demand_forecast", "src.analysis.did_policy_impact",
    "src.analysis.event_study_congestion", "src.report_analysis.generate_report",
]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--sample", action="store_true"); parser.add_argument("--rows-per-file", type=int, default=10000, help="Bounded rows per monthly Parquet file in sample mode."); args = parser.parse_args()
    for module in MODULES:
        command = [sys.executable, "-m", module]
        if args.sample:
            command.append("--sample")
        if module == "src.etl.run_etl_pipeline":
            command += ["--rows-per-file", str(args.rows_per_file)]
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
