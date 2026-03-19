"""
Category Analyzer — NEW for Food Factor pipeline.

Goes deeper on predefined categories:
food quality, drink quality, service speed, staff friendliness,
ambiance/noise, value/pricing, wait times, cleanliness, parking, accessibility,
presentation/plating, portion size, menu variety.

Uses Claude to classify each review's mentions into these categories
with per-category sentiment and representative excerpts.
"""

import json
import re
from typing import Dict, Any, List

from ..config import (
    CLAUDE_MODEL,
    EXTRACTION_MAX_TOKENS,
    EXTRACTION_TEMPERATURE,
    ANALYSIS_CATEGORIES,
    SENTIMENT_THRESHOLD_POSITIVE,
    SENTIMENT_THRESHOLD_NEGATIVE,
)


def build_category_prompt(reviews: List[str], restaurant_name: str) -> str:
    """Build the category analysis prompt."""
    numbered = "\n\n".join([f"[Review {i}]: {r}" for i, r in enumerate(reviews)])
    cats = ", ".join(ANALYSIS_CATEGORIES)

    return f"""You are analyzing customer reviews for {restaurant_name}.
Classify each review's content into these categories: {cats}

REVIEWS:
{numbered}

For EACH category that appears in at least 1 review, provide:
- mention_count: how many reviews mention this category
- avg_sentiment: average sentiment (-1.0 to 1.0) across mentions
- positive_themes: list of positive things said (2-3 max)
- negative_themes: list of negative things said (2-3 max)
- representative_excerpt: one short paraphrase that captures the typical feedback

OUTPUT (JSON):
{{
  "categories": [
    {{
      "name": "food quality",
      "mention_count": 15,
      "avg_sentiment": 0.72,
      "positive_themes": ["fresh ingredients", "great flavors"],
      "negative_themes": ["inconsistent portions"],
      "representative_excerpt": "Guests consistently praise the freshness..."
    }}
  ]
}}

CRITICAL: Output ONLY valid JSON. Only include categories that actually appear in the reviews."""


def analyze_categories(
    reviews: List[str],
    restaurant_name: str,
    api_key: str,
) -> List[Dict[str, Any]]:
    """
    Run category-level analysis on a batch of reviews.

    Args:
        reviews: Clean review texts (pass all or a sample of ~100)
        restaurant_name: Name of the restaurant
        api_key: Anthropic API key

    Returns:
        List of category dicts with mention_count, avg_sentiment, themes, etc.
    """
    from anthropic import Anthropic

    if not reviews:
        return []

    # Sample if too many reviews for one call
    sample = reviews[:100] if len(reviews) > 100 else reviews
    print(f"📊 Running category analysis on {len(sample)} reviews...")

    client = Anthropic(api_key=api_key)
    prompt = build_category_prompt(sample, restaurant_name)

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=EXTRACTION_MAX_TOKENS,
            temperature=EXTRACTION_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()

        match = re.search(r"\{[\s\S]*\}", result_text)
        if match:
            data = json.loads(match.group())
            categories = data.get("categories", [])
            print(f"✅ Category analysis complete: {len(categories)} categories identified")
            return categories
        else:
            print("⚠️ No JSON in category analysis response")
            return []

    except Exception as e:
        print(f"❌ Category analysis error: {e}")
        return []
