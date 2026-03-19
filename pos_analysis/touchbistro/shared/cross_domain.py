"""
pos_analysis.shared.cross_domain
==================================
Cross-domain analysis combining POS sales, delivery, and reservation data.

This module produces the executive summary and integrated insights that
only emerge when looking at all data sources together. Used by all POS
pipelines (Square, TouchBistro, Lightspeed).

All functions accept analysis results as dicts and benchmark values as
parameters — no POS-specific imports.
"""

import pandas as pd
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Defaults — override per-client via function params
DEFAULT_BENCHMARKS: Dict[str, Tuple[float, float]] = {
    "food_cost_pct":    (28.0, 35.0),
    "no_show_rate_pct": (0.0, 10.0),
    "avg_tip_pct":      (15.0, 20.0),
}


def build_executive_summary(
    sales: Dict[str, Any],
    menu: Dict[str, Any],
    payments: Dict[str, Any],
    ops: Dict[str, Any],
    delivery_df: pd.DataFrame,
    reservations_df: pd.DataFrame,
    benchmarks: Dict[str, Tuple[float, float]] = DEFAULT_BENCHMARKS,
) -> Dict[str, Any]:
    """
    Build the executive summary from all analysis domains.

    Combines sales KPIs, menu engineering results, delivery financials,
    reservation metrics, and operational flags into a single summary
    with auto-generated findings, recommendations, and health indicators.

    Args:
        sales:           Output from run_sales_analysis().
        menu:            Output from run_menu_engineering().
        payments:        Output from run_payment_analysis().
        ops:             Output from run_operational_flags().
        delivery_df:     Cleaned delivery DataFrame from ingest.
        reservations_df: Cleaned reservations DataFrame from ingest.
        benchmarks:      Dict of benchmark ranges keyed by metric name.

    Returns:
        Dict with: kpis, delivery_gross, delivery_net, delivery_orders,
        total_reservations, noshow_rate, findings, recommendations,
        health_indicators.
    """
    kpis = sales["kpis"]
    quad_summary = menu["quadrant_summary"]
    food_cost = menu["food_cost"]

    # ── Delivery KPIs ──
    completed_delivery = (
        delivery_df[~delivery_df["is_canceled"]]
        if not delivery_df.empty else pd.DataFrame()
    )
    delivery_gross = (
        completed_delivery["Gross_Sales"].sum()
        if not completed_delivery.empty else 0
    )
    delivery_net = (
        completed_delivery["Net_Payout"].sum()
        if not completed_delivery.empty else 0
    )
    delivery_orders = len(completed_delivery)

    # ── Reservation KPIs ──
    total_res = len(reservations_df) if not reservations_df.empty else 0
    noshow_rate = (
        reservations_df["is_noshow"].sum() / total_res * 100
    ) if total_res > 0 else 0

    # ── Auto-generated Findings ──
    findings: List[str] = []

    # Best/worst days
    dow = sales["day_of_week"]
    best_day = dow.loc[dow["avg_daily_revenue"].idxmax(), "weekday_name"]
    worst_day = dow.loc[dow["avg_daily_revenue"].idxmin(), "weekday_name"]
    findings.append(
        f"{best_day} is the highest-revenue day at "
        f"${dow.loc[dow['avg_daily_revenue'].idxmax(), 'avg_daily_revenue']:,.0f} avg; "
        f"{worst_day} is the weakest at "
        f"${dow.loc[dow['avg_daily_revenue'].idxmin(), 'avg_daily_revenue']:,.0f}."
    )

    # Food cost
    overall_fc = food_cost["overall_food_cost_pct"]
    fc_low, fc_high = benchmarks.get("food_cost_pct", (28.0, 35.0))
    if overall_fc > fc_high:
        findings.append(
            f"Overall food cost at {overall_fc:.1f}% exceeds the "
            f"{fc_high:.0f}% benchmark. "
            f"{len(food_cost['high_cost_items'])} items above threshold."
        )
    else:
        findings.append(
            f"Overall food cost at {overall_fc:.1f}% is within benchmark range."
        )

    # Stars count
    stars = quad_summary[quad_summary["quadrant"] == "Star"]
    if not stars.empty:
        findings.append(
            f"{int(stars['item_count'].values[0])} Star items driving "
            f"{stars['pct_revenue'].values[0]:.0f}% of revenue — protect these."
        )

    # Voids
    void_data = ops["voids"]
    if void_data["severity"] != "Normal":
        findings.append(
            f"Void rate at {void_data['void_rate_pct']:.1f}% — "
            f"${void_data['void_revenue_lost']:,.0f} in lost revenue. Investigate."
        )

    # No-shows
    ns_low, ns_high = benchmarks.get("no_show_rate_pct", (0.0, 10.0))
    if noshow_rate > ns_high:
        findings.append(
            f"No-show rate at {noshow_rate:.1f}% exceeds "
            f"{ns_high:.0f}% threshold."
        )

    # ── Auto-generated Recommendations ──
    recommendations: List[str] = []

    recommendations.append(
        f"Launch targeted {worst_day} promotion to lift weakest day volume. "
        f"Test a prix fixe or happy hour concept."
    )

    dogs = quad_summary[quad_summary["quadrant"] == "Dog"]
    if not dogs.empty and dogs["item_count"].values[0] > 0:
        recommendations.append(
            f"Review {int(dogs['item_count'].values[0])} Dog items — "
            f"remove or redesign lowest performers to simplify menu."
        )

    plowhorses = quad_summary[quad_summary["quadrant"] == "Plowhorse"]
    if not plowhorses.empty and plowhorses["item_count"].values[0] > 0:
        recommendations.append(
            f"Re-cost {int(plowhorses['item_count'].values[0])} Plowhorse items — "
            f"popular but low-margin. $1-2 price increase or ingredient substitution."
        )

    if delivery_gross > 0:
        commission_pct = (1 - delivery_net / delivery_gross) * 100
        recommendations.append(
            f"Delivery commission averaging {commission_pct:.0f}% of gross. "
            f"Negotiate rates or shift volume to direct online ordering."
        )

    # ── Health Indicators (RAG status) ──
    tip_low, _ = benchmarks.get("avg_tip_pct", (15.0, 20.0))

    health: Dict[str, str] = {
        "Revenue":   "green" if kpis["avg_daily_revenue"] > 10000 else "amber",
        "Food Cost": "green" if fc_low <= overall_fc <= fc_high else "red",
        "Voids":     "green" if void_data["severity"] == "Normal" else "red",
        "No-Shows":  "green" if noshow_rate <= ns_high else "amber",
        "Tips":      "green" if kpis["avg_tip_pct"] >= tip_low else "amber",
    }

    return {
        "kpis":               kpis,
        "delivery_gross":     round(delivery_gross, 2),
        "delivery_net":       round(delivery_net, 2),
        "delivery_orders":    delivery_orders,
        "total_reservations": total_res,
        "noshow_rate":        round(noshow_rate, 1),
        "findings":           findings,
        "recommendations":    recommendations,
        "health_indicators":  health,
    }
