"""
Review Analyzers — Deep-dive analysis on menu items, categories, and insights.

Modules:
- trend_analyzer: Rating and sentiment trends over time
- category_analyzer: Analysis by predefined categories (food quality, service, etc.)
- menu_item_analyzer: Per-item sentiment breakdown and recommendations
- competitive_analyzer: Competitive benchmarking
- insights_generator: Chef and manager actionable insights
"""

from .trend_analyzer import build_trend_data, compute_trend_stats
from .category_analyzer import analyze_categories
from .menu_item_analyzer import analyze_menu_items
from .competitive_analyzer import build_comparison
from .insights_generator import generate_insights

__all__ = [
    "build_trend_data",
    "compute_trend_stats",
    "analyze_categories",
    "analyze_menu_items",
    "build_comparison",
    "generate_insights",
]
