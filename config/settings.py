"""
Food Factor Analytics — Shared Settings

Centralizes configuration for API keys (from environment variables),
default file paths, daypart definitions, industry benchmarks, and
operational thresholds used across all POS adapters.

Edit the RESTAURANT PROFILE section per-client.  All downstream
modules import from here.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any

# ── API Keys (loaded from environment variables) ─────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
MODAL_TOKEN_ID: str = os.getenv("MODAL_TOKEN_ID", "")
MODAL_TOKEN_SECRET: str = os.getenv("MODAL_TOKEN_SECRET", "")

# ── Default Paths ─────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
DUMMY_DATA_DIR: Path = DATA_DIR / "dummy"
CLIENT_DATA_DIR: Path = DATA_DIR / "client"
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs"
CHARTS_DIR: Path = OUTPUT_DIR / "charts"

# ── Restaurant Profile (edit per-client) ─────────────────────────────────
RESTAURANT_NAME: str = "Coastal Table"
RESTAURANT_LOCATION: str = "Vancouver, BC"
RESTAURANT_TYPE: str = "Mid-to-Upscale West Coast"
REPORT_PERIOD: str = "March 2026"
REPORT_PERIOD_START: str = "2026-03-01"
REPORT_PERIOD_END: str = "2026-03-31"
TOTAL_SEATS: int = 72
POS_SYSTEM: str = "Square for Restaurants Plus"

# ── Daypart Definitions (24-hr boundaries) ───────────────────────────────
DAYPARTS: Dict[str, Tuple[int, int]] = {
    "Breakfast/Brunch": (6, 11),     # 06:00 – 10:59
    "Lunch":            (11, 15),    # 11:00 – 14:59
    "Afternoon":        (15, 17),    # 15:00 – 16:59
    "Dinner":           (17, 21),    # 17:00 – 20:59
    "Late Night":       (21, 24),    # 21:00 – 23:59
}

DAY_ORDER: List[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# ── Industry Benchmarks — Upscale Casual (Canada) ───────────────────────
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
    "avg_check_target":     45.00,
    "overtime_threshold_hours": 40,
}

# ── Menu Engineering Thresholds ──────────────────────────────────────────
MENU_ENGINEERING: Dict[str, Any] = {
    "popularity_metric":    "quantity_sold",
    "profitability_metric": "contribution_margin",
    "popularity_threshold": 0.70,
    "margin_threshold":     0.60,
}

# ── Tax Rates (BC, Canada) ───────────────────────────────────────────────
GST_RATE: float = 0.05
PST_RATE: float = 0.07
COMBINED_TAX_RATE: float = GST_RATE + PST_RATE
TAX_RATES: Dict[str, float] = {
    "GST": GST_RATE,
    "PST": PST_RATE,
}

# ── Operational Flags — Thresholds ───────────────────────────────────────
FLAGS: Dict[str, float] = {
    "high_void_threshold":      0.02,
    "high_refund_threshold":    0.01,
    "high_discount_threshold":  0.05,
    "overtime_alert_hours":     10,     # weekly OT hours per person
    "low_margin_item_pct":      0.20,   # items below 20 % margin
    "high_noshow_threshold":    0.10,
}


def ensure_output_dirs() -> None:
    """Create output directories if they do not exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    DUMMY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLIENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
