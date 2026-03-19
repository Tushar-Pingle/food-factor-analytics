"""
Food Factor Review Pipeline — Configuration.

Centralizes all constants, API key names, sentiment thresholds, Modal config,
brand colors, analysis categories, and runtime pipeline configuration.

No internal dependencies — this is the root config module.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================================
# SENTIMENT THRESHOLDS (extracted from modal_backend.py)
# ============================================================================
SENTIMENT_THRESHOLD_POSITIVE: float = 0.6   # >= 0.6 is positive
SENTIMENT_THRESHOLD_NEGATIVE: float = 0.0   # < 0 is negative, 0–0.59 is neutral

# ============================================================================
# SUMMARY COUNTS (extracted from modal_backend.py [INS-04])
# ============================================================================
SUMMARY_FOOD_COUNT: int = 20
SUMMARY_DRINKS_COUNT: int = 15
SUMMARY_ASPECTS_COUNT: int = 20

# ============================================================================
# BATCH PROCESSING
# ============================================================================
BATCH_SIZE: int = 30          # Reviews per NLP batch
MAX_RETRIES: int = 3          # API call retries
RETRY_BACKOFF: int = 5        # Seconds between retries (multiplied by attempt)

# ============================================================================
# CLAUDE MODEL CONFIG
# ============================================================================
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
EXTRACTION_MAX_TOKENS: int = 4000
EXTRACTION_TEMPERATURE: float = 0.3
INSIGHTS_MAX_TOKENS: int = 2000
INSIGHTS_TEMPERATURE: float = 0.4
SUMMARY_MAX_TOKENS: int = 4000
SUMMARY_TEMPERATURE: float = 0.4

# ============================================================================
# MODAL SECRETS — 5-key parallel pattern
# ============================================================================
MODAL_SECRET_BATCH1: str = "anthropic-batch1"
MODAL_SECRET_BATCH2: str = "anthropic-batch2"
MODAL_SECRET_CHEF: str = "anthropic-chef"
MODAL_SECRET_MANAGER: str = "anthropic-manager"
MODAL_SECRET_SUMMARIES: str = "anthropic-summaries"

# ============================================================================
# MODAL FUNCTION CONFIG
# ============================================================================
MODAL_TIMEOUT_BATCH: int = 210
MODAL_TIMEOUT_INSIGHTS: int = 210
MODAL_TIMEOUT_SUMMARIES: int = 210
MODAL_TIMEOUT_MAIN: int = 2100
MODAL_MEMORY_BATCH: int = 512
MODAL_MEMORY_INSIGHTS: int = 512
MODAL_MEMORY_MAIN: int = 1024

# ============================================================================
# SCRAPER DEFAULTS
# ============================================================================
DEFAULT_MAX_REVIEWS: int = 500
COMPETITOR_MAX_REVIEWS: int = 100
SCRAPER_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# ============================================================================
# FOOD FACTOR BRAND COLORS (from SKILL_food-factor-report.md)
# ============================================================================
BRAND_COLORS: dict = {
    "primary": "#1B2A4A",       # Deep Navy
    "secondary": "#D4A843",     # Warm Gold
    "accent1": "#6B8F71",       # Sage Green
    "accent2": "#C85C3B",       # Terracotta
    "background": "#F8F6F0",    # Off-White
    "text": "#2D2D2D",          # Charcoal
    "light_gray": "#E0DDD5",    # Borders/Dividers
    "positive": "#2E7D32",      # Forest Green
    "negative": "#C62828",      # Deep Red
    "neutral": "#546E7A",       # Steel Blue
}

# Plotly-friendly color sequence
BRAND_COLOR_SEQUENCE: List[str] = [
    BRAND_COLORS["primary"],
    BRAND_COLORS["secondary"],
    BRAND_COLORS["accent1"],
    BRAND_COLORS["accent2"],
    BRAND_COLORS["neutral"],
]

# ============================================================================
# CATEGORY ANALYSIS CATEGORIES (NEW)
# ============================================================================
ANALYSIS_CATEGORIES: List[str] = [
    "food quality",
    "drink quality",
    "service speed",
    "staff friendliness",
    "ambiance",
    "noise level",
    "value / pricing",
    "wait times",
    "cleanliness",
    "parking",
    "accessibility",
    "presentation / plating",
    "portion size",
    "menu variety",
]

# ============================================================================
# SUPPORTED PLATFORMS
# ============================================================================
SUPPORTED_PLATFORMS: List[str] = ["google", "opentable", "yelp", "tripadvisor"]


# ============================================================================
# RUNTIME CONFIG — passed around via CLI args
# ============================================================================
@dataclass
class PipelineConfig:
    """Runtime configuration for a single pipeline run."""

    restaurant_name: str
    location: str = "Vancouver"
    platforms: List[str] = field(default_factory=lambda: ["google", "opentable"])
    max_reviews: int = DEFAULT_MAX_REVIEWS
    competitors: List[str] = field(default_factory=list)
    output_dir: str = "output"
    headless: bool = True
    verbose: bool = True

    # URLs can be provided directly; otherwise scrapers will search
    google_url: Optional[str] = None
    opentable_url: Optional[str] = None
    yelp_url: Optional[str] = None
    tripadvisor_url: Optional[str] = None

    @property
    def competitor_max_reviews(self) -> int:
        return COMPETITOR_MAX_REVIEWS


def get_api_key(env_var: str = "ANTHROPIC_API_KEY") -> Optional[str]:
    """Get API key from environment."""
    return os.environ.get(env_var)
