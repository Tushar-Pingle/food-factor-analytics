"""
Insights Generator — EXTRACTED from modal_backend.py

Contains:
- Chef insights generation (food/kitchen focus)
- Manager insights generation (service/operations focus)
- Fallback insights
- The exact prompts and retry logic from the original
"""

import json
import re
import time as time_module
from typing import Dict, Any, List

from ..config import (
    SENTIMENT_THRESHOLD_POSITIVE,
    SENTIMENT_THRESHOLD_NEGATIVE,
    CLAUDE_MODEL,
    INSIGHTS_MAX_TOKENS,
    INSIGHTS_TEMPERATURE,
    MAX_RETRIES,
    RETRY_BACKOFF,
)


def _build_data_summary(analysis_data: Dict[str, Any], role: str) -> str:
    """
    Build the menu + aspect summary text for insight prompts.
    EXTRACTED from modal_backend.py generate_chef_insights/generate_manager_insights.
    """
    menu_items = analysis_data.get("menu_analysis", {}).get("food_items", [])[:20]
    drinks = analysis_data.get("menu_analysis", {}).get("drinks", [])[:10]
    aspects = analysis_data.get("aspect_analysis", {}).get("aspects", [])[:20]

    def indicator(s):
        if s >= SENTIMENT_THRESHOLD_POSITIVE:
            return "[+]"
        elif s >= SENTIMENT_THRESHOLD_NEGATIVE:
            return "[~]"
        else:
            return "[-]"

    menu_lines = ["TOP MENU ITEMS:"]
    for item in menu_items:
        s = item.get("sentiment", 0)
        menu_lines.append(
            f"  {indicator(s)} {item.get('name', '?')}: sentiment {s:+.2f}, {item.get('mention_count', 0)} mentions"
        )

    aspect_lines = ["TOP ASPECTS:"]
    for a in aspects:
        s = a.get("sentiment", 0)
        aspect_lines.append(
            f"  {indicator(s)} {a.get('name', '?')}: sentiment {s:+.2f}, {a.get('mention_count', 0)} mentions"
        )

    return "\n".join(menu_lines) + "\n\n" + "\n".join(aspect_lines)


def _build_insights_prompt(
    data_summary: str,
    restaurant_name: str,
    role: str,
    focus: str,
    topic_filter: str,
) -> str:
    """Build the insights prompt. EXTRACTED from modal_backend.py."""
    return f"""You are an expert restaurant consultant analyzing feedback for {restaurant_name}.

{data_summary}

SENTIMENT SCALE:
- POSITIVE (>= {SENTIMENT_THRESHOLD_POSITIVE}): Highlight as STRENGTH
- NEUTRAL ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}): Room for improvement
- NEGATIVE (< {SENTIMENT_THRESHOLD_NEGATIVE}): Flag as CONCERN

YOUR TASK: Generate insights for the {role.upper()}.
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


def _fallback_insights(role: str) -> Dict[str, Any]:
    """Fallback insights if generation fails. EXTRACTED from modal_backend.py."""
    return {
        "summary": f"Analysis complete. See data for {role} insights.",
        "strengths": ["Data available in charts"],
        "concerns": ["Review individual items for details"],
        "recommendations": [
            {"priority": "medium", "action": "Review data", "reason": "Auto-generated", "evidence": "N/A"}
        ],
    }


def generate_insights(
    analysis_data: Dict[str, Any],
    restaurant_name: str,
    role: str,
    api_key: str,
) -> Dict[str, Any]:
    """
    Generate insights for a given role (chef or manager).
    EXTRACTED from modal_backend.py generate_chef_insights/generate_manager_insights.

    Args:
        analysis_data: {"menu_analysis": {"food_items": [...], "drinks": [...]}, "aspect_analysis": {"aspects": [...]}}
        restaurant_name: Name of the restaurant
        role: "chef" or "manager"
        api_key: Anthropic API key

    Returns:
        {"role": role, "insights": {...}}
    """
    from anthropic import Anthropic

    print(f"🧠 Generating {role} insights...")

    if not api_key:
        print(f"❌ No API key for {role} insights!")
        return {"role": role, "insights": _fallback_insights(role)}

    client = Anthropic(api_key=api_key)
    data_summary = _build_data_summary(analysis_data, role)

    if role == "chef":
        focus = "Focus on: Food quality, menu items, ingredients, presentation, portions, consistency"
        topic_filter = "ONLY on food/kitchen topics"
    else:
        focus = "Focus on: Service, staff, wait times, ambience, value, cleanliness"
        topic_filter = "ONLY on operations/service topics"

    prompt = _build_insights_prompt(data_summary, restaurant_name, role, focus, topic_filter)

    for attempt in range(MAX_RETRIES):
        try:
            print(f"🔄 Calling API for {role} insights (attempt {attempt + 1}/{MAX_RETRIES})...")
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=INSIGHTS_MAX_TOKENS,
                temperature=INSIGHTS_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = response.content[0].text.strip()
            result_text = result_text.replace("```json", "").replace("```", "").strip()

            match = re.search(r"\{[\s\S]*\}", result_text)
            if match:
                try:
                    insights = json.loads(match.group())
                    if "summary" in insights and "strengths" in insights:
                        print(f"✅ {role.title()} insights generated successfully")
                        return {"role": role, "insights": insights}
                    else:
                        print(f"⚠️ {role} insights missing required fields")
                        return {"role": role, "insights": _fallback_insights(role)}
                except json.JSONDecodeError:
                    return {"role": role, "insights": _fallback_insights(role)}
            else:
                return {"role": role, "insights": _fallback_insights(role)}

        except Exception as e:
            error_str = str(e)
            if any(x in error_str.lower() for x in ["529", "overloaded", "429", "rate"]):
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * RETRY_BACKOFF
                    print(f"⚠️ API overloaded for {role}, waiting {wait_time}s...")
                    time_module.sleep(wait_time)
                    continue
            print(f"❌ Error generating {role} insights: {e}")
            return {"role": role, "insights": _fallback_insights(role)}

    return {"role": role, "insights": _fallback_insights(role)}
