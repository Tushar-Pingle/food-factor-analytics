"""
Food Factor Analytics — POS Analysis CLI Entry Point

Unified pipeline: Ingest → Analyze → Chart → Standardize → Validate.

Usage:
    python -m pos_analysis.main --system square --data-dir ./data/client/
    python -m pos_analysis.main --system touchbistro --data-dir ./data/client/
    python -m pos_analysis.main --system lightspeed --data-dir ./data/client/
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from config.settings import OUTPUT_DIR

logger = logging.getLogger("food_factor")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the analysis pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ── Square ───────────────────────────────────────────────────────────────

def run_square(data_dir: Path, output_dir: Path) -> None:
    """Run the Square POS analysis pipeline with standardization."""
    from pos_analysis.square.ingest import SquareDataLoader
    from pos_analysis.square.analysis import (
        SalesAnalyzer,
        PaymentAnalyzer,
        DeliveryAnalyzer,
        ReservationAnalyzer,
        OperationalFlagAnalyzer,
    )
    from pos_analysis.square.labor import LaborAnalyzer
    from pos_analysis.shared.menu_engineering import MenuEngineeringAnalyzer
    from pos_analysis.square.standardize import standardize_all

    logger.info("Starting Square POS analysis pipeline")
    logger.info("Data directory: %s", data_dir)

    # Step 1: Ingest
    loader = SquareDataLoader(str(data_dir))
    dataset = loader.load_all()
    logger.info("Loaded Square data: %s", dataset.summary())

    # Step 2: Analyze
    results = {}
    results["sales"] = SalesAnalyzer(dataset).run_all()
    logger.info("Sales analysis complete")

    results["payments"] = PaymentAnalyzer(dataset).run_all()
    logger.info("Payment analysis complete")

    results["labor"] = LaborAnalyzer(dataset).run_all()
    logger.info("Labor analysis complete")

    results["delivery"] = DeliveryAnalyzer(dataset).run_all()
    logger.info("Delivery analysis complete")

    results["reservations"] = ReservationAnalyzer(dataset).run_all()
    logger.info("Reservation analysis complete")

    results["ops_flags"] = OperationalFlagAnalyzer(dataset).run_all()
    logger.info("Operational flags complete")

    try:
        results["menu"] = MenuEngineeringAnalyzer(dataset.items).run_all()
        logger.info("Menu engineering complete")
    except Exception as e:
        logger.warning("Menu engineering skipped: %s", e)
        results["menu"] = {}

    # Step 3: Charts
    try:
        from pos_analysis.square.visualizations import generate_all_charts
        chart_dir = output_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)
        generate_all_charts(results, str(chart_dir))
        logger.info("Charts generated")
    except Exception as e:
        logger.warning("Chart generation failed: %s", e)

    # Step 4: Standardize
    standardize_all(results, dataset, output_dir)
    logger.info("Output standardized")


# ── TouchBistro ──────────────────────────────────────────────────────────

def run_touchbistro(data_dir: Path, output_dir: Path) -> None:
    """Run the TouchBistro POS analysis pipeline with standardization."""
    from pos_analysis.touchbistro.ingest import load_all
    from pos_analysis.touchbistro.analysis import (
        run_sales_analysis,
        run_payment_analysis,
        run_operational_flags,
    )
    from pos_analysis.touchbistro.standardize import standardize_all

    logger.info("Starting TouchBistro POS analysis pipeline")
    logger.info("Data directory: %s", data_dir)

    # Step 1: Ingest
    datasets = load_all(str(data_dir))
    logger.info("Loaded %d datasets", len(datasets))

    # Step 2: Analyze
    detailed_sales = datasets["detailed_sales"]
    results = {}
    results["sales"] = run_sales_analysis(detailed_sales)
    logger.info("Sales analysis complete: %d metrics", len(results["sales"]))

    results["payments"] = run_payment_analysis(datasets["payments"], detailed_sales)
    logger.info("Payment analysis complete: %d metrics", len(results["payments"]))

    results["ops_flags"] = run_operational_flags(detailed_sales)
    logger.info("Operational flags complete: %d metrics", len(results["ops_flags"]))

    # Step 3: Charts
    try:
        from pos_analysis.touchbistro.visualizations import generate_all_charts
        chart_dir = output_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)
        generate_all_charts(results, str(chart_dir))
        logger.info("Charts generated")
    except Exception as e:
        logger.warning("Chart generation failed: %s", e)

    # Step 4: Standardize
    standardize_all(results, datasets, output_dir)
    logger.info("Output standardized")


# ── Lightspeed ───────────────────────────────────────────────────────────

def run_lightspeed(data_dir: Path, output_dir: Path) -> None:
    """Run the Lightspeed POS analysis pipeline with standardization."""
    from pos_analysis.lightspeed.ingest import load_all
    from pos_analysis.lightspeed.analysis import (
        run_sales_analysis,
        run_payment_analysis,
        run_delivery_analysis,
        run_reservation_analysis,
        run_operational_flags,
    )
    from pos_analysis.lightspeed.labor import run_labor_analysis
    from pos_analysis.lightspeed.standardize import standardize_all

    logger.info("Starting Lightspeed POS analysis pipeline")
    logger.info("Data directory: %s", data_dir)

    # Step 1: Ingest
    datasets = load_all(data_dir)
    logger.info("Loaded Lightspeed datasets")

    # Unpack DataFrames for analysis functions
    receipts = datasets["receipts"]
    items = datasets["receipt_items"]
    products = datasets["products"]
    payments = datasets["payments"]
    labor = datasets["labor_shifts"]
    delivery = datasets.get("delivery")
    reservations = datasets.get("reservations")

    # Step 2: Analyze
    results = {}
    results["sales"] = run_sales_analysis(receipts, items, products)
    logger.info("Sales analysis complete")

    results["payments"] = run_payment_analysis(payments)
    logger.info("Payment analysis complete")

    total_net_revenue = receipts["Net_Total"].sum()
    results["labor"] = run_labor_analysis(labor, receipts, total_net_revenue)
    logger.info("Labor analysis complete")

    try:
        if delivery is not None and not delivery.empty:
            results["delivery"] = run_delivery_analysis(delivery)
            logger.info("Delivery analysis complete")
        else:
            results["delivery"] = {}
            logger.info("No delivery data — skipped")
    except Exception as e:
        logger.warning("Delivery analysis skipped: %s", e)
        results["delivery"] = {}

    try:
        if reservations is not None and not reservations.empty:
            results["reservations"] = run_reservation_analysis(reservations, receipts)
            logger.info("Reservation analysis complete")
        else:
            results["reservations"] = {}
            logger.info("No reservation data — skipped")
    except Exception as e:
        logger.warning("Reservation analysis skipped: %s", e)
        results["reservations"] = {}

    try:
        results["ops_flags"] = run_operational_flags(receipts, items, products, payments)
        logger.info("Operational flags complete")
    except Exception as e:
        logger.warning("Operational flags skipped: %s", e)
        results["ops_flags"] = {}

    # Step 3: Charts
    try:
        from pos_analysis.lightspeed.visualizations import generate_all_charts
        chart_dir = output_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)
        generate_all_charts(results, str(chart_dir))
        logger.info("Charts generated")
    except Exception as e:
        logger.warning("Chart generation failed: %s", e)

    # Step 4: Standardize
    standardize_all(results, datasets, output_dir)
    logger.info("Output standardized")


# ── Runner dispatch ──────────────────────────────────────────────────────

SYSTEM_RUNNERS = {
    "square": run_square,
    "touchbistro": run_touchbistro,
    "lightspeed": run_lightspeed,
}


def main() -> None:
    """CLI entry point for Food Factor POS analysis."""
    parser = argparse.ArgumentParser(
        prog="food-factor-pos",
        description="Food Factor Analytics — POS Analysis Pipeline",
    )
    parser.add_argument(
        "--system",
        required=True,
        choices=list(SYSTEM_RUNNERS.keys()),
        help="POS system to analyze (square, touchbistro, or lightspeed)",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Path to directory containing POS export CSV files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Path to output directory (default: ./outputs/<system>/)",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip output validation after standardization",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        logger.error("Data directory does not exist: %s", data_dir)
        sys.exit(1)

    # Default output dir: ./outputs/<system>/
    if args.output_dir:
        output_dir = args.output_dir.resolve()
    else:
        output_dir = OUTPUT_DIR / args.system
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run the pipeline (ingest → analyze → chart → standardize)
    runner = SYSTEM_RUNNERS[args.system]
    try:
        runner(data_dir, output_dir)
    except Exception:
        logger.exception("Pipeline failed for %s", args.system)
        sys.exit(1)

    # Step 5: Validate
    if not args.skip_validate:
        from pos_analysis.shared.validate_output import validate_output_dir
        result = validate_output_dir(output_dir)
        print(result.summary())
        if not result.passed:
            logger.warning("Validation found %d failures", len(result.failures))
    else:
        logger.info("Validation skipped (--skip-validate)")

    # Step 6: Summary
    logger.info("Pipeline completed successfully for %s", args.system)
    logger.info("Output directory: %s", output_dir)


if __name__ == "__main__":
    main()
