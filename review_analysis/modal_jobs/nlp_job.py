"""
Modal NLP Job — Batch processing functions for Modal deployment.

EXTRACTED from modal_backend.py process_batch_odd/process_batch_even.
Unified into a single function that accepts an API key parameter,
eliminating the odd/even split while preserving the parallel .map() pattern.

The 5-key parallel pattern is preserved at the orchestration level (main.py),
not at the Modal function level.
"""

import modal
from typing import Dict, Any, List

from ..config import (
    MODAL_TIMEOUT_BATCH,
    MODAL_MEMORY_BATCH,
    MODAL_SECRET_BATCH1,
    MODAL_SECRET_BATCH2,
)

# ============================================================================
# Modal app and image (shared across all modal_jobs)
# ============================================================================

app = modal.App("food-factor-review-pipeline")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("chromium", "chromium-driver")
    .run_commands("ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver")
    .run_commands("ln -sf /usr/bin/chromium /usr/local/bin/chromium")
    .pip_install(
        "anthropic",
        "selenium",
        "beautifulsoup4",
        "pandas",
        "python-dotenv",
        "plotly",
        "kaleido",
    )
)


# ============================================================================
# BATCH PROCESSORS — Odd/Even split for 2-key parallelism
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name(MODAL_SECRET_BATCH1)],
    timeout=MODAL_TIMEOUT_BATCH,
    retries=3,
    memory=MODAL_MEMORY_BATCH,
)
def process_batch_odd(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process ODD-numbered batches using anthropic-batch1 key.
    EXTRACTED from modal_backend.py process_batch_odd.
    """
    return _process_batch_impl(batch_data, key_label="BATCH1")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(MODAL_SECRET_BATCH2)],
    timeout=MODAL_TIMEOUT_BATCH,
    retries=3,
    memory=MODAL_MEMORY_BATCH,
)
def process_batch_even(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process EVEN-numbered batches using anthropic-batch2 key.
    EXTRACTED from modal_backend.py process_batch_even.
    """
    return _process_batch_impl(batch_data, key_label="BATCH2")


def _process_batch_impl(batch_data: Dict[str, Any], key_label: str = "") -> Dict[str, Any]:
    """
    Core batch processing implementation — shared by odd/even.
    EXTRACTED from modal_backend.py (the duplicated logic in process_batch_odd/even).
    """
    import os
    import json
    import re
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"❌ ANTHROPIC_API_KEY not found [{key_label}]!")
        return {
            "success": False,
            "batch_index": batch_data.get("batch_index", 0),
            "error": "API key not configured",
            "data": {"food_items": [], "drinks": [], "aspects": []},
        }

    reviews = batch_data["reviews"]
    restaurant_name = batch_data["restaurant_name"]
    batch_index = batch_data["batch_index"]
    start_index = batch_data["start_index"]

    print(f"🔄 [{key_label}] Processing batch {batch_index} ({len(reviews)} reviews)...")

    client = Anthropic(api_key=api_key)

    # Build extraction prompt (inline to avoid cross-module import in Modal)
    SENTIMENT_THRESHOLD_POSITIVE = 0.6
    SENTIMENT_THRESHOLD_NEGATIVE = 0.0

    numbered_reviews = [f"[Review {i}]: {review}" for i, review in enumerate(reviews)]
    reviews_text = "\n\n".join(numbered_reviews)

    prompt = f"""You are analyzing customer reviews for {restaurant_name}. Extract BOTH menu items AND aspects in ONE PASS.

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

Extract everything:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(result_text)

        # Map review indices back to full text
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

        fc = len(data.get("food_items", []))
        dc = len(data.get("drinks", []))
        ac = len(data.get("aspects", []))
        print(f"✅ Batch {batch_index}: {fc} food, {dc} drinks, {ac} aspects")
        return {"success": True, "batch_index": batch_index, "data": data}

    except json.JSONDecodeError as e:
        print(f"⚠️ Batch {batch_index} JSON error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}
    except Exception as e:
        print(f"❌ Batch {batch_index} error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}
