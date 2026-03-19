"""
pos_analysis/main.py — Food Factor POS Analysis Pipeline
==========================================================
Orchestrates the full analysis pipeline: data ingestion → analysis
→ visualization → cross-domain insights → report export.

Currently supports Square POS.  TouchBistro and Lightspeed modules
will plug in to the same orchestrator pattern.

Usage::

    python -m pos_analysis.main --data-dir /path/to/csvs
    python -m pos_analysis.main --data-dir ./data --output-dir ./reports -v
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from pos_analysis.square.ingest import SquareDataLoader, SquareDataset
from pos_analysis.square.analysis import (
    DeliveryAnalyzer,
    OperationalFlagAnalyzer,
    PaymentAnalyzer,
    ReservationAnalyzer,
    SalesAnalyzer,
)
from pos_analysis.square.labor import LaborAnalyzer
from pos_analysis.square.visualizations import generate_all_charts
from pos_analysis.shared.menu_engineering import MenuEngineeringAnalyzer
from pos_analysis.shared.cross_domain import generate_cross_domain_insights
from pos_analysis.shared.exporters import ReportExporter

logger = logging.getLogger("food_factor.main")


# ─────────────────────────────────────────────
# Report Generator
# ─────────────────────────────────────────────
class ReportGenerator:
    """
    End-to-end report generation pipeline.

    Steps:
        1. Load & normalize Square data (ingestion)
        2. Run all analysis modules
        3. Generate all charts (visualization)
        4. Compile executive summary
        5. Generate cross-domain insights
        6. Export structured report data (JSON + charts)
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(".")
        self.output_dir = Path(output_dir) if output_dir else settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)

        self.data: Optional[SquareDataset] = None
        self.results: Dict[str, Any] = {}
        self.executive_summary: Dict[str, Any] = {}
        self.cross_domain_insights: List[Dict[str, Any]] = []

    def generate(self) -> Dict[str, Any]:
        """Run the full pipeline and return structured report data."""
        logger.info("=" * 60)
        logger.info("FOOD FACTOR REPORT GENERATION — %s", settings.RESTAURANT_NAME)
        logger.info("Period: %s", settings.REPORT_PERIOD)
        logger.info("=" * 60)

        # Step 1: Load data
        logger.info("Step 1/6: Loading data...")
        loader = SquareDataLoader(data_dir=self.data_dir)
        self.data = loader.load_all()
        self._log_data_summary()

        # Step 2: Run analysis modules
        logger.info("Step 2/6: Running analysis modules...")
        self._run_analyses()

        # Step 3: Generate charts
        logger.info("Step 3/6: Generating charts...")
        chart_paths = generate_all_charts(
            self.results, output_dir=str(self.charts_dir),
        )
        self.results["chart_paths"] = {
            k: str(v) for k, v in chart_paths.items() if isinstance(v, Path)
        }

        # Step 4: Cross-domain insights
        logger.info("Step 4/6: Generating cross-domain insights...")
        self.cross_domain_insights = generate_cross_domain_insights(self.results)

        # Step 5: Compile executive summary
        logger.info("Step 5/6: Compiling executive summary...")
        exporter = ReportExporter(output_dir=self.output_dir)
        self.executive_summary = exporter.compile_executive_summary(
            self.results, self.cross_domain_insights,
        )

        # Step 6: Export report data
        logger.info("Step 6/6: Exporting report data...")
        report = exporter.compile_report(
            data_summary=self.data.summary(),
            executive_summary=self.executive_summary,
            cross_domain_insights=self.cross_domain_insights,
            results=self.results,
        )
        exporter.export_json(report)

        logger.info("=" * 60)
        logger.info("Report generation complete!")
        logger.info("Output directory: %s", self.output_dir)
        logger.info("Charts: %d files in %s", len(chart_paths), self.charts_dir)
        logger.info("=" * 60)

        return report

    # ─── internal helpers ─────────────────────

    def _run_analyses(self) -> None:
        """Execute all analysis modules."""
        d = self.data

        self.results["sales"] = SalesAnalyzer(d).run_all()
        logger.info("  ✓ Sales analysis complete")

        self.results["menu"] = MenuEngineeringAnalyzer(d.items).run_all()
        logger.info("  ✓ Menu engineering complete")

        self.results["payments"] = PaymentAnalyzer(d).run_all()
        logger.info("  ✓ Payment analysis complete")

        self.results["labor"] = LaborAnalyzer(d).run_all()
        logger.info("  ✓ Labor analysis complete")

        self.results["delivery"] = DeliveryAnalyzer(d).run_all()
        logger.info("  ✓ Delivery analysis complete")

        self.results["reservations"] = ReservationAnalyzer(d).run_all()
        logger.info("  ✓ Reservation analysis complete")

        self.results["ops_flags"] = OperationalFlagAnalyzer(d).run_all()
        logger.info("  ✓ Operational flags complete")

    def _log_data_summary(self) -> None:
        """Log data load summary."""
        summary = self.data.summary()
        logger.info("Data loaded successfully:")
        for table, count in summary.items():
            logger.info("  %s: %s rows", table, f"{count:,}")

    # ─── console output ──────────────────────

    def print_summary(self) -> None:
        """Print a formatted executive summary to stdout."""
        es = self.executive_summary
        if not es:
            print("No report generated yet. Call .generate() first.")
            return

        print("\n" + "=" * 60)
        print(f"  FOOD FACTOR — {es['restaurant']} | {es['period']}")
        print("=" * 60)

        k = es["kpis"]
        print("\n📊 KEY METRICS")
        print("-" * 40)
        print(f"  Net Sales:          ${k['net_sales']:>12,.0f}")
        print(f"  Avg Daily Revenue:  ${k['avg_daily_revenue']:>12,.0f}")
        print(f"  Avg Check Size:     ${k['avg_check_size']:>12,.2f}")
        print(f"  Total Transactions: {k['total_transactions']:>13,}")
        print(f"  Labor %:            {k['labor_pct']:>12.1%}")
        print(f"  SPLH:               ${k['splh']:>12,.0f}")
        print(f"  Delivery Margin:    {k['delivery_margin']:>12.1%}")
        print(f"  No-Show Rate:       {k['noshow_rate']:>12.1%}")
        print(f"  Menu Stars/Dogs:    {k['menu_stars']}/{k['menu_dogs']}")

        print("\n🔍 KEY FINDINGS")
        print("-" * 40)
        for i, f in enumerate(es["findings"], 1):
            print(f"  {i}. {f}")

        print("\n💡 RECOMMENDATIONS")
        print("-" * 40)
        for i, r in enumerate(es["recommendations"], 1):
            print(f"  {i}. {r}")

        if self.cross_domain_insights:
            print("\n🔗 CROSS-DOMAIN INSIGHTS")
            print("-" * 40)
            for insight in self.cross_domain_insights:
                print(f"  [{' + '.join(insight['sources'])}]")
                print(f"  {insight['title']}: {insight['insight']}")
                print()

        flags = self.results.get("ops_flags", {}).get("summary_flags", [])
        if flags:
            print("⚠️  OPERATIONAL FLAGS")
            print("-" * 40)
            for flag in flags:
                icon = {"WARNING": "🔴", "REVIEW": "🟡"}.get(flag["severity"], "🟢")
                print(f"  {icon} [{flag['area']}] {flag['message']}")

        print("\n" + "=" * 60)


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────
def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-32s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Food Factor — POS Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m pos_analysis.main --data-dir ./data
    python -m pos_analysis.main --data-dir ./data --output-dir ./reports -v
        """,
    )
    parser.add_argument(
        "--data-dir", "-d", type=str, default=None,
        help="Directory containing POS CSV exports",
    )
    parser.add_argument(
        "--output-dir", "-o", type=str, default=None,
        help="Output directory for report and charts (default: ./output)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    try:
        report = ReportGenerator(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
        )
        report.generate()
        report.print_summary()
    except FileNotFoundError as exc:
        logger.error("Data files not found:\n%s", exc)
        logger.error("Verify --data-dir points to the POS CSV export directory.")
        sys.exit(1)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
