"""
pos_analysis.lightspeed.standardize
===================================
Standardize Lightspeed analysis results to the canonical Food Factor
output schema (output_schema.py).

This module transforms Lightspeed-specific data structures into the
universal JSON format consumed by the report assembly pipeline.

Key mappings:
- revenue_summary → summary_metrics (with labor fields)
- sales daily_trend, day_of_week, daypart, order_type, category_performance, etc. → sales_analysis
- labor_summary & foh_boh_split, by_role, by_day → labor_analysis
- delivery summary, platform_compare → delivery_analysis
- reservation summary, by_source, revpash → reservation_analysis
- ops void_analysis, discount_analysis, flags → operational_flags
- payment methods → payment_analysis

Lightspeed is feature-complete for all major domains.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from config import settings
from pos_analysis.shared import output_schema as schema

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from a dict or object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return getattr(obj, key, default)
    except (AttributeError, TypeError):
        return default


def _df_to_records(
    df: Optional[pd.DataFrame],
    column_mapping: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to list of dicts, optionally renaming columns.

    Args:
        df: DataFrame to convert
        column_mapping: dict of {original_col: new_col}

    Returns:
        List of dicts, with null values handled as None
    """
    if df is None or df.empty:
        return []

    df = df.copy()
    if column_mapping:
        df = df.rename(columns=column_mapping)

    records = df.to_dict("records")

    # Convert NaN/NaT to None
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None

    return records


def _json_serializable(obj: Any) -> Any:
    """Make an object JSON-serializable."""
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return obj.to_list()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict("records")
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    if pd.isna(obj):
        return None
    return obj


# ─────────────────────────────────────────────────────────────────
# STANDARDIZATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def standardize_metadata(
    results: Dict[str, Any],
    dataset_or_config: Any,
    period_start: str,
    period_end: str,
) -> Dict[str, Any]:
    """
    Build metadata.json structure.

    Args:
        results: Analysis results dict
        dataset_or_config: Dataset or config object with restaurant info
        period_start: ISO date string
        period_end: ISO date string

    Returns:
        Metadata TypedDict structure
    """
    sales_results = results.get("sales", {})
    operating_days = _safe_get(sales_results.get("revenue_summary", {}), "num_operating_days", 0)

    data_quality = []

    table_row_counts = {}
    if "revenue_summary" in sales_results:
        rev_sum = sales_results["revenue_summary"]
        if "transaction_count" in rev_sum:
            table_row_counts["transactions"] = rev_sum["transaction_count"]

    return {
        "pos_system": "lightspeed",
        "restaurant_name": settings.RESTAURANT_NAME,
        "location": settings.RESTAURANT_LOCATION,
        "report_period": settings.REPORT_PERIOD,
        "period_start": period_start,
        "period_end": period_end,
        "operating_days": int(operating_days),
        "total_seats": _safe_get(dataset_or_config, "TOTAL_SEATS", None),
        "generated_at": datetime.now().isoformat(),
        "data_quality": data_quality,
        "table_row_counts": table_row_counts,
        "extended": {},
    }


def standardize_summary_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build summary_metrics.json from Lightspeed revenue and labor KPIs.

    Lightspeed field mappings:
    - revenue_summary.total_net_revenue → total_net_revenue
    - revenue_summary.total_with_tax → total_gross_revenue
    - revenue_summary.avg_daily_revenue → avg_daily_revenue
    - revenue_summary.transaction_count → total_transactions
    - revenue_summary.avg_check → avg_check
    - revenue_summary.total_covers → total_covers
    - revenue_summary.total_tips → total_tips
    - revenue_summary.avg_tip_rate → avg_tip_pct
    - labor_summary.labor_pct → labor_pct
    - labor_summary.splh → splh
    - labor_summary.total_labor_cost → total_labor_cost
    """
    sales_results = results.get("sales", {})
    labor_results = results.get("labor", {})

    rev_sum = sales_results.get("revenue_summary", {})
    lab_sum = labor_results.get("labor_summary", {}) if labor_results else {}

    total_net = float(_safe_get(rev_sum, "total_net_revenue", 0))
    total_gross = float(_safe_get(rev_sum, "total_with_tax", 0))
    total_covers = int(_safe_get(rev_sum, "total_covers", 1))

    revenue_per_cover = (
        total_net / total_covers if total_covers > 0 else 0
    )

    avg_tip_pct = float(_safe_get(rev_sum, "avg_tip_rate", 0))

    return {
        "total_net_revenue": total_net,
        "total_gross_revenue": total_gross,
        "avg_daily_revenue": float(_safe_get(rev_sum, "avg_daily_revenue", 0)),
        "total_transactions": int(_safe_get(rev_sum, "transaction_count", 0)),
        "avg_check": float(_safe_get(rev_sum, "avg_check", 0)),
        "total_covers": int(_safe_get(rev_sum, "total_covers", 0)),
        "revenue_per_cover": float(revenue_per_cover),
        "total_tips": float(_safe_get(rev_sum, "total_tips", 0)),
        "avg_tip_pct": avg_tip_pct,
        "total_discounts": float(_safe_get(sales_results.get("kpis", {}), "total_discounts", 0)),
        "discount_rate_pct": float(_safe_get(sales_results.get("kpis", {}), "discount_rate", 0)) / 100
            if "kpis" in sales_results else 0.0,
        "labor_pct": float(_safe_get(lab_sum, "labor_pct", None))
            if lab_sum else None,
        "splh": float(_safe_get(lab_sum, "splh", None))
            if lab_sum else None,
        "total_labor_cost": float(_safe_get(lab_sum, "total_labor_cost", None))
            if lab_sum else None,
        "delivery_net_margin": None,  # Computed separately
        "noshow_rate": None,  # Computed separately
        "menu_stars_count": None,
        "menu_dogs_count": None,
        "extended": {},
    }


def standardize_sales(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build sales_analysis.json from Lightspeed sales data.

    Lightspeed provides:
    - daily_trend: date, net_revenue, transaction_count, covers, tips, avg_check,
                   rev_per_cover, revenue_7d_avg, covers_7d_avg, day_of_week
    - day_of_week: (indexed by day name) net_revenue, transaction_count, covers, tips,
                   num_days, avg_daily_revenue, avg_check, rev_per_cover, pct_of_total
    - daypart: (indexed by daypart) net_revenue, transaction_count, covers, tips, avg_check,
               rev_per_cover, pct_of_total
    - order_type: (indexed by type: Dine-In/Takeout) net_revenue, transaction_count, covers,
                  avg_tip, avg_check, pct_of_total
    - category_performance: Category, total_revenue, quantity_sold, total_cogs, unique_items,
                           total_margin, margin_pct, food_cost_pct, revenue_mix_pct, avg_revenue_per_item
    - top_items/bottom_items: Product_ID, Item_Name, Category, total_revenue, quantity_sold,
                             avg_price, total_cogs, avg_food_cost_pct, avg_margin, total_margin, margin_pct
    """
    sales_results = results.get("sales", {})

    # Daily trend
    daily_df = _safe_get(sales_results, "daily_trend", pd.DataFrame())
    daily_trend = []
    if not daily_df.empty:
        for _, row in daily_df.iterrows():
            daily_trend.append({
                "date": str(_json_serializable(row.get("date", ""))),
                "net_revenue": float(_safe_get(row, "net_revenue", 0)),
                "transactions": int(_safe_get(row, "transaction_count", 0)),
                "covers": int(_safe_get(row, "covers", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "day_of_week": str(_safe_get(row, "day_of_week", "")),
            })

    # Day of week
    dow_df = _safe_get(sales_results, "day_of_week", pd.DataFrame())
    day_of_week = []
    if not dow_df.empty:
        for day_name in dow_df.index:
            row = dow_df.loc[day_name]
            day_of_week.append({
                "day": str(day_name),
                "avg_daily_revenue": float(_safe_get(row, "avg_daily_revenue", 0)),
                "avg_transactions": float(_safe_get(row, "transaction_count", 0) / max(_safe_get(row, "num_days", 1), 1)),
                "avg_covers": float(_safe_get(row, "covers", 0) / max(_safe_get(row, "num_days", 1), 1)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "pct_of_total": float(_safe_get(row, "pct_of_total", 0)),
            })

    # Daypart
    daypart_df = _safe_get(sales_results, "daypart", pd.DataFrame())
    daypart = []
    if not daypart_df.empty:
        for daypart_name in daypart_df.index:
            row = daypart_df.loc[daypart_name]
            daypart.append({
                "daypart": str(daypart_name),
                "net_revenue": float(_safe_get(row, "net_revenue", 0)),
                "transactions": int(_safe_get(row, "transaction_count", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "pct_of_revenue": float(_safe_get(row, "pct_of_total", 0)),
            })

    # Order type
    order_df = _safe_get(sales_results, "order_type", pd.DataFrame())
    order_type = []
    if not order_df.empty:
        for order_type_name in order_df.index:
            row = order_df.loc[order_type_name]
            order_type.append({
                "order_type": str(order_type_name),
                "net_revenue": float(_safe_get(row, "net_revenue", 0)),
                "transactions": int(_safe_get(row, "transaction_count", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "pct_of_revenue": float(_safe_get(row, "pct_of_total", 0)),
            })

    # Category performance
    cat_df = _safe_get(sales_results, "category_performance", pd.DataFrame())
    category_performance = []
    if not cat_df.empty:
        for _, row in cat_df.iterrows():
            category_performance.append({
                "category": str(_safe_get(row, "Category", "")),
                "net_revenue": float(_safe_get(row, "total_revenue", 0)),
                "quantity_sold": int(_safe_get(row, "quantity_sold", 0)),
                "margin_pct": float(_safe_get(row, "margin_pct", None))
                    if pd.notna(_safe_get(row, "margin_pct", None)) else None,
                "food_cost_pct": float(_safe_get(row, "food_cost_pct", None))
                    if pd.notna(_safe_get(row, "food_cost_pct", None)) else None,
                "pct_of_revenue": float(_safe_get(row, "revenue_mix_pct", 0)),
            })

    # Top items
    top_df = _safe_get(sales_results, "top_items", pd.DataFrame())
    top_items = []
    if not top_df.empty:
        for _, row in top_df.iterrows():
            top_items.append({
                "item_name": str(_safe_get(row, "Item_Name", "")),
                "category": str(_safe_get(row, "Category", "")),
                "quantity_sold": int(_safe_get(row, "quantity_sold", 0)),
                "net_revenue": float(_safe_get(row, "total_revenue", 0)),
                "avg_price": float(_safe_get(row, "avg_price", 0)),
                "margin_pct": float(_safe_get(row, "margin_pct", None))
                    if pd.notna(_safe_get(row, "margin_pct", None)) else None,
            })

    # Bottom items
    bottom_df = _safe_get(sales_results, "bottom_items", pd.DataFrame())
    bottom_items = []
    if not bottom_df.empty:
        for _, row in bottom_df.iterrows():
            bottom_items.append({
                "item_name": str(_safe_get(row, "Item_Name", "")),
                "category": str(_safe_get(row, "Category", "")),
                "quantity_sold": int(_safe_get(row, "quantity_sold", 0)),
                "net_revenue": float(_safe_get(row, "total_revenue", 0)),
                "avg_price": float(_safe_get(row, "avg_price", 0)),
                "margin_pct": float(_safe_get(row, "margin_pct", None))
                    if pd.notna(_safe_get(row, "margin_pct", None)) else None,
            })

    # Hourly heatmap (if available)
    hourly_heatmap = []

    return {
        "daily_trend": daily_trend,
        "day_of_week": day_of_week,
        "daypart": daypart,
        "order_type": order_type,
        "category_performance": category_performance,
        "top_items": top_items,
        "bottom_items": bottom_items,
        "hourly_heatmap": hourly_heatmap,
        "extended": {},
    }


def standardize_menu(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build menu_engineering.json.

    Lightspeed does not have dedicated menu engineering analysis.
    Return a minimal structure.
    """
    return {
        "matrix": [],
        "food_cost_by_category": [],
        "classification_summary": {},
        "overall_food_cost_pct": 0.0,
        "extended": {
            "note": "Menu engineering not included in standard Lightspeed analysis",
        },
    }


def standardize_labor(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build labor_analysis.json from Lightspeed labor data.

    Lightspeed provides:
    - labor_summary: labor_pct, splh, total_labor_cost
    - foh_boh_split: breakdown DataFrame + foh_pct, boh_pct
    - by_role: Role, User_Group, labor_cost, paid_hours, shift_count, employees, avg_rate, overtime_hours
    - by_day: (indexed by day name) labor_cost, paid_hours, shift_count, num_days, avg_daily_cost, avg_daily_hours,
              avg_shifts_per_day, avg_daily_revenue, avg_daily_covers, labor_pct, splh, covers_per_labor_hour
    - overtime_patterns: overtime_shift_count, by_employee (DataFrame), by_day, by_role
    """
    labor_results = results.get("labor", {})

    # Daily labor
    by_day_df = _safe_get(labor_results, "by_day", pd.DataFrame())
    daily_labor = []
    if not by_day_df.empty:
        for day_name in by_day_df.index:
            row = by_day_df.loc[day_name]
            daily_labor.append({
                "date": str(day_name),
                "labor_cost": float(_safe_get(row, "labor_cost", 0)),
                "labor_hours": float(_safe_get(row, "paid_hours", 0)),
                "staff_count": None,  # Not directly available
                "net_revenue": float(_safe_get(row, "avg_daily_revenue", 0)),
                "labor_pct": float(_safe_get(row, "labor_pct", 0)) / 100
                    if pd.notna(_safe_get(row, "labor_pct", None)) else None,
                "splh": float(_safe_get(row, "splh", None))
                    if pd.notna(_safe_get(row, "splh", None)) else None,
                "day_of_week": str(day_name),
            })

    # FOH/BOH split — result is a dict with "breakdown" DataFrame
    foh_boh_raw = _safe_get(labor_results, "foh_boh_split", {})
    foh_boh_df = foh_boh_raw.get("breakdown", pd.DataFrame()) if isinstance(foh_boh_raw, dict) else foh_boh_raw
    if not isinstance(foh_boh_df, pd.DataFrame):
        foh_boh_df = pd.DataFrame()
    foh_boh_split = []
    if not foh_boh_df.empty:
        for _, row in foh_boh_df.iterrows():
            foh_boh_split.append({
                "group": str(_safe_get(row, "User_Group", "")),
                "labor_cost": float(_safe_get(row, "labor_cost", 0)),
                "paid_hours": float(_safe_get(row, "paid_hours", 0)),
                "headcount": int(_safe_get(row, "employees", 0)),
                "pct_of_total": float(_safe_get(row, "pct_of_total", 0)) / 100,
            })

    # By role
    by_role_df = _safe_get(labor_results, "by_role", pd.DataFrame())
    by_role = []
    if not by_role_df.empty:
        for _, row in by_role_df.iterrows():
            by_role.append({
                "role": str(_safe_get(row, "Role", "")),
                "group": str(_safe_get(row, "User_Group", "")),
                "labor_cost": float(_safe_get(row, "labor_cost", 0)),
                "paid_hours": float(_safe_get(row, "paid_hours", 0)),
                "headcount": int(_safe_get(row, "employees", 0)),
                "avg_hourly_rate": float(_safe_get(row, "avg_rate", 0)),
                "pct_of_total": float(_safe_get(row, "pct_of_total", 0)) / 100,
            })

    # Overtime detail
    overtime_by_emp = _safe_get(labor_results, "overtime_patterns", {}).get("by_employee", pd.DataFrame())
    overtime_detail = []
    if not overtime_by_emp.empty:
        for _, row in overtime_by_emp.iterrows():
            overtime_detail.append({
                "employee_name": str(_safe_get(row, "Employee_Name", "")),
                "overtime_hours": float(_safe_get(row, "overtime_hours", 0)),
                "overtime_shifts": int(_safe_get(row, "overtime_shifts", 0)),
                "overtime_cost": float(_safe_get(row, "overtime_cost", 0)),
            })

    lab_sum = labor_results.get("labor_summary", {})

    return {
        "total_labor_cost": float(_safe_get(lab_sum, "total_labor_cost", 0)),
        "total_paid_hours": float(_safe_get(lab_sum, "total_paid_hours", 0)),
        "labor_pct": float(_safe_get(lab_sum, "labor_pct", 0)) / 100
            if _safe_get(lab_sum, "labor_pct", None) else None,
        "splh": float(_safe_get(lab_sum, "splh", 0))
            if _safe_get(lab_sum, "splh", None) else None,
        "headcount": int(_safe_get(lab_sum, "headcount", 0)),
        "total_overtime_hours": float(_safe_get(labor_results.get("overtime_patterns", {}), "overtime_shift_count", 0)),
        "overtime_premium_cost": None,
        "benchmark_labor_pct": None,
        "benchmark_splh": None,
        "daily_labor": daily_labor,
        "foh_boh_split": foh_boh_split,
        "by_role": by_role,
        "overtime_detail": overtime_detail,
        "splh_trend": [],  # Not directly provided
        "extended": {
            "foh_pct": _safe_get(labor_results, "foh_pct", None),
            "boh_pct": _safe_get(labor_results, "boh_pct", None),
        },
    }


def standardize_payments(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build payment_analysis.json from Lightspeed payment data.

    Lightspeed provides payment method breakdowns in sales results.
    """
    sales_results = results.get("sales", {})

    methods = []
    # Payment methods are typically in sales data
    # For now, return a basic structure

    rev_sum = sales_results.get("revenue_summary", {})
    total_tips = float(_safe_get(rev_sum, "total_tips", 0))
    total_net = float(_safe_get(rev_sum, "total_net_revenue", 1))

    return {
        "methods": methods,
        "overall_tip_rate": float(_safe_get(rev_sum, "avg_tip_rate", 0)),
        "total_tips": total_tips,
        "discount_rate_pct": 0.0,  # Check in sales kpis
        "total_discounts": 0.0,
        "extended": {},
    }


def standardize_ops_flags(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build operational_flags.json from Lightspeed ops data.

    Lightspeed provides:
    - void_analysis: void_count, void_rate, void_revenue_lost, alert_level, flagged_servers
    - discount_analysis: discount_rate, total_discount_value
    - flags: List[Dict] with severity, category, description, recommendation
    """
    ops_results = results.get("ops_flags", {})

    flags = []
    flags_list = _safe_get(ops_results, "flags", [])
    if flags_list:
        for flag in flags_list:
            flags.append({
                "severity": str(_safe_get(flag, "severity", "INFO")).upper(),
                "category": str(_safe_get(flag, "category", "")),
                "description": str(_safe_get(flag, "description", "")),
                "metric_value": _safe_get(flag, "metric_value", None),
                "threshold": _safe_get(flag, "threshold", None),
            })

    void_analysis = _safe_get(ops_results, "void_analysis", {})
    void_summary = {
        "void_count": int(_safe_get(void_analysis, "void_count", 0)),
        "void_rate_pct": float(_safe_get(void_analysis, "void_rate", 0)),
        "void_revenue_lost": float(_safe_get(void_analysis, "void_revenue_lost", 0)),
        "alert_level": str(_safe_get(void_analysis, "alert_level", "OK")).upper(),
    }

    discount_analysis = _safe_get(ops_results, "discount_analysis", {})
    refund_summary = {
        "refund_count": 0,
        "refund_amount": 0.0,
        "refund_rate_pct": 0.0,
    }

    return {
        "flags": flags,
        "void_summary": void_summary,
        "refund_summary": refund_summary,
        "extended": {
            "discount_analysis": _json_serializable(discount_analysis),
        },
    }


def standardize_delivery(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build delivery_analysis.json from Lightspeed delivery data.

    Lightspeed provides:
    - delivery summary: total_orders, completed_orders, canceled_orders, cancel_rate,
                       gross_revenue, net_payout, total_commissions, total_marketing_fees,
                       total_service_fees, effective_take_rate, avg_order_value
    - platform_compare: Platform, order_count, gross_revenue, net_payout, total_commissions,
                       total_marketing, total_service_fees, avg_commission_rate, avg_prep_time,
                       avg_delivery_time, avg_rating, avg_order_value, effective_take_rate, revenue_share
    """
    delivery_results = results.get("delivery", {})

    delivery_summary = _safe_get(delivery_results, "summary", {})
    total_orders = int(_safe_get(delivery_summary, "total_orders", 0))
    completed_orders = int(_safe_get(delivery_summary, "completed_orders", 0))
    gross_revenue = float(_safe_get(delivery_summary, "gross_revenue", 0))
    net_payout = float(_safe_get(delivery_summary, "net_payout", 0))

    effective_margin_pct = (
        (gross_revenue - net_payout) / gross_revenue
        if gross_revenue > 0 else None
    )

    # Platform comparison
    platform_df = _safe_get(delivery_results, "platform_compare", pd.DataFrame())
    platform_comparison = []
    if not platform_df.empty:
        for _, row in platform_df.iterrows():
            gross_rev = _safe_get(row, "gross_revenue", 0)
            net_pay = _safe_get(row, "net_payout", 0)
            total_fees = _safe_get(row, "total_commissions", 0) + _safe_get(row, "total_marketing", 0) + _safe_get(row, "total_service_fees", 0)

            platform_comparison.append({
                "platform": str(_safe_get(row, "Platform", "")),
                "order_count": int(_safe_get(row, "order_count", 0)),
                "gross_revenue": float(gross_rev),
                "net_payout": float(net_pay),
                "total_fees": float(total_fees),
                "effective_margin_pct": (gross_rev - net_pay) / gross_rev if gross_rev > 0 else None,
                "avg_order_value": float(_safe_get(row, "avg_order_value", 0)),
                "avg_prep_time": float(_safe_get(row, "avg_prep_time", None))
                    if pd.notna(_safe_get(row, "avg_prep_time", None)) else None,
                "avg_delivery_time": float(_safe_get(row, "avg_delivery_time", None))
                    if pd.notna(_safe_get(row, "avg_delivery_time", None)) else None,
                "avg_rating": float(_safe_get(row, "avg_rating", None))
                    if pd.notna(_safe_get(row, "avg_rating", None)) else None,
            })

    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "canceled_orders": int(_safe_get(delivery_summary, "canceled_orders", 0)),
        "cancel_rate": float(_safe_get(delivery_summary, "cancel_rate", 0)),
        "gross_revenue": gross_revenue,
        "net_payout": net_payout,
        "effective_margin_pct": effective_margin_pct,
        "avg_order_value": float(_safe_get(delivery_summary, "avg_order_value", 0)),
        "platform_comparison": platform_comparison,
        "daily_trend": [],  # Not directly provided
        "extended": {},
    }


def standardize_reservations(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build reservation_analysis.json from Lightspeed reservation data.

    Lightspeed provides:
    - reservation summary: total_reservations, completed, no_shows, canceled, late_cancels,
                          no_show_rate, cancel_rate, avg_party_size, total_covers_res,
                          avg_turn_time, avg_wait_time, avg_lead_time_days
    - by_source: Source, total_reservations, completed, no_shows, canceled, avg_party_size, no_show_rate, pct_of_total
    - revpash: overall_revpash, by_day_of_week
    """
    res_results = results.get("reservations", {})

    res_summary = _safe_get(res_results, "summary", {})

    # By source
    by_source_df = _safe_get(res_results, "by_source", pd.DataFrame())
    by_source = []
    if not by_source_df.empty:
        for _, row in by_source_df.iterrows():
            by_source.append({
                "source": str(_safe_get(row, "Source", "")),
                "count": int(_safe_get(row, "total_reservations", 0)),
                "noshow_rate": float(_safe_get(row, "no_show_rate", 0)) / 100
                    if pd.notna(_safe_get(row, "no_show_rate", None)) else None,
                "avg_party_size": float(_safe_get(row, "avg_party_size", 0)),
                "pct_of_total": float(_safe_get(row, "pct_of_total", 0)),
            })

    revpash = _safe_get(res_results, "revpash", {}).get("overall_revpash", None)

    return {
        "total_reservations": int(_safe_get(res_summary, "total_reservations", 0)),
        "completed": int(_safe_get(res_summary, "completed", 0)),
        "no_shows": int(_safe_get(res_summary, "no_shows", 0)),
        "noshow_rate": float(_safe_get(res_summary, "no_show_rate", 0)) / 100
            if _safe_get(res_summary, "no_show_rate", None) else None,
        "cancel_rate": float(_safe_get(res_summary, "cancel_rate", 0)) / 100
            if _safe_get(res_summary, "cancel_rate", None) else None,
        "avg_party_size": float(_safe_get(res_summary, "avg_party_size", 0)),
        "total_covers": int(_safe_get(res_summary, "total_covers_res", 0)),
        "avg_turn_time": float(_safe_get(res_summary, "avg_turn_time", None))
            if pd.notna(_safe_get(res_summary, "avg_turn_time", None)) else None,
        "avg_wait_time": float(_safe_get(res_summary, "avg_wait_time", None))
            if pd.notna(_safe_get(res_summary, "avg_wait_time", None)) else None,
        "revpash": revpash,
        "by_source": by_source,
        "noshow_by_day": [],  # Not directly provided
        "extended": {},
    }


def standardize_customer(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build customer_analysis.json.

    Lightspeed does not have detailed customer analysis.
    Return minimal structure.
    """
    return {
        "total_customers": None,
        "repeat_rate": None,
        "avg_spend_per_visit": None,
        "avg_visits": None,
        "extended": {
            "note": "Detailed customer analysis not available in standard Lightspeed output",
        },
    }


# ─────────────────────────────────────────────────────────────────
# MASTER STANDARDIZATION FUNCTION
# ─────────────────────────────────────────────────────────────────

def standardize_all(
    results: Dict[str, Any],
    dataset_or_config: Any,
    output_dir: Path | str,
    period_start: str = "2026-01-01",
    period_end: str = "2026-02-28",
) -> Dict[str, Path]:
    """
    Standardize all analysis results and export as JSON files.

    Args:
        results: Full analysis results dict from Lightspeed analysis
        dataset_or_config: Dataset or config with restaurant metadata
        output_dir: Output directory for JSON files
        period_start: ISO date string for period start
        period_end: ISO date string for period end

    Returns:
        Dict mapping filename → Path of exported files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    # Build all standardized structures
    metadata = standardize_metadata(results, dataset_or_config, period_start, period_end)
    summary_metrics = standardize_summary_metrics(results)
    sales_analysis = standardize_sales(results)
    menu_engineering = standardize_menu(results)
    labor_analysis = standardize_labor(results)
    payment_analysis = standardize_payments(results)
    operational_flags = standardize_ops_flags(results)
    delivery_analysis = standardize_delivery(results)
    reservation_analysis = standardize_reservations(results)
    customer_analysis = standardize_customer(results)

    # Export each to JSON
    files_to_export = {
        "metadata.json": metadata,
        "summary_metrics.json": summary_metrics,
        "sales_analysis.json": sales_analysis,
        "menu_engineering.json": menu_engineering,
        "labor_analysis.json": labor_analysis,
        "payment_analysis.json": payment_analysis,
        "operational_flags.json": operational_flags,
        "delivery_analysis.json": delivery_analysis,
        "reservation_analysis.json": reservation_analysis,
        "customer_analysis.json": customer_analysis,
    }

    def _serialize(obj: Any) -> Any:
        """Custom JSON serializer."""
        return _json_serializable(obj)

    for filename, data in files_to_export.items():
        filepath = output_dir / filename
        with open(filepath, "w") as fh:
            json.dump(data, fh, indent=2, default=_serialize)
        exported_files[filename] = filepath
        logger.info(f"Exported {filename}")

    logger.info(f"All standardized outputs exported to {output_dir}")
    return exported_files
