"""
pos_analysis.shared.menu_engineering — Menu Engineering Analysis

BCG-style menu matrix (Stars / Plow Horses / Puzzles / Dogs),
contribution margin analysis, food cost %, modifier performance,
and pricing gap identification.

POS-agnostic: operates on standardized DataFrames with columns
Product_ID, Item_Name, Tax_Exclusive_Price, Amount, Category,
and a products catalog with Product_ID, Name, Price, Cost, Category_Name.

Used by all three POS pipelines (Square, TouchBistro, Lightspeed).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import logging

from pos_analysis.shared import BENCHMARKS, MENU_ENGINEERING

logger = logging.getLogger(__name__)


def classify_menu_items(
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the menu engineering matrix.

    Each item is classified into one of four quadrants based on:
      - Popularity (quantity sold vs. median/mean)
      - Profitability (contribution margin vs. median/mean)

    Quadrants:
      - Star:        High popularity + High margin
      - Plow Horse:  High popularity + Low margin
      - Puzzle:      Low popularity + High margin
      - Dog:         Low popularity + Low margin

    Args:
        items:    Line-item sales DataFrame (Receipt_ID, Product_ID, Amount, Tax_Exclusive_Price).
        products: Product catalog DataFrame (Product_ID, Name, Price, Cost, Category_Name,
                  food_cost_pct, contribution_margin).

    Returns:
        DataFrame with one row per menu item including classification.
    """
    merged = items.merge(
        products[["Product_ID", "Name", "Price", "Cost", "Category_Name",
                  "food_cost_pct", "contribution_margin"]],
        on="Product_ID", how="left",
    )

    eng = merged.groupby(["Product_ID", "Name", "Category_Name"]).agg(
        quantity_sold=("Amount", "sum"),
        total_revenue=("Tax_Exclusive_Price", "sum"),
        avg_price=("Tax_Exclusive_Price", "mean"),
        unit_cost=("Cost", "first"),
        unit_margin=("contribution_margin", "first"),
        food_cost_pct=("food_cost_pct", "first"),
    ).reset_index()

    eng["total_margin"] = eng["quantity_sold"] * eng["unit_margin"]
    eng["total_cogs"] = eng["quantity_sold"] * eng["unit_cost"]

    # Popularity & profitability thresholds
    pop_method = MENU_ENGINEERING["popularity_method"]
    margin_method = MENU_ENGINEERING["margin_method"]

    pop_threshold = (
        eng["quantity_sold"].median() if pop_method == "median"
        else eng["quantity_sold"].mean()
    )
    margin_threshold = (
        eng["unit_margin"].median() if margin_method == "median"
        else eng["unit_margin"].mean()
    )

    # Classification
    conditions = [
        (eng["quantity_sold"] >= pop_threshold) & (eng["unit_margin"] >= margin_threshold),
        (eng["quantity_sold"] >= pop_threshold) & (eng["unit_margin"] < margin_threshold),
        (eng["quantity_sold"] < pop_threshold) & (eng["unit_margin"] >= margin_threshold),
        (eng["quantity_sold"] < pop_threshold) & (eng["unit_margin"] < margin_threshold),
    ]
    labels = ["Star", "Plow Horse", "Puzzle", "Dog"]
    eng["classification"] = np.select(conditions, labels, default="Unknown")

    # Menu mix percentage
    eng["menu_mix_pct"] = eng["quantity_sold"] / eng["quantity_sold"].sum()
    eng["revenue_pct"] = eng["total_revenue"] / eng["total_revenue"].sum()
    eng["margin_pct_of_total"] = eng["total_margin"] / eng["total_margin"].sum()

    # Metadata for chart thresholds
    eng.attrs["pop_threshold"] = pop_threshold
    eng.attrs["margin_threshold"] = margin_threshold

    logger.info(
        f"Menu classification: "
        f"Stars={len(eng[eng['classification']=='Star'])}, "
        f"Plow Horses={len(eng[eng['classification']=='Plow Horse'])}, "
        f"Puzzles={len(eng[eng['classification']=='Puzzle'])}, "
        f"Dogs={len(eng[eng['classification']=='Dog'])}"
    )
    return eng


def analyze_food_cost(
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Food cost analysis by item and category.

    Returns dict with:
      - overall_food_cost_pct
      - by_category: DataFrame of food cost % per category
      - high_cost_items: items above the alarm threshold
      - low_cost_items: items with suspiciously low cost (data quality flag)
    """
    merged = items.merge(
        products[["Product_ID", "Cost", "food_cost_pct", "Category_Name"]],
        on="Product_ID", how="left",
    )

    total_revenue = merged["Tax_Exclusive_Price"].sum()
    merged["line_cogs"] = merged["Cost"] * merged["Amount"]
    total_cogs = merged["line_cogs"].sum()
    overall_pct = total_cogs / max(total_revenue, 1)

    # By category
    cat_cost = merged.groupby("Category_Name").agg(
        revenue=("Tax_Exclusive_Price", "sum"),
        cogs=("line_cogs", "sum"),
    ).reset_index()
    cat_cost["food_cost_pct"] = cat_cost["cogs"] / cat_cost["revenue"].clip(lower=0.01)
    cat_cost = cat_cost.sort_values("food_cost_pct", ascending=False)

    # Flag items above threshold
    item_cost = merged.groupby(["Product_ID", "Category_Name"]).agg(
        item_name=("Item_Name", "first"),
        avg_food_cost_pct=("food_cost_pct", "first"),
        quantity_sold=("Amount", "sum"),
    ).reset_index()

    high = item_cost[item_cost["avg_food_cost_pct"] > BENCHMARKS["food_cost_pct_max"]]
    low = item_cost[item_cost["avg_food_cost_pct"] < 0.10]

    return {
        "overall_food_cost_pct": round(overall_pct, 4),
        "benchmark":             BENCHMARKS["food_cost_pct"],
        "alarm_threshold":       BENCHMARKS["food_cost_pct_max"],
        "by_category":           cat_cost,
        "high_cost_items":       high.sort_values("avg_food_cost_pct", ascending=False),
        "low_cost_items":        low,
    }


def analyze_pricing_gaps(products: pd.DataFrame) -> pd.DataFrame:
    """
    Identify pricing inconsistencies and opportunities.

    Flags:
      - Items priced below category average
      - Items where delivery markup is missing or insufficient
      - Items with unusually high or low margins within category

    Args:
        products: Product catalog with Price, Cost, Delivery_Price, Category_Name,
                  food_cost_pct, contribution_margin columns.

    Returns:
        Enriched products DataFrame with gap flags.
    """
    gaps = products.copy()

    cat_avg = products.groupby("Category_Name").agg(
        cat_avg_price=("Price", "mean"),
        cat_avg_cost=("Cost", "mean"),
        cat_avg_margin=("contribution_margin", "mean"),
        cat_avg_food_cost=("food_cost_pct", "mean"),
    ).reset_index()

    gaps = gaps.merge(cat_avg, on="Category_Name", how="left")

    gaps["below_cat_avg_price"] = gaps["Price"] < gaps["cat_avg_price"] * 0.85
    gaps["above_cat_avg_cost"] = gaps["food_cost_pct"] > gaps["cat_avg_food_cost"] * 1.20
    gaps["missing_delivery_price"] = (gaps["Delivery_Price"] == 0) | gaps["Delivery_Price"].isna()
    gaps["delivery_markup_pct"] = np.where(
        (gaps["Price"] > 0) & (gaps["Delivery_Price"] > 0),
        (gaps["Delivery_Price"] - gaps["Price"]) / gaps["Price"],
        np.nan,
    )
    gaps["low_delivery_markup"] = gaps["delivery_markup_pct"].fillna(1) < 0.10
    gaps["margin_per_dollar"] = gaps["contribution_margin"] / gaps["Price"].clip(lower=0.01)

    return gaps


def analyze_modifier_performance(
    modifiers: pd.DataFrame,
    items: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Modifier adoption and revenue analysis.

    Args:
        modifiers: Modifier applications DataFrame (mod_name, mod_price_excl, mod_id).
        items:     Line-item sales DataFrame.

    Returns:
        Dict with modifier_summary, attach_rate, total_modifier_revenue.
    """
    total_items_sold = len(items)
    total_mods = len(modifiers)

    mod_summary = modifiers.groupby("mod_name").agg(
        times_applied=("mod_id", "count"),
        total_revenue=("mod_price_excl", "sum"),
        avg_price=("mod_price_excl", "mean"),
    ).sort_values("times_applied", ascending=False).reset_index()

    mod_summary["attach_rate"] = mod_summary["times_applied"] / max(total_items_sold, 1)

    parent_items = modifiers.groupby("item_name").agg(
        modifier_count=("mod_id", "count"),
    ).sort_values("modifier_count", ascending=False).head(10)

    return {
        "modifier_summary":        mod_summary,
        "overall_attach_rate":     round(total_mods / max(total_items_sold, 1), 4),
        "total_modifier_revenue":  round(modifiers["mod_price_excl"].sum(), 2),
        "top_modified_items":      parent_items,
        "total_modifier_applications": total_mods,
    }


def analyze_category_contribution(
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """
    Category-level contribution margin analysis for strategic decisions.

    Returns DataFrame with revenue contribution, margin contribution,
    and category efficiency metrics.
    """
    merged = items.merge(
        products[["Product_ID", "Cost", "contribution_margin", "Category_Name"]],
        on="Product_ID", how="left",
    )

    merged["line_margin"] = merged["contribution_margin"] * merged["Amount"]
    merged["line_cogs"] = merged["Cost"] * merged["Amount"]

    cat = merged.groupby("Category_Name").agg(
        total_revenue=("Tax_Exclusive_Price", "sum"),
        total_margin=("line_margin", "sum"),
        total_cogs=("line_cogs", "sum"),
        items_sold=("Amount", "sum"),
        unique_items=("Product_ID", "nunique"),
    ).reset_index()

    cat["avg_margin_per_item"] = cat["total_margin"] / cat["items_sold"].clip(lower=1)
    cat["margin_pct"] = cat["total_margin"] / cat["total_revenue"].clip(lower=0.01)
    cat["revenue_share"] = cat["total_revenue"] / cat["total_revenue"].sum()
    cat["margin_share"] = cat["total_margin"] / cat["total_margin"].sum()
    cat["margin_efficiency"] = cat["margin_share"] / cat["revenue_share"].clip(lower=0.001)

    return cat.sort_values("total_margin", ascending=False)


def run_menu_engineering(
    items: pd.DataFrame,
    products: pd.DataFrame,
    modifiers: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Execute full menu engineering analysis suite.

    Args:
        items:     Line-item sales DataFrame.
        products:  Product catalog DataFrame with COGS.
        modifiers: Modifier applications DataFrame.

    Returns:
        Dict with menu_matrix, food_cost, pricing_gaps, modifier_performance,
        category_contribution, and quadrant_summary.
    """
    logger.info("Running menu engineering analysis...")

    menu_matrix = classify_menu_items(items, products)

    results = {
        "menu_matrix":              menu_matrix,
        "food_cost":                analyze_food_cost(items, products),
        "pricing_gaps":             analyze_pricing_gaps(products),
        "modifier_performance":     analyze_modifier_performance(modifiers, items),
        "category_contribution":    analyze_category_contribution(items, products),
        "quadrant_summary": {
            "stars":        menu_matrix[menu_matrix["classification"] == "Star"]["Name"].tolist(),
            "plow_horses":  menu_matrix[menu_matrix["classification"] == "Plow Horse"]["Name"].tolist(),
            "puzzles":      menu_matrix[menu_matrix["classification"] == "Puzzle"]["Name"].tolist(),
            "dogs":         menu_matrix[menu_matrix["classification"] == "Dog"]["Name"].tolist(),
        },
    }

    logger.info("Menu engineering complete.")
    return results
