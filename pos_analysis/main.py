"""
Food Factor Analytics — POS Analysis CLI Entry Point

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

logger = logging.getLogger("food_factor")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the analysis pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_square(data_dir: Path, output_dir: Optional[Path] = None) -> None:
    """Run the Square POS analysis pipeline."""
    from pos_analysis.square.main import main as square_main

    logger.info("Starting Square POS analysis pipeline")
    logger.info("Data directory: %s", data_dir)
    # Square's main() reads from its own settings; we override if needed
    square_main()


def run_touchbistro(data_dir: Path, output_dir: Optional[Path] = None) -> None:
    """Run the TouchBistro POS analysis pipeline."""
    from pos_analysis.touchbistro.ingest import load_all
    from pos_analysis.touchbistro.analysis import (
        run_sales_analysis,
        run_payment_analysis,
        run_operational_flags,
    )

    logger.info("Starting TouchBistro POS analysis pipeline")
    logger.info("Data directory: %s", data_dir)

    # Load data
    datasets = load_all(str(data_dir))
    logger.info("Loaded %d datasets", len(datasets))

    # Run analyses
    sales_results = run_sales_analysis(datasets)
    logger.info("Sales analysis complete: %d metrics", len(sales_results))

    payment_results = run_payment_analysis(datasets)
    logger.info("Payment analysis complete: %d metrics", len(payment_results))

    ops_results = run_operational_flags(datasets)
    logger.info("Operational flags complete: %d metrics", len(ops_results))

    logger.info("TouchBistro analysis pipeline finished")


def run_lightspeed(data_dir: Path, output_dir: Optional[Path] = None) -> None:
    """Run the Lightspeed POS analysis pipeline."""
    from pos_analysis.lightspeed.ingest import load_all_csvs

    logger.info("Starting Lightspeed POS analysis pipeline")
    logger.info("Data directory: %s", data_dir)

    datasets = load_all_csvs(str(data_dir))
    logger.info("Loaded Lightspeed datasets")

    # Import and run analysis modules
    from pos_analysis.lightspeed.analysis import (
        run_revenue_analysis,
        run_payment_analysis,
    )
    from pos_analysis.lightspeed.labor import run_labor_analysis

    revenue = run_revenue_analysis(datasets)
    logger.info("Revenue analysis complete")

    payments = run_payment_analysis(datasets)
    logger.info("Payment analysis complete")

    labor = run_labor_analysis(datasets)
    logger.info("Labor analysis complete")

    logger.info("Lightspeed analysis pipeline finished")


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
        help="Path to output directory (default: ./outputs/)",
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

    output_dir = args.output_dir.resolve() if args.output_dir else None

    runner = SYSTEM_RUNNERS[args.system]
    try:
        runner(data_dir, output_dir)
    except Exception:
        logger.exception("Pipeline failed for %s", args.system)
        sys.exit(1)

    logger.info("Pipeline completed successfully for %s", args.system)


if __name__ == "__main__":
    main()
