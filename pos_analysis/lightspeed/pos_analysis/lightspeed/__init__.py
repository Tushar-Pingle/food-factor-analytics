"""
pos_analysis.lightspeed — Lightspeed Restaurant K-Series Pipeline

Data ingestion, analysis, labor optimization, and visualization
for Lightspeed Restaurant POS CSV exports.

Default configuration targets Ember & Oak (development dataset).
Override RESTAURANT_CONFIG and FILE_PATHS per client engagement.
"""

from pathlib import Path
from typing import Dict, Any

# ─────────────────────────────────────────────
# RESTAURANT PROFILE (override per engagement)
# ─────────────────────────────────────────────

RESTAURANT_CONFIG: Dict[str, Any] = {
    "restaurant_name":  "Ember & Oak",
    "location":         "Vancouver, BC",
    "concept":          "Pacific Northwest + Japanese-Influenced",
    "period":           "March 2026",
    "period_days":      30,
    "total_seats":      82,
    "pos_system":       "Lightspeed Restaurant K-Series",
}

# Convenience aliases used by sub-modules
RESTAURANT_NAME: str    = RESTAURANT_CONFIG["restaurant_name"]
RESTAURANT_LOCATION: str = RESTAURANT_CONFIG["location"]
RESTAURANT_CONCEPT: str = RESTAURANT_CONFIG["concept"]
REPORT_PERIOD: str      = RESTAURANT_CONFIG["period"]
REPORT_PERIOD_DAYS: int = RESTAURANT_CONFIG["period_days"]
TOTAL_SEATS: int        = RESTAURANT_CONFIG["total_seats"]
POS_SYSTEM: str         = RESTAURANT_CONFIG["pos_system"]


# ─────────────────────────────────────────────
# FILE PATHS — Lightspeed CSV Exports
# ─────────────────────────────────────────────

DATA_DIR = Path("./data")

FILE_PATHS: Dict[str, Path] = {
    "receipts":       DATA_DIR / "Lightspeed_01_receipts.csv",
    "receipt_items":  DATA_DIR / "Lightspeed_02_receipt_items.csv",
    "modifiers":      DATA_DIR / "Lightspeed_03_modifiers.csv",
    "payments":       DATA_DIR / "Lightspeed_04_payments.csv",
    "labor_shifts":   DATA_DIR / "Lightspeed_05_labor_shifts.csv",
    "products":       DATA_DIR / "Lightspeed_06_products.csv",
    "delivery":       DATA_DIR / "Lightspeed_07_delivery_orders.csv",
    "reservations":   DATA_DIR / "Lightspeed_08_reservations.csv",
    "customers":      DATA_DIR / "Lightspeed_09_customer_directory.csv",
}


# ─────────────────────────────────────────────
# OUTPUT DIRECTORIES
# ─────────────────────────────────────────────

OUTPUT_DIR = Path("./output")
CHART_DIR = OUTPUT_DIR / "charts"


def ensure_dirs() -> None:
    """Create output directories if they don't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
