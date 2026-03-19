"""
pos_analysis/shared/menu_engineering.py — Menu Engineering Analysis
====================================================================
POS-agnostic menu engineering using the BCG-style matrix
(Star / Plow Horse / Puzzle / Dog).  Accepts a normalized item-level
DataFrame from *any* POS system.

Required DataFrame columns:
    item_name, category, quantity, net_sales, cost,
    contribution_margin, modifiers, modifier_amount

Usage::

    from pos_analysis.shared.menu_engineering import MenuEngineeringAnalyzer

    analyzer = MenuEngineeringAnalyzer(items=data.items)
    results  = analyzer.run_all()
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd

from config import settings

logger = logging.getLogger("food_factor.shared.menu_eng")


class MenuEngineeringAnalyzer:
    """
    Menu engineering analysis using the BCG-style matrix.

    Classifications:
        Star        — High popularity + High contribution margin
        Plow Horse  — High popularity + Low contribution margin
        Puzzle      — Low popularity  + High contribution margin
        Dog         — Low popularity  + Low contribution margin

    Also computes food-cost %, pricing gaps, modifier analysis,
    and category-level aggregation.

    Parameters
    ----------
    items : pd.DataFrame
        Normalized item-level sales data.  Must contain columns
        ``item_name``, ``category``, ``quantity``, ``net_sales``,
        ``cost``, ``contribution_margin``, ``modifiers``, and
        ``modifier_amount``.
    """

    def __init__(self, items: pd.DataFrame) -> None:
        self.items = items

    def run_all(self) -> Dict[str, Any]:
        """Execute all menu engineering analyses."""
        return {
            "matrix":            self.classify_items(),
            "food_cost_by_cat":  self.food_cost_by_category(),
            "modifier_analysis": self.modifier_analysis(),
            "pricing_gaps":      self.pricing_gap_analysis(),
            "category_matrix":   self.category_level_matrix(),
        }

    # ─── item classification ──────────────────

    def classify_items(self) -> pd.DataFrame:
        """
        Classify each menu item into Star / Plow Horse / Puzzle / Dog.

        Uses median popularity (quantity sold) and median per-unit
        contribution margin as thresholds.
        """
        item_agg = self.items.groupby(["item_name", "category"]).agg(
            quantity_sold=("quantity", "sum"),
            net_sales=("net_sales", "sum"),
            total_cost=("cost", "sum"),
            total_margin=("contribution_margin", "sum"),
        ).reset_index()

        item_agg["avg_price"]    = item_agg["net_sales"] / item_agg["quantity_sold"]
        item_agg["avg_margin"]   = item_agg["total_margin"] / item_agg["quantity_sold"]
        item_agg["food_cost_pct"] = item_agg["total_cost"] / item_agg["net_sales"]
        item_agg["margin_pct"]   = item_agg["total_margin"] / item_agg["net_sales"]

        pop_median = item_agg["quantity_sold"].median()
        margin_median = item_agg["avg_margin"].median()

        def _classify(row: pd.Series) -> str:
            high_pop = row["quantity_sold"] >= pop_median
            high_margin = row["avg_margin"] >= margin_median
            if high_pop and high_margin:
                return "Star"
            if high_pop and not high_margin:
                return "Plow Horse"
            if not high_pop and high_margin:
                return "Puzzle"
            return "Dog"

        item_agg["classification"] = item_agg.apply(_classify, axis=1)
        item_agg["pop_median"]     = pop_median
        item_agg["margin_median"]  = margin_median

        return item_agg.sort_values("net_sales", ascending=False)

    # ─── food cost ────────────────────────────

    def food_cost_by_category(self) -> pd.DataFrame:
        """Food cost percentage breakdown by category."""
        cat = self.items.groupby("category").agg(
            net_sales=("net_sales", "sum"),
            total_cost=("cost", "sum"),
        ).reset_index()
        cat["food_cost_pct"] = cat["total_cost"] / cat["net_sales"]
        cat["benchmark"]     = settings.BENCHMARKS["food_cost_pct"]
        cat["vs_benchmark"]  = cat["food_cost_pct"] - cat["benchmark"]
        return cat.sort_values("food_cost_pct", ascending=False)

    # ─── modifiers ────────────────────────────

    def modifier_analysis(self) -> pd.DataFrame:
        """Analyze modifier attach rates and revenue contribution."""
        has_mod = self.items[self.items["modifiers"] != ""].copy()
        if has_mod.empty:
            return pd.DataFrame()

        mod_summary = has_mod.groupby("modifiers").agg(
            count=("quantity", "sum"),
            total_upcharge=("modifier_amount", "sum"),
        ).reset_index().sort_values("count", ascending=False)

        total_items = len(self.items)
        mod_summary["attach_rate"] = mod_summary["count"] / total_items
        return mod_summary

    # ─── pricing gaps ─────────────────────────

    def pricing_gap_analysis(self) -> pd.DataFrame:
        """
        Identify items whose food cost exceeds the benchmark.

        Suggests a target price to bring each item in line with
        the benchmark food-cost percentage.
        """
        items = self.classify_items()
        target_margin = settings.BENCHMARKS["food_cost_pct"]

        underpriced = items[items["food_cost_pct"] > target_margin].copy()
        underpriced["suggested_price"] = underpriced["total_cost"] / (
            underpriced["quantity_sold"] * target_margin
        )
        underpriced["price_gap"] = (
            underpriced["suggested_price"] - underpriced["avg_price"]
        )
        return (
            underpriced[underpriced["price_gap"] > 0]
            .sort_values("price_gap", ascending=False)
        )

    # ─── category-level matrix ────────────────

    def category_level_matrix(self) -> pd.DataFrame:
        """Category-level aggregation for high-level menu health."""
        cat = self.items.groupby("category").agg(
            quantity_sold=("quantity", "sum"),
            net_sales=("net_sales", "sum"),
            total_margin=("contribution_margin", "sum"),
            total_cost=("cost", "sum"),
            unique_items=("item_name", "nunique"),
        ).reset_index()
        cat["margin_pct"]          = cat["total_margin"] / cat["net_sales"]
        cat["food_cost_pct"]       = cat["total_cost"] / cat["net_sales"]
        cat["avg_margin_per_item"] = cat["total_margin"] / cat["quantity_sold"]
        return cat.sort_values("total_margin", ascending=False)
