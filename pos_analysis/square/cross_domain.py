"""
pos_analysis/shared/cross_domain.py — Cross-Domain Insight Generator
=====================================================================
Generates insights that only emerge when multiple data domains are
combined (POS sales + labor, reservations + revenue, delivery +
menu engineering).  This is Food Factor's core value proposition.

Each insight is returned as a dict with ``title``, ``insight``
(narrative string), and ``sources`` (list of data domains used).

Usage::

    from pos_analysis.shared.cross_domain import generate_cross_domain_insights

    insights = generate_cross_domain_insights(analysis_results)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

from config import settings

logger = logging.getLogger("food_factor.shared.cross_domain")


def generate_cross_domain_insights(
    results: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate insights by connecting multiple analysis domains.

    Parameters
    ----------
    results : dict
        Full analysis results dictionary with keys:
        ``sales``, ``labor``, ``delivery``, ``reservations``, ``menu``.

    Returns
    -------
    list[dict]
        Each dict has keys ``title``, ``insight``, ``sources``.
    """
    insights: List[Dict[str, Any]] = []

    sales = results.get("sales", {})
    labor = results.get("labor", {})
    delivery = results.get("delivery", {})
    reservations = results.get("reservations", {})
    menu = results.get("menu", {})

    # ── 1. Labor-Revenue Misalignment ─────────
    dow_sales = sales.get("day_of_week", pd.DataFrame())
    dow_labor = labor.get("dow_staffing", pd.DataFrame())

    if not dow_sales.empty and not dow_labor.empty:
        merged = pd.merge(
            dow_sales[["day_of_week", "avg_daily_rev"]],
            dow_labor[["day_of_week", "labor_pct"]],
            on="day_of_week",
            how="inner",
        )
        if not merged.empty:
            worst_day = merged.loc[merged["labor_pct"].idxmax()]
            best_day = merged.loc[merged["labor_pct"].idxmin()]
            insights.append({
                "title": "Labor-Revenue Misalignment",
                "insight": (
                    f"{worst_day['day_of_week']} has the highest labor % "
                    f"({worst_day['labor_pct']:.1%}) while "
                    f"{best_day['day_of_week']} is most efficient "
                    f"({best_day['labor_pct']:.1%}). "
                    f"Shift 1-2 staff from {worst_day['day_of_week']} to "
                    f"peak nights to optimize."
                ),
                "sources": ["POS Sales", "Timecards"],
            })

    # ── 2. No-Show Revenue Impact ─────────────
    res_kpis = reservations.get("kpis", {})
    sales_kpis = sales.get("kpis", {})

    noshow_count = res_kpis.get("noshows", 0)
    avg_party = res_kpis.get("avg_party_size", 0)
    avg_check = sales_kpis.get("avg_check_size", 0)
    noshow_rate = res_kpis.get("noshow_rate", 0)

    est_lost_revenue = noshow_count * avg_party * avg_check
    if est_lost_revenue > 0:
        insights.append({
            "title": "No-Show Revenue Impact",
            "insight": (
                f"Estimated ${est_lost_revenue:,.0f} in lost revenue from "
                f"{noshow_count} no-shows this month. "
                f"At {noshow_rate:.1%}, reducing to the "
                f"{settings.BENCHMARKS['noshow_rate_target']:.0%} target "
                f"would recover ~${est_lost_revenue * 0.4:,.0f}/month."
            ),
            "sources": ["Reservations", "POS Sales"],
        })

    # ── 3. Delivery Channel Economics ─────────
    delivery_kpis = delivery.get("kpis", {})
    delivery_aov = delivery_kpis.get("avg_order_value", 0)
    dinein_check = avg_check
    margin_gap = delivery_kpis.get("effective_margin", 0)

    if delivery_aov > 0 and dinein_check > 0:
        insights.append({
            "title": "Delivery Channel Economics",
            "insight": (
                f"Delivery AOV (${delivery_aov:.0f}) is "
                f"{'higher' if delivery_aov > dinein_check else 'lower'} than "
                f"dine-in avg check (${dinein_check:.0f}), but after "
                f"platform fees the effective margin is only {margin_gap:.0%}. "
                f"Dine-in captures 100% of revenue; every delivery order costs "
                f"~${delivery_aov * (1 - margin_gap):,.0f} in platform fees."
            ),
            "sources": ["Delivery Orders", "POS Sales"],
        })

    # ── 4. Menu Stars × Delivery Upsell ───────
    matrix = menu.get("matrix", pd.DataFrame())
    if not matrix.empty:
        stars = matrix[matrix["classification"] == "Star"]
        if not stars.empty:
            top_star = stars.iloc[0]["item_name"]
            insights.append({
                "title": "Menu Optimization Opportunity",
                "insight": (
                    f"'{top_star}' is the top Star item (high popularity + "
                    f"high margin). Ensure it's prominently featured on delivery "
                    f"platform menus and upsold by servers during dine-in service."
                ),
                "sources": ["Menu Engineering", "Delivery Orders"],
            })

    logger.info("Generated %d cross-domain insights", len(insights))
    return insights
