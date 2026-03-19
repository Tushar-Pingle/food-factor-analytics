"""
Review Data Processors — Text cleaning, sentiment, and theme extraction.

Modules:
- cleaner: ReviewCleaner for deduplication and normalization
- sentiment: Keyword-based sentiment scoring and rating parsing
- theme_extractor: Claude-based extraction of food items, drinks, and aspects
"""

from .cleaner import ReviewCleaner, clean_reviews_for_ai
from .sentiment import calculate_sentiment, parse_rating
from .theme_extractor import (
    process_batch,
    merge_batch_results,
    generate_summaries,
    apply_summaries,
)

__all__ = [
    "ReviewCleaner",
    "clean_reviews_for_ai",
    "calculate_sentiment",
    "parse_rating",
    "process_batch",
    "merge_batch_results",
    "generate_summaries",
    "apply_summaries",
]
