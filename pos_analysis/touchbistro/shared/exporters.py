"""
pos_analysis.shared.exporters
===============================
Output formatting for Food Factor reports.

Generates structured output from analysis results:
    - generate_markdown_report()  → Full Markdown report for review/PDF conversion
    - export_kpis_json()          → KPIs as JSON for downstream consumers

POS-agnostic: accepts all data as parameters, no POS-specific imports.
Restaurant-specific metadata (name, period, location) passed via report_meta dict.
"""

import json
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def generate_markdown_report(
    exec_summary: Dict[str, Any],
    sales: Dict[str, Any],
    menu: Dict[str, Any],
    payments: Dict[str, Any],
    ops: Dict[str, Any],
    chart_paths: Dict[str, Path],
    report_meta: Dict[str, str] = None,
) -> str:
    """
    Generate a comprehensive Markdown report from analysis results.

    This serves as the review document before final PDF generation.
    Chart images are referenced by relative path from the charts/ directory.

    Args:
        exec_summary: Output from cross_domain.build_executive_summary().
        sales:        Output from analysis.run_sales_analysis().
        menu:         Output from menu_engineering.run_menu_engineering().
        payments:     Output from analysis.run_payment_analysis().
        ops:          Output from analysis.run_operational_flags().
        chart_paths:  Dict mapping chart name → file path.
        report_meta:  Dict with keys: restaurant_name, report_period,
                      pos_system, location, report_date.

    Returns:
        Markdown string of the full report.
    """
    meta = report_meta or {}
    restaurant = meta.get("restaurant_name", "Restaurant")
    period = meta.get("report_period", "")
    pos = meta.get("pos_system", "")
    location = meta.get("location", "")
    report_date = meta.get("report_date", "")

    kpis = exec_summary["kpis"]

    lines = []
    lines.append(f"# {restaurant} — Monthly Performance Report")
    lines.append(f"**Period:** {period}  ")
    lines.append(f"**POS System:** {pos}  ")
    lines.append(f"**Location:** {location}  ")
    lines.append(f"**Report Date:** {report_date}  ")
    lines.append("**Prepared by:** Food Factor Consulting\n")

    # ── 1. Executive Summary ──
    lines.append("---\n## 1. Executive Summary\n")
    lines.append("### Key Metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| **Net Revenue** | **${kpis['total_net']:,.2f}** |")
    lines.append(f"| Avg Daily Revenue | ${kpis['avg_daily_revenue']:,.2f} |")
    lines.append(f"| Total Covers | {kpis['total_covers']:,} |")
    lines.append(f"| Avg Check Size | ${kpis['avg_check']:.2f} |")
    lines.append(f"| Revenue per Cover | ${kpis['revenue_per_cover']:.2f} |")
    lines.append(f"| Total Bills | {kpis['total_bills']:,} |")
    lines.append(f"| Items Sold | {kpis['items_sold']:,} |")
    lines.append(f"| Avg Tip Rate | {kpis['avg_tip_pct']:.1f}% |")
    lines.append(f"| Discount Rate | {kpis['discount_rate_pct']:.1f}% |")
    lines.append(f"| Operating Days | {kpis['operating_days']} |\n")

    lines.append("### Top Findings\n")
    for i, finding in enumerate(exec_summary["findings"], 1):
        lines.append(f"{i}. {finding}")

    lines.append("\n### Top Recommendations\n")
    for i, rec in enumerate(exec_summary["recommendations"], 1):
        lines.append(f"{i}. {rec}")

    lines.append("\n### Health Dashboard\n")
    lines.append("| Domain | Status |")
    lines.append("|---|---|")
    for domain, status in exec_summary["health_indicators"].items():
        emoji = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(status, "⚪")
        lines.append(f"| {domain} | {emoji} {status.title()} |")

    # ── 2. Revenue & Sales ──
    lines.append("\n---\n## 2. Revenue & Sales Performance\n")
    lines.append("![Daily Revenue](charts/01_daily_revenue.png)\n")

    lines.append("### Day-of-Week Performance\n")
    dow = sales["day_of_week"]
    lines.append("| Day | Avg Revenue | Avg Covers | Avg Check |")
    lines.append("|---|---|---|---|")
    for _, row in dow.iterrows():
        lines.append(
            f"| {row['weekday_name']} | ${row['avg_daily_revenue']:,.0f} | "
            f"{row['avg_daily_covers']:.0f} | ${row['avg_check']:.2f} |"
        )

    lines.append("\n![Day of Week](charts/02_day_of_week.png)\n")

    lines.append("### Daypart Performance\n")
    dp = sales["daypart"]
    lines.append("| Daypart | Revenue | % of Total | Covers | Avg Check |")
    lines.append("|---|---|---|---|---|")
    for _, row in dp.iterrows():
        lines.append(
            f"| {row['daypart']} | ${row['total_net']:,.0f} | "
            f"{row['pct_revenue']:.0f}% | {int(row['total_covers']):,} | "
            f"${row['avg_check']:.2f} |"
        )

    lines.append("\n![Daypart](charts/03_daypart_revenue.png)\n")
    lines.append("![Heatmap](charts/04_hourly_heatmap.png)\n")

    lines.append("### Top 10 Items by Revenue\n")
    top = sales["top_bottom_items"]["top_by_revenue"]
    lines.append("| Item | Category | Qty | Net Sales |")
    lines.append("|---|---|---|---|")
    for _, row in top.iterrows():
        lines.append(
            f"| {row['Menu_Item']} | {row['Menu_Category']} | "
            f"{int(row['quantity']):,} | ${row['net_sales']:,.2f} |"
        )
    lines.append("\n![Top Items](charts/05_top_items_revenue.png)\n")
    lines.append("![Category Performance](charts/06_category_performance.png)\n")
    lines.append("![Sales Category](charts/14_sales_category_split.png)\n")

    # ── 3. Menu Engineering ──
    lines.append("\n---\n## 3. Menu Engineering\n")
    lines.append("![Menu Matrix](charts/07_menu_matrix.png)\n")

    qs = menu["quadrant_summary"]
    lines.append("### Quadrant Summary\n")
    lines.append("| Quadrant | Items | Revenue | % Revenue | Avg Margin | Avg Food Cost |")
    lines.append("|---|---|---|---|---|---|")
    for _, row in qs.iterrows():
        lines.append(
            f"| {row['quadrant']} | {int(row['item_count'])} | "
            f"${row['total_revenue']:,.0f} | {row['pct_revenue']:.0f}% | "
            f"${row['avg_margin']:.2f} | {row['avg_food_cost']:.1f}% |"
        )

    fc = menu["food_cost"]
    lines.append(f"\n### Food Cost Analysis\n")
    lines.append(f"**Overall Food Cost:** {fc['overall_food_cost_pct']:.1f}%  ")
    lines.append(
        f"**Benchmark Range:** "
        f"{fc['benchmark_range'][0]:.0f}–{fc['benchmark_range'][1]:.0f}%\n"
    )
    lines.append("![Food Cost by Category](charts/08_food_cost_category.png)\n")

    gaps = menu["pricing_gaps"]
    if not gaps.empty:
        lines.append("### Pricing Action Items\n")
        lines.append("| Item | Action | Revenue | Qty Sold |")
        lines.append("|---|---|---|---|")
        for _, row in gaps.head(10).iterrows():
            lines.append(
                f"| {row['Menu_Item']} | {row['price_action']} | "
                f"${row['Net_Sales']:,.0f} | {int(row['Quantity_Sold'])} |"
            )

    # ── 4. Payment Analysis ──
    lines.append("\n---\n## 4. Payment Analysis\n")
    lines.append("![Payment Mix](charts/09_payment_mix.png)\n")

    pay = payments["payment_summary"]
    lines.append("| Method | Amount | Share | Avg Txn | Tip Rate |")
    lines.append("|---|---|---|---|---|")
    for _, row in pay.iterrows():
        lines.append(
            f"| {row['Payment_Method']} | ${row['Total_Amount']:,.0f} | "
            f"{row['pct_of_total']:.0f}% | ${row['avg_transaction']:.2f} | "
            f"{row['tip_rate_pct']:.1f}% |"
        )

    disc = payments["discount_rates"]
    lines.append(
        f"\n**Total Discounts:** ${disc['total_discounts']:,.2f} "
        f"({disc['discount_rate_pct']:.1f}% of gross)  "
    )
    lines.append(
        f"**Bills with Discounts:** {disc['discounted_bills']} "
        f"({disc['discounted_bills_pct']:.1f}%)\n"
    )

    tip = payments["tip_analysis"]
    lines.append(f"**Overall Tip Rate:** {tip['overall_tip_pct']:.1f}%  ")
    lines.append(f"**Total Tips:** ${tip['total_tips']:,.2f}\n")

    # ── 5. Operational Flags ──
    lines.append("\n---\n## 5. Operational Flags\n")

    void = ops["voids"]
    lines.append(f"### Voids: {void['severity']} ({void['void_rate_pct']:.2f}%)\n")
    lines.append(f"- {void['void_count']} items voided out of {void['total_items']:,}")
    lines.append(f"- Revenue impact: ${void['void_revenue_lost']:,.2f}")
    lines.append(f"- Threshold: {void['threshold']:.1f}%\n")
    lines.append("![Void Rate by Server](charts/11_void_rate_server.png)\n")

    refund = ops["refunds"]
    lines.append("### Refunds\n")
    lines.append(f"- {refund['refund_count']} return transactions")
    lines.append(f"- Total refunded: ${refund['refund_amount']:,.2f}")
    lines.append(f"- Refund rate: {refund['refund_rate_pct']:.2f}%\n")

    comp = ops["comps"]
    lines.append(f"### Comps: {comp['severity']}\n")
    lines.append(
        f"- {comp['comp_count']} full comp items"
    )
    lines.append(
        f"- Revenue impact: ${comp['comp_revenue_lost']:,.2f} "
        f"({comp['comp_rate_pct']:.2f}%)"
    )
    lines.append(
        f"- Late-night comps (after 10 PM): {comp['late_night_comp_count']}\n"
    )

    alerts = ops["alerts"]
    if alerts:
        lines.append("### Active Alerts\n")
        lines.append("| Category | Severity | Details |")
        lines.append("|---|---|---|")
        for alert in alerts:
            lines.append(
                f"| {alert['category']} | {alert['severity']} | "
                f"{alert['message']} |"
            )

    # ── 6. Delivery Performance ──
    lines.append("\n---\n## 6. Delivery Performance\n")
    lines.append(f"- Orders completed: {exec_summary['delivery_orders']}")
    lines.append(
        f"- Gross delivery revenue: ${exec_summary['delivery_gross']:,.2f}"
    )
    lines.append(f"- Net payout: ${exec_summary['delivery_net']:,.2f}")
    if exec_summary["delivery_gross"] > 0:
        eff_rate = (
            1 - exec_summary["delivery_net"] / exec_summary["delivery_gross"]
        ) * 100
        lines.append(f"- Effective commission rate: {eff_rate:.1f}%\n")
    lines.append("![Delivery Comparison](charts/12_delivery_comparison.png)\n")

    # ── 7. Reservations ──
    lines.append("\n---\n## 7. Reservations & Capacity\n")
    lines.append(f"- Total reservations: {exec_summary['total_reservations']}")
    lines.append(f"- No-show rate: {exec_summary['noshow_rate']:.1f}%\n")
    lines.append("![Reservation Status](charts/13_reservation_status.png)\n")

    # ── 8. Server Performance ──
    lines.append("\n---\n## 8. Server Performance\n")
    lines.append("![Server Performance](charts/10_server_performance.png)\n")
    srv = sales["server_performance"]
    lines.append("| Server | Revenue | Bills | Avg Check | Tip Rate |")
    lines.append("|---|---|---|---|---|")
    for _, row in srv.iterrows():
        lines.append(
            f"| {row['Waiter']} | ${row['net_sales']:,.0f} | "
            f"{int(row['bill_count'])} | ${row['avg_check']:.2f} | "
            f"{row['tip_rate_pct']:.1f}% |"
        )

    # ── Footer ──
    lines.append("\n---\n*Report generated by Food Factor Intelligence Platform*  ")
    lines.append(f"*Data period: {period} | Generated: {report_date}*\n")

    return "\n".join(lines)


def export_kpis_json(
    kpis: Dict[str, Any],
    output_path: Path,
) -> Path:
    """
    Export KPIs dict as formatted JSON for downstream consumers.

    Args:
        kpis: Dict of key performance indicators.
        output_path: File path to write JSON.

    Returns:
        Path to the written JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(kpis, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info(f"KPIs exported: {output_path}")
    return output_path
