"""
Trend Analyzer — EXTRACTED from modal_backend.py

Builds trend_data list from the review DataFrame (date, rating, sentiment).
Includes rating estimation from sentiment when no rating is available.
"""

import pandas as pd
from typing import List, Dict, Any

from ..processors.sentiment import calculate_sentiment, parse_rating


def build_trend_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Build trend data from a review DataFrame.

    EXTRACTED from modal_backend.py full_analysis_parallel (lines 930-958).

    Args:
        df: DataFrame with columns: review_text, overall_rating, date
            (and optionally food_rating, service_rating, ambience_rating)

    Returns:
        {"trend_data": [...], "estimated_rating_count": int}
    """
    trend_data = []
    estimated_rating_count = 0

    for _, row in df.iterrows():
        text = str(row.get("review_text", ""))
        rating = float(row.get("overall_rating", 0) or 0)
        sentiment = calculate_sentiment(text)

        # Estimate rating from sentiment if missing
        if rating == 0 and sentiment != 0:
            rating = round((sentiment + 1) * 2 + 1, 1)  # -1→1, 0→3, 1→5
            estimated_rating_count += 1

        date_val = row.get("date", "")
        if pd.isna(date_val):
            date_val = ""
        else:
            date_val = str(date_val).strip()

        trend_data.append({
            "date": date_val,
            "rating": rating,
            "sentiment": sentiment,
        })

    if estimated_rating_count > 0:
        print(f"📊 Estimated {estimated_rating_count} ratings from sentiment")

    return {
        "trend_data": trend_data,
        "estimated_rating_count": estimated_rating_count,
    }


def compute_trend_stats(trend_data: List[Dict]) -> Dict[str, Any]:
    """
    Compute aggregate statistics from trend data.
    NEW — provides summary metrics for reports.
    """
    if not trend_data:
        return {"avg_rating": 0, "avg_sentiment": 0, "total_reviews": 0}

    ratings = [t["rating"] for t in trend_data if t["rating"] > 0]
    sentiments = [t["sentiment"] for t in trend_data]

    return {
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        "avg_sentiment": round(sum(sentiments) / len(sentiments), 3) if sentiments else 0,
        "total_reviews": len(trend_data),
        "reviews_with_ratings": len(ratings),
        "positive_pct": round(
            sum(1 for s in sentiments if s >= 0.6) / max(len(sentiments), 1) * 100, 1
        ),
        "negative_pct": round(
            sum(1 for s in sentiments if s < 0) / max(len(sentiments), 1) * 100, 1
        ),
    }
