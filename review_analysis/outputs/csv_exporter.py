"""
CSV Exporter — Flat CSV outputs for ad-hoc analysis.

Produces separate CSV files for food items, drinks, aspects, trends, and categories.
"""

import csv
import os
from typing import Dict, Any, List, Optional


def export_all_csvs(
    restaurant_name: str,
    food_items: List[Dict],
    drinks: List[Dict],
    aspects: List[Dict],
    trend_data: List[Dict],
    category_analysis: Optional[List[Dict]] = None,
    menu_item_analysis: Optional[Dict[str, Any]] = None,
    output_dir: str = "output",
) -> List[str]:
    """
    Export all analysis data as CSV files.

    Returns: list of file paths created.
    """
    os.makedirs(output_dir, exist_ok=True)
    safe_name = restaurant_name.lower().replace(" ", "_").replace("'", "")
    paths = []

    # 1. Food items
    path = _write_items_csv(
        food_items,
        os.path.join(output_dir, f"{safe_name}_food_items.csv"),
        ["name", "mention_count", "sentiment", "category", "summary"],
    )
    paths.append(path)

    # 2. Drinks
    path = _write_items_csv(
        drinks,
        os.path.join(output_dir, f"{safe_name}_drinks.csv"),
        ["name", "mention_count", "sentiment", "category", "summary"],
    )
    paths.append(path)

    # 3. Aspects
    path = _write_items_csv(
        aspects,
        os.path.join(output_dir, f"{safe_name}_aspects.csv"),
        ["name", "mention_count", "sentiment", "description", "summary"],
    )
    paths.append(path)

    # 4. Trend data
    path = os.path.join(output_dir, f"{safe_name}_trend_data.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "rating", "sentiment"])
        writer.writeheader()
        for row in trend_data:
            writer.writerow(row)
    paths.append(path)
    print(f"📄 Trend data: {path} ({len(trend_data)} rows)")

    # 5. Category analysis (if available)
    if category_analysis:
        path = os.path.join(output_dir, f"{safe_name}_categories.csv")
        fieldnames = ["name", "mention_count", "avg_sentiment", "positive_themes", "negative_themes", "representative_excerpt"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for cat in category_analysis:
                row = dict(cat)
                # Flatten lists to strings
                row["positive_themes"] = "; ".join(row.get("positive_themes", []))
                row["negative_themes"] = "; ".join(row.get("negative_themes", []))
                writer.writerow(row)
        paths.append(path)
        print(f"📄 Categories: {path} ({len(category_analysis)} rows)")

    # 6. Menu item analysis (if available)
    if menu_item_analysis:
        for key in ("food_analysis", "drinks_analysis"):
            items = menu_item_analysis.get(key, [])
            if items:
                path = os.path.join(output_dir, f"{safe_name}_{key}.csv")
                fieldnames = ["name", "mention_count", "avg_sentiment", "key_praise", "key_criticism", "recommendation", "menu_engineering_tag"]
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                    for item in items:
                        writer.writerow(item)
                paths.append(path)
                print(f"📄 {key}: {path} ({len(items)} rows)")

    print(f"📦 Exported {len(paths)} CSV files to {output_dir}/")
    return paths


def _write_items_csv(
    items: List[Dict],
    filepath: str,
    fieldnames: List[str],
) -> str:
    """Write a list of item dicts to CSV, ignoring extra fields."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow(item)
    print(f"📄 {os.path.basename(filepath)}: {len(items)} items")
    return filepath
