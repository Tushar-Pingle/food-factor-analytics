"""
pos_analysis.touchbistro.config
================================
Central configuration for the TouchBistro analysis pipeline.

Contains:
    - Restaurant-specific parameters (name, dates, seats, file paths)
    - Food Factor brand palette (shared across all POS modules — will be
      promoted to pos_analysis.shared.brand once all POS pipelines exist)
    - Industry benchmarks and alert thresholds
    - Daypart definitions
    - Visualization settings

To run against a new client: update RESTAURANT_NAME, DATE_START/END,
TOTAL_SEATS, and point DATA_DIR to their CSV export folder.
"""

from pathlib import Path
from typing import Dict, List, Tuple

# ──────────────────────────────────────────────
# 1. RESTAURANT PROFILE
# ──────────────────────────────────────────────

RESTAURANT_NAME: str = "Coastal Table"
RESTAURANT_LOCATION: str = "Vancouver, BC"
REPORT_PERIOD: str = "March 1–30, 2026"
REPORT_DATE: str = "2026-04-05"
TOTAL_SEATS: int = 72
POS_SYSTEM: str = "TouchBistro"

DATE_START: str = "2026-03-01"
DATE_END: str = "2026-03-30"

SECTIONS: List[str] = ["Main Dining", "Patio", "Bar", "Cash Register"]

# ──────────────────────────────────────────────
# 2. FILE PATHS
# ──────────────────────────────────────────────

DATA_DIR: Path = Path("data")

FILE_MAP: Dict[str, str] = {
    "detailed_sales":   "TouchBistro_01_detailed_sales.csv",
    "item_totals":      "TouchBistro_02_sales_item_totals.csv",
    "shifts":           "TouchBistro_03_detailed_shift_report.csv",
    "delivery":         "TouchBistro_04_delivery_orders.csv",
    "reservations":     "TouchBistro_05_reservations.csv",
    "payments":         "TouchBistro_06_payments_refund_totals.csv",
}

CHART_OUTPUT_DIR: Path = Path("charts")

# ──────────────────────────────────────────────
# 3. FOOD FACTOR BRAND PALETTE
#    NOTE: These colors are shared across all POS modules.
#    Will be promoted to pos_analysis.shared.brand in a
#    future refactor so Square/Lightspeed import from there.
# ──────────────────────────────────────────────

COLORS: Dict[str, str] = {
    "primary":      "#1B2A4A",   # Deep Navy
    "secondary":    "#D4A843",   # Warm Gold
    "accent_1":     "#6B8F71",   # Sage Green
    "accent_2":     "#C85C3B",   # Terracotta
    "background":   "#F8F6F0",   # Off-White
    "text":         "#2D2D2D",   # Charcoal
    "light_gray":   "#E0DDD5",   # Borders / Dividers
    "positive":     "#2E7D32",   # Forest Green
    "negative":     "#C62828",   # Deep Red
    "neutral":      "#546E7A",   # Steel Blue
}

CHART_PALETTE: List[str] = [
    COLORS["primary"],
    COLORS["secondary"],
    COLORS["accent_1"],
    COLORS["accent_2"],
    COLORS["neutral"],
    COLORS["positive"],
    COLORS["negative"],
]

# ──────────────────────────────────────────────
# 4. DAYPART DEFINITIONS
# ──────────────────────────────────────────────

# (label, start_hour_inclusive, end_hour_exclusive)
DAYPARTS: List[Tuple[str, int, int]] = [
    ("Breakfast/Brunch", 7, 11),
    ("Lunch",            11, 15),
    ("Afternoon",        15, 17),
    ("Dinner",           17, 22),
    ("Late Night",       22, 26),  # wraps to 2 AM
]

# ──────────────────────────────────────────────
# 5. MENU ENGINEERING THRESHOLDS
# ──────────────────────────────────────────────

POPULARITY_INDEX: float = 0.70

# ──────────────────────────────────────────────
# 6. INDUSTRY BENCHMARKS (casual / upscale casual)
# ──────────────────────────────────────────────

BENCHMARKS: Dict[str, Tuple[float, float]] = {
    "food_cost_pct":        (28.0, 35.0),
    "labor_pct":            (25.0, 35.0),
    "prime_cost_pct":       (55.0, 65.0),
    "void_rate_pct":        (0.0, 2.0),
    "comp_rate_pct":        (0.0, 3.0),
    "no_show_rate_pct":     (0.0, 10.0),
    "avg_tip_pct":          (15.0, 20.0),
    "delivery_commission":  (15.0, 30.0),
    "splh":                 (40.0, 60.0),
}

# ──────────────────────────────────────────────
# 7. OPERATIONAL FLAGS — ALERT THRESHOLDS
# ──────────────────────────────────────────────

ALERT_VOID_RATE_PCT: float = 2.0
ALERT_COMP_RATE_PCT: float = 3.0
ALERT_NOSHOW_RATE_PCT: float = 10.0
ALERT_DELIVERY_CANCEL_PCT: float = 5.0

# ──────────────────────────────────────────────
# 8. TAX RATES (BC)
# ──────────────────────────────────────────────

GST_RATE: float = 0.05
PST_RATE_ALCOHOL: float = 0.10

# ──────────────────────────────────────────────
# 9. VISUALIZATION SETTINGS
# ──────────────────────────────────────────────

CHART_DPI: int = 200
CHART_WIDTH: int = 10       # inches
CHART_HEIGHT: int = 6       # inches
CHART_FONT_FAMILY: str = "sans-serif"
CHART_FONT_SIZE_TITLE: int = 16
CHART_FONT_SIZE_LABEL: int = 12
CHART_FONT_SIZE_TICK: int = 10
CHART_FONT_SIZE_ANNOTATION: int = 9
CHART_FORMAT: str = "png"
