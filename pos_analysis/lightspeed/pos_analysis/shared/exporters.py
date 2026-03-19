"""
pos_analysis.shared.exporters — Report Data Export Utilities

JSON and CSV serialization for compiled report data dictionaries.
Handles pandas/numpy type conversion for clean serialization.

Used by all POS pipeline runners to write final output files.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def _default_json_handler(obj: Any) -> Any:
    """Handle non-serializable types during JSON export."""
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict("records")
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def export_report_json(
    report: Dict[str, Any],
    filepath: str,
) -> str:
    """
    Export compiled report data as JSON for downstream processing.

    Args:
        report:   Complete report data dictionary from compile_report_data().
        filepath: Destination path for the JSON file.

    Returns:
        The filepath that was written.
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2, default=_default_json_handler)

    logger.info(f"Exported report JSON → {filepath}")
    return filepath


def export_summary_csv(
    report: Dict[str, Any],
    filepath: str,
) -> str:
    """
    Export executive summary KPIs and action plan as a flat CSV.

    Useful for quick import into Google Sheets or Excel.

    Args:
        report:   Complete report data dictionary.
        filepath: Destination path for the CSV file.

    Returns:
        The filepath that was written.
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    rows = []

    # KPI rows
    for kpi in report.get("executive_summary", {}).get("kpis", []):
        rows.append({
            "section":  "KPI",
            "metric":   kpi["metric"],
            "value":    kpi["value"],
            "benchmark": kpi.get("benchmark", ""),
            "status":   kpi.get("status", ""),
        })

    # Action plan rows
    for item in report.get("action_plan", []):
        rows.append({
            "section":  "Action Plan",
            "metric":   item.get("category", ""),
            "value":    item.get("action", ""),
            "benchmark": item.get("impact", ""),
            "status":   item.get("priority", ""),
        })

    pd.DataFrame(rows).to_csv(filepath, index=False)
    logger.info(f"Exported summary CSV → {filepath}")
    return filepath
