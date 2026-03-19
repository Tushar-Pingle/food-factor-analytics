"""
pos_analysis.shared
====================
Cross-POS shared modules used by all POS analysis pipelines.

Modules:
    - menu_engineering: Stars/Plowhorses/Puzzles/Dogs classification matrix
    - cross_domain:     Combined analysis across POS + delivery + reservations
    - exporters:        Markdown/JSON/CSV report output formatting
"""

from .menu_engineering import classify_menu_items, run_menu_engineering
from .cross_domain import build_executive_summary
from .exporters import generate_markdown_report

__all__ = [
    "classify_menu_items",
    "run_menu_engineering",
    "build_executive_summary",
    "generate_markdown_report",
]
