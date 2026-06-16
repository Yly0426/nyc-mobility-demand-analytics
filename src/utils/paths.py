from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "nyc_tlc"
PROCESSED_DIR = DATA_DIR / "processed"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"


def ensure_project_dirs() -> None:
    for path in [PROCESSED_DIR, WAREHOUSE_DIR, REPORTS_DIR, FIGURES_DIR, TABLES_DIR]:
        path.mkdir(parents=True, exist_ok=True)

