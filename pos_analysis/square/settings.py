"""
config/settings.py — Food Factor Shared Settings
==================================================
Restaurant-specific parameters, industry benchmarks, daypart
definitions, tax rates, and operational thresholds. These are
POS-agnostic and shared across all analysis modules.

Edit the RESTAURANT PROFILE section per-client. All downstream
modules import from here.
"""

from pathlib import Path
from typing import Dict, List, Tuple

# ─────────────────────────────────────────────
# RESTAURANT PROFILE  (edit per-client)
# ─────────────────────────────────────────────
RESTAURANT_NAME: str = "Coastal Table"
RESTAURANT_LOCATION: str = "Vancouver, BC"
RESTAURANT_TYPE: str = "Mid-to-Upscale West Coast"
REPORT_PERIOD: str = "February 2026"
REPORT_PERIOD_START: str = "2026-02-01"
REPORT_PERIOD_END: str = "2026-02-28"
TOTAL_SEATS: int = 72
POS_SYSTEM: str = "Square for Restaurants Plus"

# ─────────────────────────────────────────────
# OUTPUT PATHS
# ─────────────────────────────────────────────
OUTPUT_DIR: Path = Path("output")
CHARTS_DIR: Path = OUTPUT_DIR / "charts"

# ─────────────────────────────────────────────
# DAYPART DEFINITIONS  (24-hr boundaries)
# ─────────────────────────────────────────────
DAYPARTS: Dict[str, Tuple[int, int]] = {
    "Breakfast/Brunch": (6, 11),    # 06:00 – 10:59
    "Lunch":            (11, 15),   # 11:00 – 14:59
    "Afternoon":        (15, 17),   # 15:00 – 16:59
    "Dinner":           (17, 21),   # 17:00 – 20:59
    "Late Night":       (21, 24),   # 21:00 – 23:59
}

DAY_ORDER: List[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# ─────────────────────────────────────────────
# INDUSTRY BENCHMARKS — Upscale Casual (Canada)
# ─────────────────────────────────────────────
BENCHMARKS: Dict[str, float] = {
    "food_cost_pct":        0.30,    # 28–32 % target
    "labor_cost_pct":       0.28,    # 25–30 % target
    "prime_cost_pct":       0.60,    # food + labor < 60 %
    "average_check_lunch":  40.00,
    "average_check_dinner": 75.00,
    "void_rate_max":        0.02,    # > 2 % warrants investigation
    "refund_rate_max":      0.01,    # > 1 % warrants investigation
    "discount_rate_max":    0.05,    # > 5 % is aggressive
    "noshow_rate_target":   0.05,    # < 5 % is excellent
    "delivery_margin_min":  0.60,    # net payout / gross > 60 %
    "splh_target":          55.00,   # Sales Per Labor Hour
    "revpash_target":       12.00,   # Revenue Per Available Seat Hour
    "comp_rate_max":        0.015,   # > 1.5 % needs review
}

# ─────────────────────────────────────────────
# MENU ENGINEERING THRESHOLDS
# ─────────────────────────────────────────────
MENU_ENGINEERING: Dict[str, str] = {
    "popularity_metric":    "quantity_sold",
    "profitability_metric": "contribution_margin",
}

# ─────────────────────────────────────────────
# TAX RATES  (BC, Canada)
# ─────────────────────────────────────────────
GST_RATE: float = 0.05
PST_RATE: float = 0.07
COMBINED_TAX_RATE: float = GST_RATE + PST_RATE

# ─────────────────────────────────────────────
# OPERATIONAL FLAGS — THRESHOLDS
# ─────────────────────────────────────────────
FLAGS: Dict[str, float] = {
    "high_void_threshold":      0.02,
    "high_refund_threshold":    0.01,
    "high_discount_threshold":  0.05,
    "overtime_alert_hours":     10,     # weekly OT hours per person
    "low_margin_item_pct":      0.20,   # items below 20 % margin
    "high_noshow_threshold":    0.10,
}
