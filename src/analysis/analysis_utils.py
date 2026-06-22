"""Shared IO, plotting and interpretation helpers for policy analysis."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

from src.utils.project import FIGURES_DIR, OUTPUTS_DIR, TABLES_DIR, ensure_output_dirs, resolve_project_path


def configure_plot_fonts() -> None:
    """Prefer an installed Chinese font for report figures and exported legends."""
    available = {font.name for font in font_manager.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "Noto Sans SC", "Source Han Sans CN", "SimHei", "Microsoft JhengHei"]
    selected = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


configure_plot_fonts()


def read_panel(path: str) -> pd.DataFrame:
    """Read a Parquet panel with normalized date fields."""
    data = pd.read_parquet(resolve_project_path(path))
    if "trip_date" in data:
        data["trip_date"] = pd.to_datetime(data["trip_date"])
    return data


def save_table(data: pd.DataFrame, name: str) -> Path:
    """Write a report table and return its path."""
    ensure_output_dirs()
    path = TABLES_DIR / name
    data.to_csv(path, index=False)
    return path


def save_json(payload: object, name: str) -> Path:
    """Write dashboard-facing JSON with UTF-8 encoding."""
    ensure_output_dirs()
    path = OUTPUTS_DIR / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def save_plot(fig: plt.Figure, name: str) -> Path:
    """Save a report figure with consistent export settings."""
    ensure_output_dirs()
    path = FIGURES_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path
