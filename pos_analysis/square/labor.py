"""
pos_analysis/square/labor.py — Square Labor Optimization Analysis
==================================================================
Computes labor cost %, sales per labor hour (SPLH), FOH / BOH split,
overtime patterns, and staffing-vs-sales alignment from Square
timecard exports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from config import settings
from pos_analysis.square.ingest import SquareDataset

logger = logging.getLogger("food_factor.square.labor")


class LaborAnalyzer:
    """
    Labor cost optimization analysis.

    Computes labor %, SPLH, FOH / BOH split, overtime patterns,
    and staffing alignment with sales volume.
    """

    def __init__(self, data: SquareDataset) -> None:
        self.timecards = data.timecards
        self.payments = data.transactions[~data.transactions["is_refund"]].copy()
        self.period_days: int = (data.period_end - data.period_start).days + 1

    def run_all(self) -> Dict[str, Any]:
        """Execute all labor analyses and return combined results."""
        return {
            "kpis":          self.compute_kpis(),
            "daily_labor":   self.daily_labor_vs_sales(),
            "foh_boh_split": self.foh_boh_split(),
            "by_role":       self.cost_by_role(),
            "overtime":      self.overtime_analysis(),
            "splh_trend":    self.splh_trend(),
            "dow_staffing":  self.dow_staffing_alignment(),
        }

    # ─── KPIs ────────────────────────────────

    def compute_kpis(self) -> Dict[str, float]:
        """Core labor KPIs."""
        total_labor = self.timecards["labor_cost"].sum()
        total_hours = self.timecards["paid_hours"].sum()
        total_ot = self.timecards["overtime_hours"].sum()
        net_sales = self.payments["net_sales"].sum()

        return {
            "total_labor_cost":    round(total_labor, 2),
            "total_paid_hours":    round(total_hours, 1),
            "total_ot_hours":      round(total_ot, 1),
            "labor_pct":           round(total_labor / net_sales, 4) if net_sales > 0 else 0,
            "avg_hourly_cost":     round(total_labor / total_hours, 2) if total_hours > 0 else 0,
            "splh":                round(net_sales / total_hours, 2) if total_hours > 0 else 0,
            "benchmark_labor_pct": settings.BENCHMARKS["labor_cost_pct"],
            "benchmark_splh":      settings.BENCHMARKS["splh_target"],
            "headcount":           self.timecards["team_member"].nunique(),
        }

    # ─── daily / trend methods ────────────────

    def daily_labor_vs_sales(self) -> pd.DataFrame:
        """Daily labor cost alongside daily revenue for alignment."""
        labor_daily = self.timecards.groupby("date_only").agg(
            labor_cost=("labor_cost", "sum"),
            labor_hours=("paid_hours", "sum"),
            staff_count=("team_member", "nunique"),
        ).reset_index()

        sales_daily = self.payments.groupby("date_only").agg(
            net_sales=("net_sales", "sum"),
        ).reset_index()

        merged = pd.merge(
            labor_daily, sales_daily, on="date_only", how="outer",
        ).fillna(0)
        merged["labor_pct"] = np.where(
            merged["net_sales"] > 0,
            merged["labor_cost"] / merged["net_sales"],
            0,
        )
        merged["splh"] = np.where(
            merged["labor_hours"] > 0,
            merged["net_sales"] / merged["labor_hours"],
            0,
        )
        merged["day_of_week"] = pd.to_datetime(merged["date_only"]).dt.day_name()
        return merged.sort_values("date_only")

    def foh_boh_split(self) -> pd.DataFrame:
        """Labor cost split between front-of-house and back-of-house."""
        split = self.timecards.groupby("is_foh").agg(
            labor_cost=("labor_cost", "sum"),
            paid_hours=("paid_hours", "sum"),
            headcount=("team_member", "nunique"),
        ).reset_index()
        split["label"]        = split["is_foh"].map({True: "FOH", False: "BOH"})
        split["pct_of_total"] = split["labor_cost"] / split["labor_cost"].sum()
        return split

    def cost_by_role(self) -> pd.DataFrame:
        """Labor cost breakdown by job title."""
        by_role = self.timecards.groupby("job_title").agg(
            labor_cost=("labor_cost", "sum"),
            paid_hours=("paid_hours", "sum"),
            headcount=("team_member", "nunique"),
            ot_hours=("overtime_hours", "sum"),
        ).reset_index()
        by_role["avg_hourly"]   = by_role["labor_cost"] / by_role["paid_hours"]
        by_role["pct_of_total"] = by_role["labor_cost"] / by_role["labor_cost"].sum()
        return by_role.sort_values("labor_cost", ascending=False)

    def overtime_analysis(self) -> Dict[str, Any]:
        """Overtime frequency, cost, and top offenders."""
        ot = self.timecards[self.timecards["overtime_hours"] > 0].copy()
        ot_by_person = ot.groupby("team_member").agg(
            total_ot_hours=("overtime_hours", "sum"),
            ot_shifts=("overtime_hours", "count"),
            ot_cost=("labor_cost", "sum"),
        ).reset_index().sort_values("total_ot_hours", ascending=False)

        # Incremental OT cost (the 0.5× premium only)
        total_ot_cost = (ot["overtime_hours"] * ot["hourly_rate"] * 0.5).sum()

        return {
            "total_ot_hours":     ot["overtime_hours"].sum(),
            "total_ot_shifts":    len(ot),
            "incremental_ot_cost": round(total_ot_cost, 2),
            "by_person":          ot_by_person,
        }

    def splh_trend(self) -> pd.DataFrame:
        """Sales per labor hour trend by date."""
        daily = self.daily_labor_vs_sales()
        return daily[["date_only", "splh", "net_sales", "labor_hours", "day_of_week"]]

    def dow_staffing_alignment(self) -> pd.DataFrame:
        """Compare staffing levels with revenue by day of week."""
        labor_dow = self.timecards.groupby("day_of_week").agg(
            avg_staff=("team_member", "nunique"),
            avg_hours=("paid_hours", "sum"),
            avg_labor_cost=("labor_cost", "sum"),
        ).reindex(settings.DAY_ORDER).reset_index()

        sales_dow = self.payments.groupby("day_of_week").agg(
            total_sales=("net_sales", "sum"),
        ).reindex(settings.DAY_ORDER).reset_index()

        dates = pd.date_range(
            settings.REPORT_PERIOD_START, settings.REPORT_PERIOD_END,
        )
        day_counts = dates.day_name().value_counts()

        merged = pd.merge(labor_dow, sales_dow, on="day_of_week")
        merged["num_weeks"]       = merged["day_of_week"].map(day_counts)
        merged["avg_daily_sales"] = merged["total_sales"] / merged["num_weeks"]
        merged["avg_daily_labor"] = merged["avg_labor_cost"] / merged["num_weeks"]
        merged["labor_pct"]       = merged["avg_daily_labor"] / merged["avg_daily_sales"]
        return merged
