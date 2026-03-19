"""
Modal Insights Job — Chef, Manager, and Summary generation on Modal.

EXTRACTED from modal_backend.py generate_chef_insights, generate_manager_insights,
generate_all_summaries. Each uses its own Modal secret for rate limit isolation.
"""

import modal
from typing import Dict, Any, List

from ..config import (
    MODAL_TIMEOUT_INSIGHTS,
    MODAL_TIMEOUT_SUMMARIES,
    MODAL_MEMORY_INSIGHTS,
    MODAL_SECRET_CHEF,
    MODAL_SECRET_MANAGER,
    MODAL_SECRET_SUMMARIES,
)

# Re-use app and image from nlp_job
from .nlp_job import app, image


# ============================================================================
# CHEF INSIGHTS
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name(MODAL_SECRET_CHEF)],
    timeout=MODAL_TIMEOUT_INSIGHTS,
    retries=3,
    memory=MODAL_MEMORY_INSIGHTS,
)
def generate_chef_insights_modal(
    analysis_data: Dict[str, Any], restaurant_name: str
) -> Dict[str, Any]:
    """Generate chef insights on Modal using anthropic-chef key."""
    import os
    return _generate_insights_impl(
        analysis_data, restaurant_name, role="chef",
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )


# ============================================================================
# MANAGER INSIGHTS
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name(MODAL_SECRET_MANAGER)],
    timeout=MODAL_TIMEOUT_INSIGHTS,
    retries=3,
    memory=MODAL_MEMORY_INSIGHTS,
)
def generate_manager_insights_modal(
    analysis_data: Dict[str, Any], restaurant_name: str
) -> Dict[str, Any]:
    """Generate manager insights on Modal using anthropic-manager key."""
    import os
    return _generate_insights_impl(
        analysis_data, restaurant_name, role="manager",
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )


# ============================================================================
# SUMMARY GENERATION
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name(MODAL_SECRET_SUMMARIES)],
    timeout=MODAL_TIMEOUT_SUMMARIES,
    memory=MODAL_MEMORY_INSIGHTS,
)
def generate_summaries_modal(
    food_items: List[Dict[str, Any]],
    drinks: List[Dict[str, Any]],
    aspects: List[Dict[str, Any]],
    restaurant_name: str,
) -> Dict[str, Dict[str, str]]:
    """Generate all summaries on Modal using anthropic-summaries key."""
    import os
    import json
    import re
    from anthropic import Anthropic

    SENTIMENT_THRESHOLD_POSITIVE = 0.6
    SENTIMENT_THRESHOLD_NEGATIVE = 0.0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found for summaries!")
        return {"food": {}, "drinks": {}, "aspects": {}}

    client = Anthropic(api_key=api_key)

    food_str = "\n".join(
        [f"- {f.get('name', '?')} (sentiment: {f.get('sentiment', 0):.2f}, mentions: {f.get('mention_count', 0)})" for f in food_items]
    )
    drinks_str = "\n".join(
        [f"- {d.get('name', '?')} (sentiment: {d.get('sentiment', 0):.2f}, mentions: {d.get('mention_count', 0)})" for d in drinks]
    )
    aspects_str = "\n".join(
        [f"- {a.get('name', '?')} (sentiment: {a.get('sentiment', 0):.2f}, mentions: {a.get('mention_count', 0)})" for a in aspects]
    )

    prompt = f"""Generate brief 2-3 sentence summaries for each item at {restaurant_name}.

FOOD ITEMS:
{food_str}

DRINKS:
{drinks_str}

ASPECTS:
{aspects_str}

For each summary:
1. Synthesizes what customers say
2. Reflects the sentiment score (positive if >= {SENTIMENT_THRESHOLD_POSITIVE}, negative if < {SENTIMENT_THRESHOLD_NEGATIVE}, neutral otherwise)
3. Gives actionable insight for restaurant staff

OUTPUT FORMAT (JSON):
{{
  "food": {{
    "item name": "2-3 sentence summary based on reviews..."
  }},
  "drinks": {{
    "drink name": "summary..."
  }},
  "aspects": {{
    "aspect name": "summary..."
  }}
}}

CRITICAL: Output ONLY valid JSON. Generate summaries for ALL items listed above."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{[\s\S]*\}", result_text)
        if match:
            summaries = json.loads(match.group())
            print(f"✅ Summaries: {len(summaries.get('food', {}))} food, {len(summaries.get('drinks', {}))} drinks, {len(summaries.get('aspects', {}))} aspects")
            return summaries
        print("⚠️ No JSON in summary response")
        return {"food": {}, "drinks": {}, "aspects": {}}
    except Exception as e:
        print(f"⚠️ Summary error: {e}")
        return {"food": {}, "drinks": {}, "aspects": {}}


# ============================================================================
# SHARED INSIGHTS IMPLEMENTATION (inline to avoid cross-module issues in Modal)
# ============================================================================

def _generate_insights_impl(
    analysis_data: Dict[str, Any],
    restaurant_name: str,
    role: str,
    api_key: str,
) -> Dict[str, Any]:
    """Core insights generation — used by both chef and manager Modal functions."""
    import json
    import re
    import time as time_module
    from anthropic import Anthropic

    SENTIMENT_THRESHOLD_POSITIVE = 0.6
    SENTIMENT_THRESHOLD_NEGATIVE = 0.0

    if not api_key:
        return {"role": role, "insights": _fallback(role)}

    client = Anthropic(api_key=api_key)

    menu_items = analysis_data.get("menu_analysis", {}).get("food_items", [])[:20]
    aspects = analysis_data.get("aspect_analysis", {}).get("aspects", [])[:20]

    def indicator(s):
        return "[+]" if s >= SENTIMENT_THRESHOLD_POSITIVE else "[~]" if s >= SENTIMENT_THRESHOLD_NEGATIVE else "[-]"

    menu_lines = ["TOP MENU ITEMS:"] + [
        f"  {indicator(i.get('sentiment', 0))} {i.get('name', '?')}: sentiment {i.get('sentiment', 0):+.2f}, {i.get('mention_count', 0)} mentions"
        for i in menu_items
    ]
    aspect_lines = ["TOP ASPECTS:"] + [
        f"  {indicator(a.get('sentiment', 0))} {a.get('name', '?')}: sentiment {a.get('sentiment', 0):+.2f}, {a.get('mention_count', 0)} mentions"
        for a in aspects
    ]

    if role == "chef":
        focus = "Focus on: Food quality, menu items, ingredients, presentation, portions, consistency"
        topic_filter = "ONLY on food/kitchen topics"
        role_title = "HEAD CHEF"
    else:
        focus = "Focus on: Service, staff, wait times, ambience, value, cleanliness"
        topic_filter = "ONLY on operations/service topics"
        role_title = "RESTAURANT MANAGER"

    prompt = f"""You are an expert restaurant consultant analyzing feedback for {restaurant_name}.

{chr(10).join(menu_lines)}

{chr(10).join(aspect_lines)}

SENTIMENT SCALE:
- POSITIVE (>= {SENTIMENT_THRESHOLD_POSITIVE}): Highlight as STRENGTH
- NEUTRAL ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}): Room for improvement
- NEGATIVE (< {SENTIMENT_THRESHOLD_NEGATIVE}): Flag as CONCERN

YOUR TASK: Generate insights for the {role_title}.
{focus}

RULES:
1. Focus {topic_filter}
2. STRENGTHS from items with sentiment >= {SENTIMENT_THRESHOLD_POSITIVE}
3. CONCERNS from items with sentiment < {SENTIMENT_THRESHOLD_NEGATIVE}
4. Output ONLY valid JSON

OUTPUT:
{{
  "summary": "2-3 sentence executive summary",
  "strengths": ["strength 1", "strength 2", "strength 3", "strength 4", "strength 5"],
  "concerns": ["concern 1", "concern 2", "concern 3"],
  "recommendations": [
    {{"priority": "high", "action": "action", "reason": "why", "evidence": "data"}},
    {{"priority": "medium", "action": "action", "reason": "why", "evidence": "data"}},
    {{"priority": "low", "action": "action", "reason": "why", "evidence": "data"}}
  ]
}}

Generate {role} insights:"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}],
            )
            result_text = response.content[0].text.strip()
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            match = re.search(r"\{[\s\S]*\}", result_text)
            if match:
                insights = json.loads(match.group())
                if "summary" in insights and "strengths" in insights:
                    print(f"✅ {role.title()} insights generated")
                    return {"role": role, "insights": insights}
            return {"role": role, "insights": _fallback(role)}
        except Exception as e:
            if any(x in str(e).lower() for x in ["529", "overloaded", "429", "rate"]):
                if attempt < max_retries - 1:
                    time_module.sleep((attempt + 1) * 5)
                    continue
            return {"role": role, "insights": _fallback(role)}

    return {"role": role, "insights": _fallback(role)}


def _fallback(role: str) -> Dict[str, Any]:
    return {
        "summary": f"Analysis complete. See data for {role} insights.",
        "strengths": ["Data available in charts"],
        "concerns": ["Review individual items for details"],
        "recommendations": [{"priority": "medium", "action": "Review data", "reason": "Auto-generated", "evidence": "N/A"}],
    }
