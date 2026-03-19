"""
pos_analysis/shared/exporters.py — Report Data Export
======================================================
Compiles analysis results into structured report data and
exports to JSON.  POS-agnostic — works with any analysis
results dictionary.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger("food_factor.shared.exporters")


class ReportExporter:
    """
    Compile and export structured report data.

    Handles:
    - Executive summary generation (KPIs, findings, recommendations)
    - Report metadata assembly
    - JSON serialization with Pandas / NumPy type handling
    """

    def __init__(self, output_dir: Path | str | None = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─── executive summary ────────────────────

    def compile_executive_summary(
        self,
        results: Dict[str, Any],
        cross_domain_insights: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build the executive summary from all analysis results.

        Returns headline KPIs, top findings, and top recommendations.
        """
        sales_kpis = results["sales"]["kpis"]
        labor_kpis = results["labor"]["kpis"]
        delivery_kpis = results["delivery"]["kpis"]
        res_kpis = results["reservations"]["kpis"]

        menu_matrix = results["menu"]["matrix"]
        class_counts = menu_matrix["classification"].value_counts().to_dict()

        kpis = {
            "net_sales":          sales_kpis["net_sales"],
            "avg_daily_revenue":  sales_kpis["avg_daily_revenue"],
            "avg_check_size":     sales_kpis["avg_check_size"],
            "total_transactions": sales_kpis["total_transactions"],
            "labor_pct":          labor_kpis["labor_pct"],
            "splh":               labor_kpis["splh"],
            "delivery_margin":    delivery_kpis["effective_margin"],
            "noshow_rate":        res_kpis["noshow_rate"],
            "total_covers":       res_kpis["total_covers"],
            "menu_stars":         class_counts.get("Star", 0),
            "menu_dogs":          class_counts.get("Dog", 0),
        }

        findings = self._generate_findings(
            kpis, sales_kpis, labor_kpis, delivery_kpis, res_kpis,
        )
        recommendations = self._generate_recommendations(kpis, results)

        return {
            "kpis":            kpis,
            "findings":        findings[:5],
            "recommendations": recommendations[:5],
            "period":          settings.REPORT_PERIOD,
            "restaurant":      settings.RESTAURANT_NAME,
        }

    @staticmethod
    def _generate_findings(
        kpis: Dict[str, Any],
        sales: Dict,
        labor: Dict,
        delivery: Dict,
        res: Dict,
    ) -> List[str]:
        """Generate key findings based on analysis results."""
        findings: List[str] = []

        findings.append(
            f"Net sales of ${kpis['net_sales']:,.0f} over {settings.REPORT_PERIOD} "
            f"with an average daily revenue of ${kpis['avg_daily_revenue']:,.0f} "
            f"and average check of ${kpis['avg_check_size']:.2f}."
        )

        labor_status = (
            "below" if kpis["labor_pct"] < settings.BENCHMARKS["labor_cost_pct"]
            else "above"
        )
        findings.append(
            f"Labor cost is {kpis['labor_pct']:.1%} of net sales — "
            f"{labor_status} the {settings.BENCHMARKS['labor_cost_pct']:.0%} "
            f"industry benchmark. SPLH of ${kpis['splh']:.0f} vs. "
            f"target of ${settings.BENCHMARKS['splh_target']:.0f}."
        )

        findings.append(
            f"Delivery effective margin is {kpis['delivery_margin']:.1%} "
            f"(target: >{settings.BENCHMARKS['delivery_margin_min']:.0%}). "
            f"{delivery['completed_orders']} orders completed across platforms."
        )

        noshow_status = (
            "exceeds" if kpis["noshow_rate"] > settings.BENCHMARKS["noshow_rate_target"]
            else "within"
        )
        findings.append(
            f"No-show rate of {kpis['noshow_rate']:.1%} {noshow_status} "
            f"the {settings.BENCHMARKS['noshow_rate_target']:.0%} target. "
            f"{kpis['total_covers']} covers from {res['total_reservations']} reservations."
        )

        findings.append(
            f"Menu analysis identified {kpis['menu_stars']} Stars and "
            f"{kpis['menu_dogs']} Dogs. Dogs are candidates for removal or repricing."
        )

        return findings

    @staticmethod
    def _generate_recommendations(
        kpis: Dict[str, Any],
        results: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable recommendations based on KPIs vs benchmarks."""
        recs: List[str] = []

        if kpis["labor_pct"] > settings.BENCHMARKS["labor_cost_pct"]:
            recs.append(
                "Reduce labor cost by reviewing slow-day staffing. "
                "Monday-Wednesday dinner service may be overstaffed "
                "relative to covers."
            )
        else:
            recs.append(
                "Labor % is healthy. Monitor SPLH during peak periods "
                "to ensure service quality isn't compromised by understaffing."
            )

        if kpis["noshow_rate"] > settings.BENCHMARKS["noshow_rate_target"]:
            recs.append(
                "Implement no-show mitigation: SMS reminders 4hr before "
                "reservation, credit card holds for parties of 4+, and a "
                "waitlist system to backfill cancellations."
            )

        if kpis["delivery_margin"] < settings.BENCHMARKS["delivery_margin_min"]:
            recs.append(
                "Delivery margins are below target. Consider menu price "
                "increases for delivery-only items, negotiate commission "
                "rates, or evaluate whether low-margin platforms should "
                "be dropped."
            )

        if kpis["menu_dogs"] > 3:
            recs.append(
                f"Review {kpis['menu_dogs']} 'Dog' items: consider removing, "
                f"repricing, or repositioning. Replacing with higher-margin "
                f"alternatives could improve food cost by 1-2 points."
            )

        disc_rate = results["sales"]["kpis"]["discount_rate"]
        if disc_rate > settings.BENCHMARKS["discount_rate_max"]:
            recs.append(
                f"Discount rate of {disc_rate:.1%} is above the "
                f"{settings.BENCHMARKS['discount_rate_max']:.0%} threshold. "
                f"Audit discount authority and implement approval workflows."
            )

        return recs

    # ─── full report compilation ──────────────

    def compile_report(
        self,
        data_summary: Dict[str, int],
        executive_summary: Dict[str, Any],
        cross_domain_insights: List[Dict[str, Any]],
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compile the full report data structure."""
        return {
            "metadata": {
                "restaurant":    settings.RESTAURANT_NAME,
                "location":      settings.RESTAURANT_LOCATION,
                "period":        settings.REPORT_PERIOD,
                "generated_at":  datetime.now().isoformat(),
                "pos_system":    settings.POS_SYSTEM,
                "data_summary":  data_summary,
            },
            "executive_summary":      executive_summary,
            "cross_domain_insights":  cross_domain_insights,
            "sales_kpis":             results["sales"]["kpis"],
            "labor_kpis":             results["labor"]["kpis"],
            "delivery_kpis":          results["delivery"]["kpis"],
            "reservation_kpis":       results["reservations"]["kpis"],
            "operational_flags":      results["ops_flags"]["summary_flags"],
            "chart_count":            len(results.get("chart_paths", {})),
        }

    # ─── JSON export ──────────────────────────

    def export_json(self, report: Dict[str, Any]) -> Path:
        """
        Export report data as JSON.

        Handles pandas / numpy type serialization automatically.
        """
        filepath = self.output_dir / "report_data.json"

        def _serialize(obj: Any) -> Any:
            if isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            if isinstance(obj, (pd.Series, pd.DataFrame)):
                return obj.to_dict()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, Path):
                return str(obj)
            raise TypeError(f"Cannot serialize {type(obj)}")

        with open(filepath, "w") as fh:
            json.dump(report, fh, indent=2, default=_serialize)

        logger.info("Report JSON exported: %s", filepath)
        return filepath
