"""
JSON Exporter — Structured output for Food Factor report assembly (Prompt 17).

Produces a single comprehensive JSON file containing all pipeline outputs,
structured to be consumed by the report generation prompt.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


def export_full_report_json(
    restaurant_name: str,
    platform: str,
    menu_analysis: Dict[str, Any],
    aspect_analysis: Dict[str, Any],
    insights: Dict[str, Any],
    trend_data: List[Dict],
    trend_stats: Dict[str, Any],
    category_analysis: Optional[List[Dict]] = None,
    menu_item_analysis: Optional[Dict[str, Any]] = None,
    competitive_analysis: Optional[Dict[str, Any]] = None,
    stats: Optional[Dict[str, Any]] = None,
    output_dir: str = "output",
) -> str:
    """
    Export the full pipeline output as a structured JSON file.

    Returns: path to the saved JSON file.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = restaurant_name.lower().replace(" ", "_").replace("'", "")
    filename = f"{safe_name}_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    report = {
        "metadata": {
            "restaurant_name": restaurant_name,
            "generated_at": datetime.now().isoformat(),
            "platform": platform,
            "pipeline_version": "2.0.0",
        },
        "stats": stats or {},
        "trend_stats": trend_stats,
        "menu_analysis": menu_analysis,
        "aspect_analysis": aspect_analysis,
        "insights": insights,
        "trend_data": trend_data,
    }

    # Optional sections
    if category_analysis:
        report["category_analysis"] = category_analysis
    if menu_item_analysis:
        report["menu_item_analysis"] = menu_item_analysis
    if competitive_analysis:
        report["competitive_analysis"] = competitive_analysis

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    size_kb = os.path.getsize(filepath) / 1024
    print(f"💾 Saved report JSON: {filepath} ({size_kb:.1f} KB)")
    return filepath


def export_prompt17_json(
    report_json_path: str,
    output_dir: str = "output",
) -> str:
    """
    Transform the full report JSON into the specific format
    expected by Prompt 17 (Food Factor report assembly prompt).

    This creates a flattened, annotated version optimized for
    the report generation LLM prompt.
    """
    with open(report_json_path, "r") as f:
        report = json.load(f)

    name = report["metadata"]["restaurant_name"]

    # Build Prompt 17 structure
    p17 = {
        "restaurant": name,
        "generated_at": report["metadata"]["generated_at"],
        "executive_summary_inputs": {
            "total_reviews": report.get("stats", {}).get("total_reviews", 0),
            "avg_rating": report.get("trend_stats", {}).get("avg_rating", 0),
            "avg_sentiment": report.get("trend_stats", {}).get("avg_sentiment", 0),
            "positive_pct": report.get("trend_stats", {}).get("positive_pct", 0),
            "negative_pct": report.get("trend_stats", {}).get("negative_pct", 0),
            "top_food_items": [
                {"name": i["name"], "sentiment": i.get("sentiment", 0), "mentions": i.get("mention_count", 0)}
                for i in report.get("menu_analysis", {}).get("food_items", [])[:10]
            ],
            "top_aspects": [
                {"name": a["name"], "sentiment": a.get("sentiment", 0), "mentions": a.get("mention_count", 0)}
                for a in report.get("aspect_analysis", {}).get("aspects", [])[:10]
            ],
        },
        "chef_insights": report.get("insights", {}).get("chef", {}),
        "manager_insights": report.get("insights", {}).get("manager", {}),
        "category_analysis": report.get("category_analysis", []),
        "menu_item_analysis": report.get("menu_item_analysis", {}),
        "competitive_analysis": report.get("competitive_analysis", {}),
        "chart_data": {
            "trend_data": report.get("trend_data", []),
            "food_items": report.get("menu_analysis", {}).get("food_items", [])[:20],
            "drinks": report.get("menu_analysis", {}).get("drinks", [])[:15],
            "aspects": report.get("aspect_analysis", {}).get("aspects", [])[:20],
        },
    }

    safe_name = name.lower().replace(" ", "_").replace("'", "")
    filepath = os.path.join(output_dir, f"{safe_name}_prompt17.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(p17, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 Saved Prompt 17 JSON: {filepath}")
    return filepath
