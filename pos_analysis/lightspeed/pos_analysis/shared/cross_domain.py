"""
pos_analysis.shared.cross_domain — Cross-Domain Analysis & Report Compilation

Generates executive summaries, key findings, prioritized recommendations,
and action plans by synthesizing results from multiple data domains
(POS sales, labor, menu engineering, delivery, reservations, operational flags).

POS-agnostic: accepts analysis result dicts with standardized keys.
Restaurant-specific metadata (name, location, period) is passed via
a ``restaurant_config`` dict rather than hard-coded imports.

Used by all three POS pipeline runners to compile the final report.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
import logging

from pos_analysis.shared import BENCHMARKS

logger = logging.getLogger(__name__)


def generate_executive_summary(
    sales: Dict[str, Any],
    menu: Dict[str, Any],
    labor: Dict[str, Any],
    delivery: Dict[str, Any],
    reservation: Dict[str, Any],
    ops: Dict[str, Any],
    restaurant_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate executive summary content for page 1 of the report.

    Args:
        sales:             Output of run_sales_analysis().
        menu:              Output of run_menu_engineering().
        labor:             Output of run_labor_analysis().
        delivery:          Output of run_delivery_analysis().
        reservation:       Output of run_reservation_analysis().
        ops:               Output of run_operational_flags().
        restaurant_config: Dict with keys: restaurant_name, location, period,
                           concept, pos_system, total_seats.

    Returns:
        Dict with KPI cards, top findings, and top recommendations.
    """
    rev = sales["revenue_summary"]
    lab = labor["labor_summary"]
    res_summary = reservation.get("summary", {})

    # KPI cards with benchmark comparison
    kpis: List[Dict[str, Any]] = [
        {
            "metric":   "Net Revenue",
            "value":    rev["total_net_revenue"],
            "format":   "currency",
            "trend":    None,
        },
        {
            "metric":   "Average Check",
            "value":    rev["avg_check"],
            "format":   "currency",
        },
        {
            "metric":   "Total Covers",
            "value":    rev["total_covers"],
            "format":   "integer",
        },
        {
            "metric":   "Labor %",
            "value":    lab["labor_pct"],
            "format":   "percent",
            "benchmark": BENCHMARKS["labor_pct"],
            "status":   "good" if lab["labor_pct"] <= BENCHMARKS["labor_pct"] else "warning",
        },
        {
            "metric":   "SPLH",
            "value":    lab["splh"],
            "format":   "currency",
            "benchmark": BENCHMARKS["splh_target"],
            "status":   "good" if lab["splh"] >= BENCHMARKS["splh_target"] else "warning",
        },
    ]

    if res_summary:
        kpis.append({
            "metric":   "No-Show Rate",
            "value":    res_summary.get("no_show_rate", 0),
            "format":   "percent",
            "benchmark": BENCHMARKS["no_show_rate_max"],
            "status":   "good" if res_summary.get("no_show_rate", 0) <= BENCHMARKS["no_show_rate_max"] else "warning",
        })

    findings = _generate_findings(sales, menu, labor, delivery, reservation, ops)
    recommendations = _generate_recommendations(sales, menu, labor, delivery, reservation, ops)

    return {
        "restaurant_name":      restaurant_config.get("restaurant_name", ""),
        "location":             restaurant_config.get("location", ""),
        "period":               restaurant_config.get("period", ""),
        "generated_at":         datetime.now().isoformat(),
        "kpis":                 kpis,
        "top_findings":         findings[:5],
        "top_recommendations":  recommendations[:5],
    }


def _generate_findings(
    sales: Dict, menu: Dict, labor: Dict,
    delivery: Dict, reservation: Dict, ops: Dict,
) -> List[Dict[str, str]]:
    """Auto-generate key findings from analysis results."""
    findings: List[Dict[str, str]] = []
    rev = sales["revenue_summary"]
    lab = labor["labor_summary"]

    # Revenue finding
    findings.append({
        "category": "Revenue",
        "finding":  f"Net revenue of ${rev['total_net_revenue']:,.0f} across "
                    f"{rev['transaction_count']:,} transactions, averaging "
                    f"${rev['avg_check']:.2f} per check and "
                    f"${rev['rev_per_cover']:.2f} per cover.",
    })

    # Day-of-week insight
    dow = sales["day_of_week"]
    best_day = dow["avg_daily_revenue"].idxmax()
    worst_day = dow["avg_daily_revenue"].idxmin()
    gap = dow.loc[best_day, "avg_daily_revenue"] - dow.loc[worst_day, "avg_daily_revenue"]
    findings.append({
        "category": "Revenue Pattern",
        "finding":  f"{best_day} generates ${dow.loc[best_day, 'avg_daily_revenue']:,.0f}/day "
                    f"vs {worst_day} at ${dow.loc[worst_day, 'avg_daily_revenue']:,.0f}/day — "
                    f"a ${gap:,.0f} gap that signals opportunity for targeted promotions.",
    })

    # Labor finding
    status = "within target" if lab["labor_pct"] <= BENCHMARKS["labor_pct"] else "above target"
    findings.append({
        "category": "Labor",
        "finding":  f"Labor cost at {lab['labor_pct']:.1%} of revenue is {status} "
                    f"(benchmark: {BENCHMARKS['labor_pct']:.0%}). "
                    f"SPLH of ${lab['splh']:.0f} "
                    f"{'exceeds' if lab['splh'] >= BENCHMARKS['splh_target'] else 'falls below'} "
                    f"the ${BENCHMARKS['splh_target']:.0f} target.",
    })

    # Menu engineering finding
    matrix = menu.get("menu_matrix", pd.DataFrame())
    if not matrix.empty:
        stars = matrix[matrix["classification"] == "Star"]
        dogs = matrix[matrix["classification"] == "Dog"]
        findings.append({
            "category": "Menu",
            "finding":  f"{len(stars)} Star items drive both volume and margin. "
                        f"{len(dogs)} Dog items underperform on both dimensions — "
                        f"candidates for removal or repositioning.",
        })

    # Food cost finding
    food_cost = menu.get("food_cost", {})
    if food_cost:
        fc_pct = food_cost.get("overall_food_cost_pct", 0)
        findings.append({
            "category": "Food Cost",
            "finding":  f"Overall food cost at {fc_pct:.1%} "
                        f"{'exceeds' if fc_pct > BENCHMARKS['food_cost_pct'] else 'is within'} "
                        f"the {BENCHMARKS['food_cost_pct']:.0%} target.",
        })

    # Operational flags
    flag_count = ops.get("flag_count", {})
    if flag_count.get("critical", 0) > 0 or flag_count.get("warning", 0) > 0:
        findings.append({
            "category": "Operations",
            "finding":  f"{flag_count.get('critical', 0)} critical and "
                        f"{flag_count.get('warning', 0)} warning-level operational "
                        f"flags identified. See Operational Flags section for details.",
        })

    # Delivery finding
    if delivery.get("status") != "no_data" and delivery.get("summary"):
        ds = delivery["summary"]
        findings.append({
            "category": "Delivery",
            "finding":  f"Delivery generates ${ds['gross_revenue']:,.0f} gross but only "
                        f"${ds['net_payout']:,.0f} net ({ds['effective_take_rate']:.0%} "
                        f"consumed by platform fees).",
        })

    # Reservation finding
    if reservation.get("summary"):
        rs = reservation["summary"]
        if rs.get("no_show_rate", 0) > BENCHMARKS["no_show_rate_max"]:
            lost = rs.get("total_covers_res", 0) * rs.get("no_show_rate", 0)
            findings.append({
                "category": "Reservations",
                "finding":  f"No-show rate of {rs['no_show_rate']:.1%} exceeds the "
                            f"{BENCHMARKS['no_show_rate_max']:.0%} benchmark, representing "
                            f"~{int(lost)} lost covers this period.",
            })

    return findings


def _generate_recommendations(
    sales: Dict, menu: Dict, labor: Dict,
    delivery: Dict, reservation: Dict, ops: Dict,
) -> List[Dict[str, str]]:
    """Auto-generate prioritized recommendations."""
    recs: List[Dict[str, str]] = []
    lab = labor["labor_summary"]

    # Labor optimization
    if lab["labor_pct"] > BENCHMARKS["labor_pct"]:
        labor_dow = labor.get("by_day", pd.DataFrame())
        if not labor_dow.empty:
            worst = labor_dow["labor_pct"].idxmax()
            recs.append({
                "priority": "HIGH",
                "category": "Labor",
                "action":   f"Reduce {worst} staffing — labor % of "
                            f"{labor_dow.loc[worst, 'labor_pct']:.0%} is the worst day. "
                            f"Cut one FOH shift to align with "
                            f"{labor_dow.loc[worst, 'avg_daily_covers']:.0f} avg covers.",
                "impact":   "Estimated $200-400/week savings",
                "effort":   "Low",
            })

    if lab["overtime_shifts"] > 10:
        recs.append({
            "priority": "MEDIUM",
            "category": "Labor",
            "action":   f"Address overtime — {lab['overtime_shifts']} OT shifts "
                        f"costing ${lab['overtime_premium']:,.0f} in premium. "
                        f"Redistribute shifts to stay under 8-hour threshold.",
            "impact":   f"${lab['overtime_premium']:,.0f} savings",
            "effort":   "Medium",
        })

    # Menu recommendations
    matrix = menu.get("menu_matrix", pd.DataFrame())
    if not matrix.empty:
        dogs = matrix[matrix["classification"] == "Dog"]
        if len(dogs) > 3:
            dog_names = dogs.nsmallest(3, "total_revenue")["Name"].tolist()
            recs.append({
                "priority": "MEDIUM",
                "category": "Menu",
                "action":   f"Remove or reposition bottom performers: "
                            f"{', '.join(dog_names)}. "
                            f"These items contribute <2% of revenue each.",
                "impact":   "Simplified operations, reduced waste",
                "effort":   "Low",
            })

        puzzles = matrix[matrix["classification"] == "Puzzle"]
        if len(puzzles) > 0:
            top_puzzle = puzzles.nlargest(1, "unit_margin")["Name"].values[0]
            recs.append({
                "priority": "MEDIUM",
                "category": "Menu",
                "action":   f"Promote high-margin Puzzle items like {top_puzzle} — "
                            f"server training on suggestive selling and menu positioning.",
                "impact":   "Increased margin without price changes",
                "effort":   "Low",
            })

    # No-show mitigation
    res_summary = reservation.get("summary", {})
    if res_summary.get("no_show_rate", 0) > BENCHMARKS["no_show_rate_max"]:
        recs.append({
            "priority": "HIGH",
            "category": "Reservations",
            "action":   "Implement confirmation texts 24h and 2h before reservation. "
                        "Add credit card hold policy for parties of 5+.",
            "impact":   f"Reduce {res_summary['no_shows']} monthly no-shows by 30-50%",
            "effort":   "Medium",
        })

    # Delivery margin
    if delivery.get("summary"):
        ds = delivery["summary"]
        if ds.get("effective_take_rate", 0) > 0.25:
            recs.append({
                "priority": "MEDIUM",
                "category": "Delivery",
                "action":   f"Negotiate commission rates (currently "
                            f"{ds['effective_take_rate']:.0%} blended). "
                            f"At current volume, a 2% reduction saves "
                            f"~${ds['gross_revenue'] * 0.02:,.0f}/month.",
                "impact":   "Direct margin improvement",
                "effort":   "Medium",
            })

    return recs


def generate_action_plan(recommendations: List[Dict[str, str]]) -> pd.DataFrame:
    """
    Convert recommendations into a structured action plan table.

    Args:
        recommendations: List of recommendation dicts from _generate_recommendations.

    Returns:
        DataFrame with priority, category, action, impact, effort, timeline, owner.
    """
    if not recommendations:
        return pd.DataFrame()

    plan = pd.DataFrame(recommendations)
    plan["timeline"] = plan["effort"].map({
        "Low": "This Week",
        "Medium": "This Month",
        "High": "Next Quarter",
    })
    plan["owner"] = "TBD"

    return plan[["priority", "category", "action", "impact", "effort", "timeline", "owner"]]


def compile_report_data(
    sales: Dict[str, Any],
    menu: Dict[str, Any],
    payment: Dict[str, Any],
    labor: Dict[str, Any],
    delivery: Dict[str, Any],
    reservation: Dict[str, Any],
    ops: Dict[str, Any],
    restaurant_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compile all analysis results into the final report data structure.

    This is the master output that feeds the PDF/PPTX generators.

    Args:
        sales:             Output of run_sales_analysis().
        menu:              Output of run_menu_engineering().
        payment:           Output of run_payment_analysis().
        labor:             Output of run_labor_analysis().
        delivery:          Output of run_delivery_analysis().
        reservation:       Output of run_reservation_analysis().
        ops:               Output of run_operational_flags().
        restaurant_config: Dict with restaurant_name, location, concept,
                           period, pos_system, total_seats.

    Returns:
        Complete report data dictionary for downstream rendering.
    """
    logger.info("Compiling report data...")

    exec_summary = generate_executive_summary(
        sales, menu, labor, delivery, reservation, ops, restaurant_config,
    )
    action_plan = generate_action_plan(exec_summary["top_recommendations"])

    report: Dict[str, Any] = {
        "metadata": {
            "restaurant_name":  restaurant_config.get("restaurant_name", ""),
            "location":         restaurant_config.get("location", ""),
            "concept":          restaurant_config.get("concept", ""),
            "period":           restaurant_config.get("period", ""),
            "pos_system":       restaurant_config.get("pos_system", ""),
            "total_seats":      restaurant_config.get("total_seats", 0),
            "generated_at":     datetime.now().isoformat(),
            "version":          "1.0.0",
        },
        "executive_summary":    exec_summary,
        "sales":                sales,
        "menu_engineering":     menu,
        "payments":             payment,
        "labor":                labor,
        "delivery":             delivery,
        "reservations":         reservation,
        "operational_flags":    ops,
        "action_plan":          action_plan.to_dict("records") if not action_plan.empty else [],
    }

    logger.info(
        f"Report compiled — "
        f"{len(exec_summary['top_findings'])} findings, "
        f"{len(exec_summary['top_recommendations'])} recommendations, "
        f"{len(report['action_plan'])} action items"
    )
    return report
