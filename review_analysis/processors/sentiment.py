"""
Sentiment Calculator — EXTRACTED from modal_backend.py

Contains the keyword-based sentiment scorer used for quick local scoring
(before the Claude-based NLP extraction runs).

Also includes rating parsing logic extracted from full_analysis_parallel().
"""

import pandas as pd
from typing import Any


def calculate_sentiment(text: str) -> float:
    """
    Simple keyword-based sentiment calculation.
    Returns value from -1 (very negative) to +1 (very positive).

    EXTRACTED from modal_backend.py lines 92-114.
    """
    if not text:
        return 0.0
    text = str(text).lower()

    positive = [
        "amazing", "excellent", "fantastic", "great", "awesome", "delicious",
        "perfect", "outstanding", "loved", "beautiful", "fresh", "friendly",
        "best", "wonderful", "incredible", "superb", "exceptional", "good",
        "nice", "tasty", "recommend", "enjoy", "impressed", "favorite",
    ]
    negative = [
        "terrible", "horrible", "awful", "bad", "worst", "disappointing",
        "poor", "overpriced", "slow", "rude", "cold", "bland", "mediocre",
        "disgusting", "inedible", "undercooked", "overcooked",
    ]

    pos = sum(1 for w in positive if w in text)
    neg = sum(1 for w in negative if w in text)

    if pos + neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


def parse_rating(val: Any) -> float:
    """
    Convert rating to numeric (0-5 scale).
    EXTRACTED from modal_backend.py full_analysis_parallel() lines 887-910.
    """
    if pd.isna(val) or val == "" or val is None:
        return 0.0

    try:
        num = float(val)
        if 0 <= num <= 5:
            return num
    except (ValueError, TypeError):
        pass

    text_map = {
        "excellent": 5.0, "very good": 4.5, "good": 4.0,
        "average": 3.0, "below average": 2.0, "poor": 1.0, "terrible": 1.0,
        "5": 5.0, "4": 4.0, "3": 3.0, "2": 2.0, "1": 1.0,
    }

    val_str = str(val).lower().strip()
    for key, num in text_map.items():
        if key in val_str:
            return num

    return 0.0
