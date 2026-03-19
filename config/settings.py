"""
Food Factor Analytics — Shared Settings

Centralizes configuration for API keys (from environment variables),
default file paths, daypart definitions, industry benchmarks, and
operational thresholds used across all POS adapters.
"""

import os
from pathlib import Path
from typing import Dict, Any

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

# ── Daypart Definitions ──────────────────────────────────────────────────
DAYPART_DEFINITIONS: Dict[str, tuple] = {
    "Early Morning": (5, 8),
    "Breakfast": (8, 11),
    "Lunch": (11, 14),
    "Afternoon": (14, 17),
    "Dinner": (17, 21),
    "Late Night": (21, 5),
}

DAY_ORDER: list = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# ── Industry Benchmarks ─────────────────────────────────────────────────
BENCHMARKS: Dict[str, Any] = {
    "food_cost_pct": 30.0,
    "labor_cost_pct": 28.0,
    "prime_cost_pct": 58.0,
    "avg_check_target": 45.0,
    "splh_target": 40.0,
    "overtime_threshold_hours": 40,
    "no_show_rate_target": 10.0,
    "void_rate_threshold": 2.0,
    "discount_rate_threshold": 5.0,
    "refund_rate_threshold": 1.5,
}

# ── Menu Engineering Thresholds ──────────────────────────────────────────
MENU_ENGINEERING: Dict[str, float] = {
    "popularity_threshold": 0.70,
    "margin_threshold": 0.60,
}

# ── Tax Rates ────────────────────────────────────────────────────────────
TAX_RATES: Dict[str, float] = {
    "GST": 0.05,
    "PST": 0.07,
}


def ensure_output_dirs() -> None:
    """Create output directories if they do not exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DUMMY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLIENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
