"""
pos_analysis.lightspeed.labor — Labor Optimization Analysis

Total labor cost, labor % of revenue, SPLH, FOH vs BOH split,
overtime frequency, staffing alignment, and scheduling recommendations.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

from pos_analysis.shared import BENCHMARKS
from pos_analysis.lightspeed import TOTAL_SEATS

logger = logging.getLogger(__name__)


def analyze_labor_summary(
    labor: pd.DataFrame,
    total_net_revenue: float,
) -> Dict[str, Any]:
    """
    Top-line labor KPIs for the reporting period.

    Returns dict with total cost, labor %, SPLH, overtime stats, and benchmarks.
    """
    total_cost = labor["Labor_Cost"].sum()
    total_hours = labor["Paid_Hours"].sum()
    total_ot = labor["Overtime_Hours"].sum()
    total_shifts = labor["Shift_ID"].nunique()
    num_employees = labor["User_ID"].nunique()
    num_days = labor["Date"].dt.date.nunique()

    labor_pct = total_cost / max(total_net_revenue, 1)
    splh = total_net_revenue / max(total_hours, 1)

    ot_cost = labor[labor["Overtime_Hours"] > 0].copy()
    ot_premium = (ot_cost["Overtime_Hours"] * ot_cost["Hourly_Rate"] * 0.5).sum()

    return {
        "total_labor_cost":     round(total_cost, 2),
        "total_paid_hours":     round(total_hours, 1),
        "labor_pct":            round(labor_pct, 4),
        "labor_pct_benchmark":  BENCHMARKS["labor_pct"],
        "labor_pct_alarm":      BENCHMARKS["labor_pct_max"],
        "splh":                 round(splh, 2),
        "splh_benchmark":       BENCHMARKS["splh_target"],
        "total_shifts":         total_shifts,
        "num_employees":        num_employees,
        "avg_shifts_per_day":   round(total_shifts / max(num_days, 1), 1),
        "overtime_hours":       round(total_ot, 1),
        "overtime_shifts":      int((labor["Overtime_Hours"] > 0).sum()),
        "overtime_pct":         round((labor["Overtime_Hours"] > 0).mean(), 4),
        "overtime_premium":     round(ot_premium, 2),
        "avg_hourly_rate":      round(labor["Hourly_Rate"].mean(), 2),
    }


def analyze_foh_boh_split(labor: pd.DataFrame) -> Dict[str, Any]:
    """Front-of-house vs back-of-house labor breakdown."""
    split = labor.groupby("User_Group").agg(
        labor_cost=("Labor_Cost", "sum"),
        paid_hours=("Paid_Hours", "sum"),
        shift_count=("Shift_ID", "nunique"),
        employees=("User_ID", "nunique"),
        overtime_hours=("Overtime_Hours", "sum"),
        avg_rate=("Hourly_Rate", "mean"),
    ).reset_index()

    total_cost = split["labor_cost"].sum()
    split["pct_of_total"] = split["labor_cost"] / max(total_cost, 1)

    return {
        "breakdown": split,
        "foh_pct": round(
            split.loc[split["User_Group"] == "FOH", "pct_of_total"].values[0], 4
        ) if "FOH" in split["User_Group"].values else 0,
        "boh_pct": round(
            split.loc[split["User_Group"] == "BOH", "pct_of_total"].values[0], 4
        ) if "BOH" in split["User_Group"].values else 0,
    }


def analyze_labor_by_role(labor: pd.DataFrame) -> pd.DataFrame:
    """Labor breakdown by role (Server, Bartender, Line Cook, etc.)."""
    role = labor.groupby(["Role", "User_Group"]).agg(
        labor_cost=("Labor_Cost", "sum"),
        paid_hours=("Paid_Hours", "sum"),
        shift_count=("Shift_ID", "nunique"),
        employees=("User_ID", "nunique"),
        avg_rate=("Hourly_Rate", "mean"),
        overtime_hours=("Overtime_Hours", "sum"),
    ).reset_index()

    role["cost_per_shift"] = role["labor_cost"] / role["shift_count"].clip(lower=1)
    role["avg_hours_per_shift"] = role["paid_hours"] / role["shift_count"].clip(lower=1)

    return role.sort_values("labor_cost", ascending=False)


def analyze_labor_by_day(
    labor: pd.DataFrame,
    receipts: pd.DataFrame,
) -> pd.DataFrame:
    """Day-of-week labor analysis with revenue overlay for staffing alignment."""
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    lab_dow = labor.groupby(labor["Date"].dt.day_name()).agg(
        labor_cost=("Labor_Cost", "sum"),
        paid_hours=("Paid_Hours", "sum"),
        shift_count=("Shift_ID", "nunique"),
        num_days=("Date", lambda x: x.dt.date.nunique()),
    ).reindex(dow_order)

    lab_dow["avg_daily_cost"] = lab_dow["labor_cost"] / lab_dow["num_days"].clip(lower=1)
    lab_dow["avg_daily_hours"] = lab_dow["paid_hours"] / lab_dow["num_days"].clip(lower=1)
    lab_dow["avg_shifts_per_day"] = lab_dow["shift_count"] / lab_dow["num_days"].clip(lower=1)

    valid = receipts[~receipts["is_voided"]]
    rev_dow = valid.groupby("day_of_week").agg(
        net_revenue=("Net_Total", "sum"),
        covers=("Number_of_Seats", "sum"),
        num_days=("date", "nunique"),
    ).reindex(dow_order)

    rev_dow["avg_daily_revenue"] = rev_dow["net_revenue"] / rev_dow["num_days"].clip(lower=1)
    rev_dow["avg_daily_covers"] = rev_dow["covers"] / rev_dow["num_days"].clip(lower=1)

    merged = lab_dow.join(rev_dow[["avg_daily_revenue", "avg_daily_covers"]])
    merged["labor_pct"] = merged["avg_daily_cost"] / merged["avg_daily_revenue"].clip(lower=0.01)
    merged["splh"] = merged["avg_daily_revenue"] / merged["avg_daily_hours"].clip(lower=0.01)
    merged["covers_per_labor_hour"] = merged["avg_daily_covers"] / merged["avg_daily_hours"].clip(lower=0.01)

    return merged


def analyze_labor_by_daypart(
    labor: pd.DataFrame,
    receipts: pd.DataFrame,
) -> pd.DataFrame:
    """
    Approximate daypart labor analysis.

    Uses clock-in time to estimate daypart assignment.
    """
    labor = labor.copy()
    labor["clock_in_hour"] = labor["Clock_In"].dt.hour

    def assign_shift_daypart(hour: int) -> str:
        if hour < 15:
            return "Lunch"
        elif hour < 17:
            return "Transition"
        else:
            return "Dinner"

    labor["shift_daypart"] = labor["clock_in_hour"].apply(assign_shift_daypart)

    return labor.groupby("shift_daypart").agg(
        labor_cost=("Labor_Cost", "sum"),
        paid_hours=("Paid_Hours", "sum"),
        shift_count=("Shift_ID", "nunique"),
    ).reset_index()


def analyze_employee_performance(
    labor: pd.DataFrame,
    receipts: pd.DataFrame,
) -> pd.DataFrame:
    """Individual employee efficiency metrics (joins labor hours with revenue for FOH)."""
    valid = receipts[~receipts["is_voided"]]
    server_rev = valid.groupby("Username").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        total_tips=("Tip", "sum"),
    ).reset_index()

    emp_labor = labor.groupby("Employee_Name").agg(
        total_hours=("Paid_Hours", "sum"),
        total_cost=("Labor_Cost", "sum"),
        shift_count=("Shift_ID", "nunique"),
        role=("Role", "first"),
        group=("User_Group", "first"),
        overtime_hours=("Overtime_Hours", "sum"),
    ).reset_index()

    merged = emp_labor.merge(
        server_rev, left_on="Employee_Name", right_on="Username", how="left"
    )

    merged["rev_per_hour"] = np.where(
        merged["total_hours"] > 0,
        merged["net_revenue"].fillna(0) / merged["total_hours"],
        0,
    )
    merged["tips_per_hour"] = np.where(
        merged["total_hours"] > 0,
        merged["total_tips"].fillna(0) / merged["total_hours"],
        0,
    )
    merged["cost_to_revenue_ratio"] = np.where(
        merged["net_revenue"].fillna(0) > 0,
        merged["total_cost"] / merged["net_revenue"],
        np.nan,
    )

    return merged.sort_values("rev_per_hour", ascending=False)


def analyze_overtime_patterns(labor: pd.DataFrame) -> Dict[str, Any]:
    """Overtime deep dive — frequency, cost, and scheduling implications."""
    ot_shifts = labor[labor["Overtime_Hours"] > 0].copy()

    if ot_shifts.empty:
        return {
            "overtime_shift_count": 0,
            "by_employee": pd.DataFrame(),
            "by_day": pd.DataFrame(),
            "by_role": pd.DataFrame(),
        }

    by_emp = ot_shifts.groupby("Employee_Name").agg(
        ot_shift_count=("Shift_ID", "nunique"),
        total_ot_hours=("Overtime_Hours", "sum"),
        avg_ot_per_shift=("Overtime_Hours", "mean"),
        role=("Role", "first"),
    ).sort_values("total_ot_hours", ascending=False).reset_index()

    by_day = ot_shifts.groupby(ot_shifts["Date"].dt.day_name()).agg(
        ot_shift_count=("Shift_ID", "nunique"),
        total_ot_hours=("Overtime_Hours", "sum"),
    ).reset_index()

    by_role = ot_shifts.groupby("Role").agg(
        ot_shift_count=("Shift_ID", "nunique"),
        total_ot_hours=("Overtime_Hours", "sum"),
    ).sort_values("total_ot_hours", ascending=False).reset_index()

    return {
        "overtime_shift_count": len(ot_shifts),
        "by_employee": by_emp,
        "by_day": by_day,
        "by_role": by_role,
    }


def run_labor_analysis(
    labor: pd.DataFrame,
    receipts: pd.DataFrame,
    total_net_revenue: float,
) -> Dict[str, Any]:
    """Execute full labor analysis suite."""
    logger.info("Running labor analysis...")

    results: Dict[str, Any] = {
        "labor_summary":        analyze_labor_summary(labor, total_net_revenue),
        "foh_boh_split":        analyze_foh_boh_split(labor),
        "by_role":              analyze_labor_by_role(labor),
        "by_day":               analyze_labor_by_day(labor, receipts),
        "by_daypart":           analyze_labor_by_daypart(labor, receipts),
        "employee_performance": analyze_employee_performance(labor, receipts),
        "overtime_patterns":    analyze_overtime_patterns(labor),
    }

    logger.info(
        f"Labor analysis complete — "
        f"labor %: {results['labor_summary']['labor_pct']:.1%}, "
        f"SPLH: ${results['labor_summary']['splh']:.2f}"
    )
    return results
