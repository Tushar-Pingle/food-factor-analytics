"""
Food Factor Analytics — Output Validation Script

Validates a standardized output directory against the output schema contract.
Checks that all required JSON files exist, validates field types and presence,
and confirms all required charts are present.

Usage:
    python -m pos_analysis.shared.validate_output ./outputs/restaurant_name/
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pos_analysis.shared.output_schema import (
    REQUIRED_JSON_FILES,
    REQUIRED_CHARTS,
)

logger = logging.getLogger("food_factor.validate")


class ValidationResult:
    """Collects pass/fail results for a validation run."""

    def __init__(self):
        self.passes: List[str] = []
        self.failures: List[str] = []
        self.warnings: List[str] = []

    def ok(self, msg: str) -> None:
        self.passes.append(msg)

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0

    def summary(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("FOOD FACTOR OUTPUT VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append("")

        if self.passed:
            lines.append("RESULT: PASS")
        else:
            lines.append("RESULT: FAIL")

        lines.append(f"  Checks passed:  {len(self.passes)}")
        lines.append(f"  Checks failed:  {len(self.failures)}")
        lines.append(f"  Warnings:       {len(self.warnings)}")
        lines.append("")

        if self.failures:
            lines.append("FAILURES:")
            for f in self.failures:
                lines.append(f"  [FAIL] {f}")
            lines.append("")

        if self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  [WARN] {w}")
            lines.append("")

        if self.passes:
            lines.append("PASSES:")
            for p in self.passes:
                lines.append(f"  [OK]   {p}")

        return "\n".join(lines)


# ── Schema definitions for validation ────────────────────────────────────

# Required fields per JSON file and their expected types
# None means any type is acceptable, "nullable" means field can be null
FIELD_SPECS: Dict[str, Dict[str, Any]] = {
    "metadata.json": {
        "pos_system": str,
        "restaurant_name": str,
        "generated_at": str,
        "table_row_counts": dict,
    },
    "summary_metrics.json": {
        "total_net_revenue": (int, float),
        "total_gross_revenue": (int, float),
        "avg_daily_revenue": (int, float),
        "total_transactions": (int, float),
        "avg_check": (int, float),
        "total_covers": (int, float),
        "total_tips": (int, float),
        "avg_tip_pct": (int, float),
        "total_discounts": (int, float),
        "discount_rate_pct": (int, float),
        # These are nullable
        # "labor_pct": nullable
        # "splh": nullable
    },
    "sales_analysis.json": {
        "daily_trend": list,
        "day_of_week": list,
        "daypart": list,
        "order_type": list,
        "category_performance": list,
        "top_items": list,
        "bottom_items": list,
        "hourly_heatmap": list,
    },
    "menu_engineering.json": {
        "matrix": list,
        "food_cost_by_category": list,
        "classification_summary": dict,
        "overall_food_cost_pct": (int, float),
    },
    "labor_analysis.json": {
        "total_labor_cost": (int, float),
        "total_paid_hours": (int, float),
        "labor_pct": (int, float),
        "splh": (int, float),
        "daily_labor": list,
        "foh_boh_split": list,
        "by_role": list,
    },
    "payment_analysis.json": {
        "methods": list,
        "overall_tip_rate": (int, float),
        "total_tips": (int, float),
        "discount_rate_pct": (int, float),
        "total_discounts": (int, float),
    },
    "operational_flags.json": {
        "flags": list,
        "void_summary": dict,
        "refund_summary": dict,
    },
    "delivery_analysis.json": {
        "platform_comparison": list,
    },
    "reservation_analysis.json": {},
    "customer_analysis.json": {},
}

# Nullable fields in summary_metrics (these can be null/None)
NULLABLE_FIELDS = {
    "summary_metrics.json": [
        "labor_pct", "splh", "total_labor_cost",
        "delivery_net_margin", "noshow_rate",
        "menu_stars_count", "menu_dogs_count",
    ],
}


def validate_json_file(
    filepath: Path,
    filename: str,
    result: ValidationResult,
) -> dict | None:
    """Validate a single JSON file exists and is parseable."""
    if not filepath.exists():
        result.fail(f"{filename} — file not found")
        return None

    try:
        with open(filepath) as f:
            data = json.load(f)
        result.ok(f"{filename} — file exists and is valid JSON")
        return data
    except json.JSONDecodeError as e:
        result.fail(f"{filename} — invalid JSON: {e}")
        return None


def validate_fields(
    data: dict,
    filename: str,
    specs: Dict[str, Any],
    result: ValidationResult,
) -> None:
    """Validate required fields exist with correct types."""
    for field, expected_type in specs.items():
        if field not in data:
            result.fail(f"{filename} — missing required field: '{field}'")
            continue

        value = data[field]
        if value is None:
            # Check if this field is nullable
            nullable_list = NULLABLE_FIELDS.get(filename, [])
            if field in nullable_list:
                result.ok(f"{filename}.{field} — null (allowed)")
            else:
                result.warn(f"{filename}.{field} — is null (unexpected)")
            continue

        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                result.fail(
                    f"{filename}.{field} — expected {expected_type}, got {type(value).__name__}"
                )
            else:
                result.ok(f"{filename}.{field} — type OK ({type(value).__name__})")
        elif expected_type is not None:
            if not isinstance(value, expected_type):
                result.fail(
                    f"{filename}.{field} — expected {expected_type.__name__}, got {type(value).__name__}"
                )
            else:
                result.ok(f"{filename}.{field} — type OK")

    # Check for 'extended' key
    if "extended" not in data:
        result.warn(f"{filename} — missing 'extended' key (bonus data)")
    else:
        result.ok(f"{filename} — has 'extended' key")


def validate_charts(output_dir: Path, result: ValidationResult) -> None:
    """Validate that all required chart files exist."""
    charts_dir = output_dir / "charts"
    if not charts_dir.exists():
        result.fail("charts/ directory not found")
        return

    result.ok("charts/ directory exists")

    for chart_name in REQUIRED_CHARTS:
        chart_path = charts_dir / chart_name
        if chart_path.exists():
            result.ok(f"charts/{chart_name} — found")
        else:
            result.warn(f"charts/{chart_name} — not found (may not be generated yet)")


def validate_output_dir(output_dir: Path) -> ValidationResult:
    """
    Run full validation on a standardized output directory.

    Args:
        output_dir: Path to the standard output directory.

    Returns:
        ValidationResult with all pass/fail/warning details.
    """
    result = ValidationResult()

    if not output_dir.exists():
        result.fail(f"Output directory does not exist: {output_dir}")
        return result

    if not output_dir.is_dir():
        result.fail(f"Path is not a directory: {output_dir}")
        return result

    result.ok(f"Output directory exists: {output_dir}")

    # Validate each required JSON file
    for filename in REQUIRED_JSON_FILES:
        filepath = output_dir / filename
        data = validate_json_file(filepath, filename, result)

        if data is not None and filename in FIELD_SPECS:
            validate_fields(data, filename, FIELD_SPECS[filename], result)

    # Validate charts
    validate_charts(output_dir, result)

    # Check metadata consistency
    meta_path = output_dir / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            pos = meta.get("pos_system", "")
            if pos in ("square", "touchbistro", "lightspeed"):
                result.ok(f"metadata.pos_system — valid: '{pos}'")
            else:
                result.warn(f"metadata.pos_system — unknown: '{pos}'")
        except Exception:
            pass

    return result


def main() -> None:
    """CLI entry point for output validation."""
    parser = argparse.ArgumentParser(
        prog="validate-output",
        description="Validate a Food Factor standardized output directory.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Path to the standardized output directory to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    result = validate_output_dir(args.output_dir.resolve())

    if args.strict:
        for w in result.warnings:
            result.fail(f"(strict) {w}")
        result.warnings.clear()

    print(result.summary())

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
