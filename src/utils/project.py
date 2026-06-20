"""Project paths, YAML loading and small reusable helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = DATA_DIR / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
CONFIG_DIR = PROJECT_ROOT / "config"


def ensure_output_dirs() -> None:
    """Create all directories used by analysis scripts."""
    for path in (PROCESSED_DIR, OUTPUTS_DIR, FIGURES_DIR, TABLES_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 YAML mapping."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def resolve_project_path(path: str | Path) -> Path:
    """Resolve project-relative paths while preserving absolute paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
