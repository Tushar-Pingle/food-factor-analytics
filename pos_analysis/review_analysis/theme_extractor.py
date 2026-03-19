"""
Theme Extractor — EXTRACTED from modal_backend.py

Contains:
- The Claude extraction prompt for food_items, drinks, aspects
- Review-index-to-text mapping logic
- Batch merge logic (weighted average sentiment, appended related_reviews)
- Summary generation prompt

These functions are designed to be called from Modal jobs (modal_jobs/nlp_job.py)
or locally for testing.
"""

import json
import re
from typing import Dict, Any, List

from ..config import (
    SENTIMENT_THRESHOLD_POSITIVE,
    SENTIMENT_THRESHOLD_NEGATIVE,
    CLAUDE_MODEL,
    EXTRACTION_MAX_TOKENS,
    EXTRACTION_TEMPERATURE,
    SUMMARY_MAX_TOKENS,
    SUMMARY_TEMPERATURE,
    SUMMARY_FOOD_COUNT,
    SUMMARY_DRINKS_COUNT,
    SUMMARY_ASPECTS_COUNT,
)


def build_extraction_prompt(reviews: List[str], restaurant_name: str) -> str:
    """
    Build the Claude extraction prompt.
    EXTRACTED from modal_backend.py process_batch_odd/even (lines 159-196, 301-338).
    """
    numbered_reviews = []
    for i, review in enumerate(reviews):
        numbered_reviews.append(f"[Review {i}]: {review}")
    reviews_text = "\n\n".join(numbered_reviews)

    return f"""You are analyzing customer reviews for {restaurant_name}. Extract BOTH menu items AND aspects in ONE PASS.

REVIEWS:
{reviews_text}

YOUR TASK - Extract THREE things simultaneously:
1. **MENU ITEMS** (food & drinks mentioned)
2. **ASPECTS** (what customers care about: service, ambience, etc.)
3. **SENTIMENT** for each

SENTIMENT SCALE (IMPORTANT):
- **Positive ({SENTIMENT_THRESHOLD_POSITIVE} to 1.0):** Customer clearly enjoyed/praised this item or aspect
- **Neutral ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}):** Mixed feelings, okay but not exceptional
- **Negative (-1.0 to {SENTIMENT_THRESHOLD_NEGATIVE - 0.01}):** Customer complained, criticized, or expressed disappointment

RULES:
- Specific items only: "salmon sushi", "miso soup", "sake"
- Separate food from drinks
- Lowercase names
- For EACH item/aspect, list which review NUMBERS mention it

OUTPUT (JSON):
{{
  "food_items": [
    {{"name": "item name", "mention_count": 2, "sentiment": 0.85, "category": "type", "related_reviews": [0, 5]}}
  ],
  "drinks": [
    {{"name": "drink name", "mention_count": 1, "sentiment": 0.7, "category": "alcohol", "related_reviews": [3]}}
  ],
  "aspects": [
    {{"name": "service speed", "mention_count": 3, "sentiment": 0.65, "description": "brief desc", "related_reviews": [1, 2, 7]}}
  ]
}}

CRITICAL: Output ONLY valid JSON, no other text.
Use sentiment scale: >= {SENTIMENT_THRESHOLD_POSITIVE} positive, {SENTIMENT_THRESHOLD_NEGATIVE}-{SENTIMENT_THRESHOLD_POSITIVE - 0.01} neutral, < {SENTIMENT_THRESHOLD_NEGATIVE} negative

Extract everything:"""


def map_review_indices(data: Dict[str, Any], reviews: List[str], start_index: int) -> Dict[str, Any]:
    """
    Map review indices back to full text.
    EXTRACTED from modal_backend.py process_batch_odd/even (lines 212-246).
    """
    for key in ("food_items", "drinks", "aspects"):
        for item in data.get(key, []):
            indices = item.get("related_reviews", [])
            item["related_reviews"] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item["related_reviews"].append({
                        "review_index": start_index + idx,
                        "review_text": reviews[idx],
                    })
            if "name" in item:
                item["name"] = item["name"].lower().strip()
    return data


def process_batch(
    reviews: List[str],
    restaurant_name: str,
    batch_index: int,
    start_index: int,
    api_key: str,
) -> Dict[str, Any]:
    """
    Process a single batch of reviews through Claude extraction.
    EXTRACTED from modal_backend.py process_batch_odd/even.

    Returns: {"success": bool, "batch_index": int, "data": {...}}
    """
    from anthropic import Anthropic

    print(f"🔄 Processing batch {batch_index} ({len(reviews)} reviews)...")

    client = Anthropic(api_key=api_key)
    prompt = build_extraction_prompt(reviews, restaurant_name)

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=EXTRACTION_MAX_TOKENS,
            temperature=EXTRACTION_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(result_text)

        data = map_review_indices(data, reviews, start_index)

        food_count = len(data.get("food_items", []))
        drink_count = len(data.get("drinks", []))
        aspect_count = len(data.get("aspects", []))
        print(f"✅ Batch {batch_index}: {food_count} food, {drink_count} drinks, {aspect_count} aspects")

        return {"success": True, "batch_index": batch_index, "data": data}

    except json.JSONDecodeError as e:
        print(f"⚠️ Batch {batch_index} JSON error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}
    except Exception as e:
        print(f"❌ Batch {batch_index} error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}


def merge_batch_results(batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge results from all batches with weighted sentiment averaging.
    EXTRACTED from modal_backend.py full_analysis_parallel (lines 1010-1074).
    """
    all_food_items: Dict[str, Dict] = {}
    all_drinks: Dict[str, Dict] = {}
    all_aspects: Dict[str, Dict] = {}

    for batch_result in batch_results:
        if not batch_result.get("success"):
            continue

        data = batch_result.get("data", {})

        # Merge food items
        for item in data.get("food_items", []):
            name = item.get("name", "").lower().strip()
            if not name:
                continue
            if name in all_food_items:
                _merge_item(all_food_items[name], item)
            else:
                all_food_items[name] = item

        # Merge drinks
        for item in data.get("drinks", []):
            name = item.get("name", "").lower().strip()
            if not name:
                continue
            if name in all_drinks:
                _merge_item(all_drinks[name], item)
            else:
                all_drinks[name] = item

        # Merge aspects
        for aspect in data.get("aspects", []):
            name = aspect.get("name", "").lower().strip()
            if not name:
                continue
            if name in all_aspects:
                _merge_item(all_aspects[name], aspect)
            else:
                all_aspects[name] = aspect

    # Sort by mention count
    food_list = sorted(all_food_items.values(), key=lambda x: x.get("mention_count", 0), reverse=True)
    drinks_list = sorted(all_drinks.values(), key=lambda x: x.get("mention_count", 0), reverse=True)
    aspects_list = sorted(all_aspects.values(), key=lambda x: x.get("mention_count", 0), reverse=True)

    print(f"📊 Merged: {len(food_list)} food + {len(drinks_list)} drinks + {len(aspects_list)} aspects")

    return {
        "food_items": food_list,
        "drinks": drinks_list,
        "aspects": aspects_list,
    }


def _merge_item(existing: Dict, new_item: Dict):
    """Merge a new item into an existing one (weighted sentiment avg, appended reviews)."""
    old_count = existing["mention_count"]
    new_count = new_item.get("mention_count", 1)
    existing["mention_count"] += new_count

    # [INS-05] Append related_reviews
    existing.setdefault("related_reviews", []).extend(new_item.get("related_reviews", []))

    # Weighted average sentiment
    total = old_count + new_count
    if total > 0:
        old_sent = existing.get("sentiment", 0)
        new_sent = new_item.get("sentiment", 0)
        existing["sentiment"] = (old_sent * old_count + new_sent * new_count) / total


# ============================================================================
# SUMMARY GENERATION
# ============================================================================

def build_summary_prompt(
    food_items: List[Dict],
    drinks: List[Dict],
    aspects: List[Dict],
    restaurant_name: str,
) -> str:
    """
    Build summary generation prompt.
    EXTRACTED from modal_backend.py generate_all_summaries (lines 714-749).
    """
    food_list_str = "\n".join(
        [f"- {f.get('name', '?')} (sentiment: {f.get('sentiment', 0):.2f}, mentions: {f.get('mention_count', 0)})" for f in food_items]
    )
    drinks_list_str = "\n".join(
        [f"- {d.get('name', '?')} (sentiment: {d.get('sentiment', 0):.2f}, mentions: {d.get('mention_count', 0)})" for d in drinks]
    )
    aspects_list_str = "\n".join(
        [f"- {a.get('name', '?')} (sentiment: {a.get('sentiment', 0):.2f}, mentions: {a.get('mention_count', 0)})" for a in aspects]
    )

    return f"""Generate brief 2-3 sentence summaries for each item at {restaurant_name}.

FOOD ITEMS:
{food_list_str}

DRINKS:
{drinks_list_str}

ASPECTS:
{aspects_list_str}

For each summary:
1. Synthesizes what customers say
2. Reflects the sentiment score (positive if >= {SENTIMENT_THRESHOLD_POSITIVE}, negative if < {SENTIMENT_THRESHOLD_NEGATIVE}, neutral otherwise)
3. Gives actionable insight for restaurant staff

OUTPUT FORMAT (JSON):
{{
  "food": {{
    "item name": "2-3 sentence summary based on reviews...",
    "another item": "summary..."
  }},
  "drinks": {{
    "drink name": "summary..."
  }},
  "aspects": {{
    "aspect name": "summary..."
  }}
}}

CRITICAL: Output ONLY valid JSON. Generate summaries for ALL items listed above."""


def generate_summaries(
    food_items: List[Dict],
    drinks: List[Dict],
    aspects: List[Dict],
    restaurant_name: str,
    api_key: str,
) -> Dict[str, Dict[str, str]]:
    """
    Generate all summaries in a single API call.
    EXTRACTED from modal_backend.py generate_all_summaries (lines 693-773).
    """
    from anthropic import Anthropic

    print(f"📝 Generating summaries for {restaurant_name}...")

    client = Anthropic(api_key=api_key)
    prompt = build_summary_prompt(
        food_items[:SUMMARY_FOOD_COUNT],
        drinks[:SUMMARY_DRINKS_COUNT],
        aspects[:SUMMARY_ASPECTS_COUNT],
        restaurant_name,
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=SUMMARY_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()

        match = re.search(r"\{[\s\S]*\}", result_text)
        if match:
            summaries = json.loads(match.group())
            print(f"✅ Summaries: {len(summaries.get('food', {}))} food, {len(summaries.get('drinks', {}))} drinks, {len(summaries.get('aspects', {}))} aspects")
            return summaries
        else:
            print("⚠️ No JSON found in summary response")
            return {"food": {}, "drinks": {}, "aspects": {}}

    except Exception as e:
        print(f"⚠️ Summary generation error: {e}")
        return {"food": {}, "drinks": {}, "aspects": {}}


def apply_summaries(
    food_list: List[Dict],
    drinks_list: List[Dict],
    aspects_list: List[Dict],
    summaries: Dict[str, Dict[str, str]],
):
    """
    Apply generated summaries back to items.
    EXTRACTED from modal_backend.py lines 1096-1136.
    Uses flexible name matching (lowercase, title, strip).
    """
    food_summaries = summaries.get("food", {})
    drink_summaries = summaries.get("drinks", {})
    aspect_summaries = summaries.get("aspects", {})

    def find_summary(name: str, summary_dict: Dict[str, str]) -> str:
        name_clean = name.lower().strip()
        name_title = name_clean.title()
        if name_clean in summary_dict:
            return summary_dict[name_clean]
        if name_title in summary_dict:
            return summary_dict[name_title]
        for key, val in summary_dict.items():
            if key.lower().strip() == name_clean:
                return val
        return ""

    for item in food_list:
        s = find_summary(item.get("name", ""), food_summaries)
        if s:
            item["summary"] = s

    for item in drinks_list:
        s = find_summary(item.get("name", ""), drink_summaries)
        if s:
            item["summary"] = s

    for item in aspects_list:
        s = find_summary(item.get("name", ""), aspect_summaries)
        if s:
            item["summary"] = s
