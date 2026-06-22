"""Generate report tables and figures for OD flow changes."""
from __future__ import annotations
import argparse, logging
from src.analysis.analysis_utils import read_panel
from src.analysis.report_analysis_modules import od_flow
def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--input", default="data/processed/trip_policy_features.parquet"); parser.add_argument("--sample", action="store_true"); args=parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s"); od_flow(read_panel(args.input)); return 0
if __name__ == "__main__": raise SystemExit(main())
