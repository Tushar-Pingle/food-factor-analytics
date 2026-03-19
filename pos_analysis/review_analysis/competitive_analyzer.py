"""
Competitive Analyzer — NEW for Food Factor pipeline.

Takes analysis results from the main restaurant and 1-5 competitors,
then produces a structured comparison:
- Rating comparison
- Sentiment comparison
- Category-level benchmarking
- Strengths/weaknesses relative to competitors
"""

import json
import re
from typing import Dict, Any, List

from ..config import (
    CLAUDE_MODEL,
    EXTRACTION_MAX_TOKENS,
    INSIGHTS_TEMPERATURE,
)


def build_comparison(
    main_result: Dict[str, Any],
    competitor_results: List[Dict[str, Any]],
    api_key: str,
) -> Dict[str, Any]:
    """
    Generate competitive comparison analysis.

    Args:
        main_result: Full pipeline result for the primary restaurant
        competitor_results: List of pipeline results for competitors
        api_key: Anthropic API key

    Returns:
        Structured comparison dict
    """
    from anthropic import Anthropic

    if not competitor_results:
        return {"comparison": {}, "error": "No competitor data available"}

    main_name = main_result.get("restaurant_name", "Main Restaurant")

    # Build comparison data
    comparison_input = _build_comparison_input(main_result, competitor_results)

    prompt = f"""You are a restaurant industry analyst comparing {main_name} against its competitors.

{comparison_input}

Produce a competitive analysis with:
1. **overall_ranking**: Rank all restaurants by overall performance
2. **rating_comparison**: Average rating per restaurant
3. **sentiment_comparison**: Average sentiment per restaurant
4. **category_benchmarks**: For key categories (food quality, service, ambiance, value), show how the main restaurant compares
5. **competitive_advantages**: What {main_name} does better than competitors
6. **competitive_gaps**: Where competitors outperform {main_name}
7. **strategic_recommendations**: 3 specific actions {main_name} should take based on competitive positioning

OUTPUT (JSON):
{{
  "overall_ranking": [
    {{"rank": 1, "restaurant": "name", "score": 8.5, "rationale": "..."}}
  ],
  "rating_comparison": [
    {{"restaurant": "name", "avg_rating": 4.2, "review_count": 150}}
  ],
  "sentiment_comparison": [
    {{"restaurant": "name", "avg_sentiment": 0.65, "positive_pct": 72}}
  ],
  "category_benchmarks": [
    {{
      "category": "food quality",
      "main_score": 0.82,
      "competitor_avg": 0.75,
      "best_performer": "competitor name",
      "best_score": 0.88
    }}
  ],
  "competitive_advantages": ["advantage 1", "advantage 2"],
  "competitive_gaps": ["gap 1", "gap 2"],
  "strategic_recommendations": [
    {{"priority": "high", "action": "...", "competitor_evidence": "..."}}
  ]
}}

CRITICAL: Output ONLY valid JSON."""

    print(f"🏆 Running competitive analysis: {main_name} vs {len(competitor_results)} competitors...")

    client = Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=EXTRACTION_MAX_TOKENS,
            temperature=INSIGHTS_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()

        match = re.search(r"\{[\s\S]*\}", result_text)
        if match:
            comparison = json.loads(match.group())
            print(f"✅ Competitive analysis complete")
            return {"comparison": comparison, "main_restaurant": main_name}
        else:
            print("⚠️ No JSON in competitive analysis response")
            return {"comparison": {}, "error": "Failed to parse comparison"}

    except Exception as e:
        print(f"❌ Competitive analysis error: {e}")
        return {"comparison": {}, "error": str(e)}


def _build_comparison_input(
    main_result: Dict[str, Any],
    competitor_results: List[Dict[str, Any]],
) -> str:
    """Build text summary of all restaurants for comparison."""
    sections = []

    # Main restaurant
    sections.append(_summarize_restaurant(main_result, is_main=True))

    # Competitors
    for comp in competitor_results:
        sections.append(_summarize_restaurant(comp, is_main=False))

    return "\n\n".join(sections)


def _summarize_restaurant(result: Dict[str, Any], is_main: bool = False) -> str:
    """Summarize a single restaurant's results for the comparison prompt."""
    name = result.get("restaurant_name", "Unknown")
    label = f"[MAIN] {name}" if is_main else f"[COMPETITOR] {name}"

    stats = result.get("stats", {})
    trend_stats = result.get("trend_stats", {})

    lines = [f"=== {label} ==="]
    lines.append(f"Total reviews: {stats.get('total_reviews', 'N/A')}")
    lines.append(f"Avg rating: {trend_stats.get('avg_rating', 'N/A')}")
    lines.append(f"Avg sentiment: {trend_stats.get('avg_sentiment', 'N/A')}")
    lines.append(f"Positive %: {trend_stats.get('positive_pct', 'N/A')}")

    # Top food items
    food_items = result.get("menu_analysis", {}).get("food_items", [])[:5]
    if food_items:
        lines.append("Top food items:")
        for item in food_items:
            lines.append(f"  - {item.get('name', '?')}: sentiment {item.get('sentiment', 0):+.2f}, {item.get('mention_count', 0)} mentions")

    # Top aspects
    aspects = result.get("aspect_analysis", {}).get("aspects", [])[:5]
    if aspects:
        lines.append("Top aspects:")
        for a in aspects:
            lines.append(f"  - {a.get('name', '?')}: sentiment {a.get('sentiment', 0):+.2f}, {a.get('mention_count', 0)} mentions")

    # Insights summary
    insights = result.get("insights", {})
    for role in ("chef", "manager"):
        role_data = insights.get(role, {})
        summary = role_data.get("summary", "")
        if summary:
            lines.append(f"{role.title()} summary: {summary}")

    return "\n".join(lines)
