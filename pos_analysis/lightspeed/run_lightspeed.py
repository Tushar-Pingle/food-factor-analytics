"""
run_lightspeed.py — Food Factor Lightspeed Pipeline Runner

Top-level CLI orchestrator for the Lightspeed Restaurant analysis pipeline.
Wires together ingestion, analysis, visualization, and report compilation.

Usage:
    python run_lightspeed.py                           # Default data dir
    python run_lightspeed.py --data-dir ./client_data  # Custom data dir
    python run_lightspeed.py --skip-charts             # Analysis only (faster)
    python run_lightspeed.py --verbose                 # Debug logging
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Pipeline modules
from pos_analysis.lightspeed import (
    RESTAURANT_NAME, REPORT_PERIOD, OUTPUT_DIR, CHART_DIR,
    RESTAURANT_CONFIG, ensure_dirs,
)
from pos_analysis.lightspeed.ingest import (
    load_all, build_item_sales_view, build_daily_summary,
)
from pos_analysis.lightspeed.analysis import (
    run_sales_analysis, run_payment_analysis, run_delivery_analysis,
    run_reservation_analysis, run_operational_flags,
)
from pos_analysis.lightspeed.labor import run_labor_analysis
from pos_analysis.lightspeed.visualizations import generate_all_charts
from pos_analysis.shared.menu_engineering import run_menu_engineering
from pos_analysis.shared.cross_domain import compile_report_data
from pos_analysis.shared.exporters import export_report_json


def setup_logging(verbose: bool = False, output_dir: Path = OUTPUT_DIR) -> None:
    """Configure pipeline logging to stdout and file."""
    level = logging.DEBUG if verbose else logging.INFO
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(output_dir / "pipeline.log", mode="w"),
        ],
    )


def run_pipeline(
    data_dir: Path = None,
    skip_charts: bool = False,
    output_dir: Path = None,
) -> Dict[str, Any]:
    """
    Execute the full Food Factor Lightspeed analysis pipeline.

    Args:
        data_dir:    Directory containing Lightspeed CSV exports.
        skip_charts: If True, skip chart generation (analysis only).
        output_dir:  Override output directory.

    Returns:
        Complete report data dictionary.
    """
    start = time.time()
    out = output_dir or OUTPUT_DIR
    chart_out = out / "charts"

    logger = logging.getLogger("pipeline")
    logger.info("=" * 70)
    logger.info(f"  FOOD FACTOR — Lightspeed Analysis Pipeline")
    logger.info(f"  Restaurant: {RESTAURANT_NAME}")
    logger.info(f"  Period:     {REPORT_PERIOD}")
    logger.info("=" * 70)

    # ── STEP 1: Data Ingestion ──────────────────────────────────────
    logger.info("STEP 1/10 → Data Ingestion")
    data = load_all(data_dir)

    receipts = data["receipts"]
    items = data["receipt_items"]
    modifiers = data["modifiers"]
    payments = data["payments"]
    labor = data["labor_shifts"]
    products = data["products"]
    delivery = data["delivery"]
    reservations = data["reservations"]
    customers = data["customers"]

    total_rows = sum(len(df) for df in data.values())
    logger.info(f"  Loaded {total_rows:,} total rows across {len(data)} files")

    # ── STEP 2: Build Analytical Views ──────────────────────────────
    logger.info("STEP 2/10 → Building analytical views")
    item_sales = build_item_sales_view(receipts, items, products)
    daily_summary = build_daily_summary(receipts, labor)

    # ── STEP 3: Sales Analysis ──────────────────────────────────────
    logger.info("STEP 3/10 → Sales Analysis")
    sales_results = run_sales_analysis(receipts, items, products)

    # ── STEP 4: Menu Engineering ────────────────────────────────────
    logger.info("STEP 4/10 → Menu Engineering")
    menu_results = run_menu_engineering(items, products, modifiers)

    # ── STEP 5: Payment Analysis ────────────────────────────────────
    logger.info("STEP 5/10 → Payment Analysis")
    payment_results = run_payment_analysis(payments)

    # ── STEP 6: Labor Analysis ──────────────────────────────────────
    logger.info("STEP 6/10 → Labor Optimization")
    total_net = sales_results["revenue_summary"]["total_net_revenue"]
    labor_results = run_labor_analysis(labor, receipts, total_net)

    # ── STEP 7: Delivery Analysis ───────────────────────────────────
    logger.info("STEP 7/10 → Delivery Analysis")
    delivery_results = run_delivery_analysis(delivery)

    # ── STEP 8: Reservation Analysis ────────────────────────────────
    logger.info("STEP 8/10 → Reservation Analysis")
    reservation_results = run_reservation_analysis(reservations, receipts)

    # ── STEP 9: Operational Flags ───────────────────────────────────
    logger.info("STEP 9/10 → Operational Flags")
    ops_results = run_operational_flags(receipts, items, products, payments)

    # ── STEP 10: Visualization ──────────────────────────────────────
    if not skip_charts:
        logger.info("STEP 10/10 → Chart Generation")
        charts = generate_all_charts(
            sales_results, menu_results, payment_results,
            labor_results, delivery_results, reservation_results,
            ops_results, daily_summary, chart_out,
        )
        logger.info(f"  Generated {len(charts)} charts → {chart_out}")
    else:
        logger.info("STEP 10/10 → Charts SKIPPED")
        charts = {}

    # ── Report Compilation ──────────────────────────────────────────
    logger.info("Compiling final report...")
    report = compile_report_data(
        sales_results, menu_results, payment_results,
        labor_results, delivery_results, reservation_results,
        ops_results, RESTAURANT_CONFIG,
    )

    # Export JSON
    json_path = export_report_json(report, str(out / "report_data.json"))

    elapsed = time.time() - start
    logger.info("=" * 70)
    logger.info(f"  Pipeline complete in {elapsed:.1f}s")
    logger.info(f"  Output directory: {out}")
    logger.info(f"  Report JSON:      {json_path}")
    if charts:
        logger.info(f"  Charts:           {len(charts)} files in {chart_out}")
    logger.info("=" * 70)

    # ── Console Summary ─────────────────────────────────────────────
    _print_summary(report)

    return report


def _print_summary(report: Dict[str, Any]) -> None:
    """Print a human-readable summary to console."""
    es = report["executive_summary"]
    print("\n" + "─" * 60)
    print(f"  {es['restaurant_name']} — {es['period']}")
    print("─" * 60)

    print("\n  KEY METRICS:")
    for kpi in es["kpis"]:
        status = kpi.get("status", "")
        icon = "✅" if status == "good" else "⚠️ " if status == "warning" else "  "
        if kpi["format"] == "currency":
            val = f"${kpi['value']:,.2f}"
        elif kpi["format"] == "percent":
            val = f"{kpi['value']:.1%}"
        elif kpi["format"] == "integer":
            val = f"{kpi['value']:,}"
        else:
            val = str(kpi["value"])
        print(f"  {icon} {kpi['metric']:.<25} {val}")

    print("\n  TOP FINDINGS:")
    for i, f in enumerate(es["top_findings"][:5], 1):
        print(f"  {i}. [{f['category']}] {f['finding'][:100]}...")

    print("\n  TOP RECOMMENDATIONS:")
    for i, r in enumerate(es["top_recommendations"][:5], 1):
        print(f"  {i}. [{r['priority']}] {r['action'][:100]}...")

    # Operational flags
    flags = report.get("operational_flags", {}).get("flags", [])
    if flags:
        print("\n  OPERATIONAL FLAGS:")
        for f in flags:
            icon = "🔴" if f["severity"] == "CRITICAL" else "🟡" if f["severity"] == "WARNING" else "ℹ️"
            print(f"  {icon} [{f['category']}] {f['description'][:100]}...")

    print("\n" + "─" * 60)


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Food Factor — Lightspeed POS Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_lightspeed.py
  python run_lightspeed.py --data-dir ./march_data
  python run_lightspeed.py --skip-charts --verbose
        """,
    )
    parser.add_argument(
        "--data-dir", type=Path, default=None,
        help="Directory containing Lightspeed CSV exports (default: ./data)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output directory for report and charts (default: ./output)",
    )
    parser.add_argument(
        "--skip-charts", action="store_true",
        help="Skip chart generation (analysis only, faster)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    ensure_dirs()
    setup_logging(args.verbose, args.output_dir or OUTPUT_DIR)

    run_pipeline(
        data_dir=args.data_dir,
        skip_charts=args.skip_charts,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
