"""
Menu Item Analyzer — NEW for Food Factor pipeline.

Takes the extracted food_items and drinks from the NLP pipeline and
produces a deeper per-item analysis:
- Sentiment distribution (positive / neutral / negative %)
- Related review excerpts (paraphrased)
- Trend direction (if enough data)
- Actionable recommendation per item
"""

import json
import re
from typing import Dict, Any, List

from ..config import (
    CLAUDE_MODEL,
    EXTRACTION_MAX_TOKENS,
    EXTRACTION_TEMPERATURE,
    SENTIMENT_THRESHOLD_POSITIVE,
    SENTIMENT_THRESHOLD_NEGATIVE,
)


def analyze_menu_items(
    food_items: List[Dict[str, Any]],
    drinks: List[Dict[str, Any]],
    restaurant_name: str,
    api_key: str,
    top_n: int = 25,
) -> Dict[str, Any]:
    """
    Deep-dive analysis on individual menu items and drinks.

    Args:
        food_items: Extracted food items with sentiment, mention_count, related_reviews
        drinks: Extracted drinks with same structure
        restaurant_name: Name of the restaurant
        api_key: Anthropic API key
        top_n: Analyze top N items by mention count

    Returns:
        {"food_analysis": [...], "drinks_analysis": [...]}
    """
    from anthropic import Anthropic

    # Take top items by mentions
    top_food = sorted(food_items, key=lambda x: x.get("mention_count", 0), reverse=True)[:top_n]
    top_drinks = sorted(drinks, key=lambda x: x.get("mention_count", 0), reverse=True)[:top_n]

    if not top_food and not top_drinks:
        return {"food_analysis": [], "drinks_analysis": []}

    print(f"🍽️ Analyzing {len(top_food)} food items and {len(top_drinks)} drinks...")

    # Build item summaries with review excerpts
    items_text = _build_items_text(top_food, "FOOD ITEMS")
    drinks_text = _build_items_text(top_drinks, "DRINKS")

    prompt = f"""You are a restaurant consultant analyzing menu item performance for {restaurant_name}.

{items_text}

{drinks_text}

For each item, provide:
1. sentiment_breakdown: {{"positive_pct": 70, "neutral_pct": 20, "negative_pct": 10}}
2. key_praise: What customers love (1-2 phrases)
3. key_criticism: What customers dislike (1-2 phrases, or "None" if all positive)
4. recommendation: One specific action for the kitchen/bar team
5. menu_engineering_tag: "star" (high popularity + high sentiment), "plowhorse" (high popularity + low sentiment), "puzzle" (low popularity + high sentiment), "dog" (low both)

OUTPUT (JSON):
{{
  "food_analysis": [
    {{
      "name": "item name",
      "mention_count": 15,
      "avg_sentiment": 0.82,
      "sentiment_breakdown": {{"positive_pct": 75, "neutral_pct": 20, "negative_pct": 5}},
      "key_praise": "Perfectly cooked, generous portions",
      "key_criticism": "None",
      "recommendation": "Feature prominently on specials board",
      "menu_engineering_tag": "star"
    }}
  ],
  "drinks_analysis": [...]
}}

CRITICAL: Output ONLY valid JSON."""

    client = Anthropic(api_key=api_key)
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
            food_count = len(data.get("food_analysis", []))
            drinks_count = len(data.get("drinks_analysis", []))
            print(f"✅ Menu item analysis: {food_count} food, {drinks_count} drinks")
            return data
        else:
            print("⚠️ No JSON in menu item analysis response")
            return {"food_analysis": [], "drinks_analysis": []}

    except Exception as e:
        print(f"❌ Menu item analysis error: {e}")
        return {"food_analysis": [], "drinks_analysis": []}


def _build_items_text(items: List[Dict], header: str) -> str:
    """Build text representation of items for the prompt."""
    if not items:
        return f"{header}: None"

    lines = [f"{header}:"]
    for item in items:
        name = item.get("name", "?")
        mentions = item.get("mention_count", 0)
        sentiment = item.get("sentiment", 0)

        # Include a few review excerpts if available
        excerpts = []
        for rr in item.get("related_reviews", [])[:3]:
            text = rr.get("review_text", "")
            if text:
                excerpts.append(text[:120])

        excerpt_str = " | ".join(excerpts) if excerpts else "No excerpts"
        lines.append(
            f"  - {name} (mentions: {mentions}, sentiment: {sentiment:+.2f}): {excerpt_str}"
        )

    return "\n".join(lines)
