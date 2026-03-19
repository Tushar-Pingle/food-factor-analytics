"""
pos_analysis.shared.menu_engineering
======================================
POS-agnostic menu engineering analysis.

Classifies menu items into the BCG-style restaurant matrix:
    High Popularity + High Margin  → Star        (protect & promote)
    High Popularity + Low Margin   → Plowhorse   (re-engineer cost)
    Low Popularity  + High Margin  → Puzzle      (boost visibility)
    Low Popularity  + Low Margin   → Dog         (remove or redesign)

Shared by all POS pipelines (Square, TouchBistro, Lightspeed).
Each POS module's ingest.py is responsible for producing a DataFrame with
the required columns; this module operates on the standardized output.

Required columns in item_totals DataFrame:
    Menu_Item, Menu_Category, Sales_Category, Quantity_Sold,
    Gross_Sales, Net_Sales, Item_Cost, Total_Cost,
    food_cost_pct (float 0-1), contribution_margin, total_contribution_margin

Required columns in detailed_sales DataFrame (for modifier_analysis only):
    Bill_Number, is_void, is_return, Modifiers, Modifier_Amount
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Defaults — override via function parameters per-client
DEFAULT_POPULARITY_INDEX: float = 0.70
DEFAULT_FOOD_COST_BENCHMARK: Tuple[float, float] = (28.0, 35.0)


# ──────────────────────────────────────────────
# MENU ENGINEERING MATRIX
# ──────────────────────────────────────────────

def classify_menu_items(
    item_totals: pd.DataFrame,
    popularity_index: float = DEFAULT_POPULARITY_INDEX,
) -> pd.DataFrame:
    """
    Classify each menu item into the 4-quadrant matrix.

    Classification logic:
        - Popularity threshold: popularity_index × mean quantity sold
        - Profitability threshold: mean contribution margin across all items

    Args:
        item_totals: DataFrame with per-item aggregated sales and cost data.
        popularity_index: Fraction of average quantity used as popularity
                          threshold (default 0.70 = 70% of average).

    Returns:
        DataFrame with added columns: popularity_class, profitability_class,
        quadrant, pct_of_total_sales, pct_of_total_quantity.
    """
    df = item_totals[item_totals["Quantity_Sold"] > 0].copy()

    avg_quantity = df["Quantity_Sold"].mean()
    popularity_threshold = avg_quantity * popularity_index
    avg_margin = df["contribution_margin"].mean()

    logger.info(
        f"Menu engineering thresholds — "
        f"Popularity: {popularity_threshold:.0f} units "
        f"(avg={avg_quantity:.0f} × {popularity_index}), "
        f"Margin: ${avg_margin:.2f}"
    )

    df["popularity_class"] = np.where(
        df["Quantity_Sold"] >= popularity_threshold, "High", "Low"
    )
    df["profitability_class"] = np.where(
        df["contribution_margin"] >= avg_margin, "High", "Low"
    )

    conditions = [
        (df["popularity_class"] == "High") & (df["profitability_class"] == "High"),
        (df["popularity_class"] == "High") & (df["profitability_class"] == "Low"),
        (df["popularity_class"] == "Low")  & (df["profitability_class"] == "High"),
        (df["popularity_class"] == "Low")  & (df["profitability_class"] == "Low"),
    ]
    labels = ["Star", "Plowhorse", "Puzzle", "Dog"]
    df["quadrant"] = np.select(conditions, labels, default="Unclassified")

    total_net = df["Net_Sales"].sum()
    total_qty = df["Quantity_Sold"].sum()
    df["pct_of_total_sales"] = (df["Net_Sales"] / total_net * 100).round(1)
    df["pct_of_total_quantity"] = (df["Quantity_Sold"] / total_qty * 100).round(1)

    quadrant_order = {"Star": 0, "Plowhorse": 1, "Puzzle": 2, "Dog": 3}
    df["_sort"] = df["quadrant"].map(quadrant_order)
    df = df.sort_values(["_sort", "Net_Sales"], ascending=[True, False])
    df = df.drop(columns=["_sort"]).reset_index(drop=True)

    for q in labels:
        count = (df["quadrant"] == q).sum()
        rev = df.loc[df["quadrant"] == q, "Net_Sales"].sum()
        logger.info(f"  {q}: {count} items, ${rev:,.0f} revenue")

    return df


# ──────────────────────────────────────────────
# QUADRANT SUMMARY
# ──────────────────────────────────────────────

def quadrant_summary(classified: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate stats by quadrant for the executive summary.

    Returns:
        DataFrame with quadrant, item_count, total_revenue,
        pct_revenue, avg_margin, avg_food_cost.
    """
    summary = classified.groupby("quadrant").agg(
        item_count=("Menu_Item", "count"),
        total_revenue=("Net_Sales", "sum"),
        avg_margin=("contribution_margin", "mean"),
        avg_food_cost=("food_cost_pct", "mean"),
        total_quantity=("Quantity_Sold", "sum"),
    ).reset_index()

    total_rev = summary["total_revenue"].sum()
    summary["pct_revenue"] = (summary["total_revenue"] / total_rev * 100).round(1)
    summary["avg_margin"] = summary["avg_margin"].round(2)
    summary["avg_food_cost"] = (summary["avg_food_cost"] * 100).round(1)

    order = {"Star": 0, "Plowhorse": 1, "Puzzle": 2, "Dog": 3}
    summary["_sort"] = summary["quadrant"].map(order)
    summary = summary.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    return summary


# ──────────────────────────────────────────────
# FOOD COST ANALYSIS
# ──────────────────────────────────────────────

def food_cost_analysis(
    item_totals: pd.DataFrame,
    benchmark_range: Tuple[float, float] = DEFAULT_FOOD_COST_BENCHMARK,
) -> Dict[str, Any]:
    """
    Food cost metrics: overall weighted average, by category, flagged items.

    Args:
        item_totals: Per-item DataFrame with cost data.
        benchmark_range: (low, high) acceptable food cost % range.

    Returns:
        Dict with overall_food_cost_pct, by_category,
        high_cost_items, low_cost_items, benchmark_range.
    """
    df = item_totals[item_totals["Quantity_Sold"] > 0].copy()

    total_cost = df["Total_Cost"].sum()
    total_net = df["Net_Sales"].sum()
    overall_pct = (total_cost / total_net * 100) if total_net > 0 else 0

    by_cat = df.groupby("Menu_Category").agg(
        total_cost=("Total_Cost", "sum"),
        net_sales=("Net_Sales", "sum"),
        item_count=("Menu_Item", "count"),
    ).reset_index()
    by_cat["food_cost_pct"] = (
        by_cat["total_cost"] / by_cat["net_sales"] * 100
    ).round(1)
    by_cat = by_cat.sort_values("food_cost_pct", ascending=False).reset_index(drop=True)

    low_bench, high_bench = benchmark_range
    df["food_cost_pct_display"] = (df["food_cost_pct"] * 100).round(1)

    high_cost = df[df["food_cost_pct_display"] > high_bench].sort_values(
        "food_cost_pct_display", ascending=False
    ).reset_index(drop=True)

    low_cost = df[df["food_cost_pct_display"] < low_bench].sort_values(
        "food_cost_pct_display"
    ).reset_index(drop=True)

    return {
        "overall_food_cost_pct": round(overall_pct, 1),
        "by_category":          by_cat,
        "high_cost_items":      high_cost,
        "low_cost_items":       low_cost,
        "benchmark_range":      benchmark_range,
    }


# ──────────────────────────────────────────────
# PRICING GAP ANALYSIS
# ──────────────────────────────────────────────

def pricing_gap_analysis(
    item_totals: pd.DataFrame,
    popularity_index: float = DEFAULT_POPULARITY_INDEX,
) -> pd.DataFrame:
    """
    Identify pricing opportunities per item.

    Args:
        item_totals: Per-item DataFrame.
        popularity_index: Popularity threshold fraction.

    Returns:
        DataFrame of actionable items with price_action recommendation.
    """
    df = item_totals[item_totals["Quantity_Sold"] > 0].copy()

    avg_qty = df["Quantity_Sold"].mean()
    avg_margin = df["contribution_margin"].mean()

    df["unit_price"] = (df["Net_Sales"] / df["Quantity_Sold"]).round(2)
    df["price_action"] = "Hold"

    # Price increase candidates: high demand, below-avg margin
    df.loc[
        (df["Quantity_Sold"] >= avg_qty * popularity_index)
        & (df["contribution_margin"] < avg_margin),
        "price_action",
    ] = "Consider price increase"

    # Promo candidates: low demand, high margin
    df.loc[
        (df["Quantity_Sold"] < avg_qty * popularity_index)
        & (df["contribution_margin"] >= avg_margin),
        "price_action",
    ] = "Promote or reposition"

    # Remove candidates: very low demand, very low margin
    df.loc[
        (df["Quantity_Sold"] < avg_qty * popularity_index * 0.5)
        & (df["contribution_margin"] < avg_margin * 0.5),
        "price_action",
    ] = "Remove or redesign"

    actionable = df[df["price_action"] != "Hold"].sort_values(
        "Net_Sales", ascending=False
    ).reset_index(drop=True)

    return actionable


# ──────────────────────────────────────────────
# MODIFIER / ADD-ON ANALYSIS
# ──────────────────────────────────────────────

def modifier_analysis(detailed_sales: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze modifier usage and revenue from add-ons.

    Args:
        detailed_sales: Line-item DataFrame with Modifiers and Modifier_Amount.

    Returns:
        DataFrame with modifier name, frequency, total upcharge revenue.
    """
    valid = detailed_sales[
        (~detailed_sales["is_void"])
        & (~detailed_sales["is_return"])
        & (detailed_sales["Modifiers"] != "")
    ].copy()

    if valid.empty:
        return pd.DataFrame(columns=["modifier", "count", "total_revenue"])

    mods = valid.groupby("Modifiers").agg(
        count=("Bill_Number", "count"),
        total_revenue=("Modifier_Amount", "sum"),
    ).reset_index()
    mods = mods.rename(columns={"Modifiers": "modifier"})
    return mods.sort_values("total_revenue", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# CATEGORY MARGIN PERFORMANCE
# ──────────────────────────────────────────────

def category_margin_performance(item_totals: pd.DataFrame) -> pd.DataFrame:
    """
    Contribution margin and food cost aggregated by Sales_Category
    (Food / Alcohol / Non-Alcoholic).
    """
    df = item_totals[item_totals["Quantity_Sold"] > 0].copy()

    cat = df.groupby("Sales_Category").agg(
        total_net=("Net_Sales", "sum"),
        total_cost=("Total_Cost", "sum"),
        total_cm=("total_contribution_margin", "sum"),
        item_count=("Menu_Item", "count"),
        total_quantity=("Quantity_Sold", "sum"),
    ).reset_index()

    cat["food_cost_pct"] = (cat["total_cost"] / cat["total_net"] * 100).round(1)
    cat["avg_cm_per_unit"] = (cat["total_cm"] / cat["total_quantity"]).round(2)
    cat["pct_total_margin"] = (cat["total_cm"] / cat["total_cm"].sum() * 100).round(1)

    return cat.sort_values("total_cm", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────

def run_menu_engineering(
    item_totals: pd.DataFrame,
    detailed_sales: pd.DataFrame,
    popularity_index: float = DEFAULT_POPULARITY_INDEX,
    food_cost_benchmark: Tuple[float, float] = DEFAULT_FOOD_COST_BENCHMARK,
) -> Dict[str, Any]:
    """
    Execute all menu engineering analysis.

    Args:
        item_totals:         Per-item aggregated DataFrame (TouchBistro_02 or equiv).
        detailed_sales:      Line-item DataFrame (TouchBistro_01 or equiv).
        popularity_index:    Popularity threshold fraction (default 0.70).
        food_cost_benchmark: Acceptable food cost % range (default 28–35%).

    Returns:
        Dict with classified_items, quadrant_summary, food_cost,
        pricing_gaps, modifier_analysis, category_margins.
    """
    classified = classify_menu_items(item_totals, popularity_index)

    results = {
        "classified_items":     classified,
        "quadrant_summary":     quadrant_summary(classified),
        "food_cost":            food_cost_analysis(item_totals, food_cost_benchmark),
        "pricing_gaps":         pricing_gap_analysis(item_totals, popularity_index),
        "modifier_analysis":    modifier_analysis(detailed_sales),
        "category_margins":     category_margin_performance(item_totals),
    }

    logger.info("Menu engineering analysis complete")
    return results
