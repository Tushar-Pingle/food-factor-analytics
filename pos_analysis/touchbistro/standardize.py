"""
pos_analysis.touchbistro.standardize
====================================
Standardize TouchBistro analysis results to the canonical Food Factor
output schema (output_schema.py).

This module transforms TouchBistro-specific data structures into the
universal JSON format consumed by the report assembly pipeline.

Key mappings:
- sales.kpis → summary_metrics
- sales.daily_revenue, day_of_week, daypart, order_type, category_performance, etc. → sales_analysis
- ops analysis → operational_flags
- payments analysis → payment_analysis
- Touch-specific data → extended fields

Labor, Delivery, and Reservations are not available in TouchBistro:
- labor_analysis → None / stub (all metrics null)
- delivery_analysis → null
- reservation_analysis → null
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

    operating_days = _safe_get(sales_results.get("kpis", {}), "operating_days", 0)

    data_quality = []
    if "labor" not in results or results.get("labor") is None:
        data_quality.append({
            "table": "labor",
            "issue": "Labor analysis not available in TouchBistro",
            "severity": "info",
        })
    if "delivery" not in results or results.get("delivery") is None:
        data_quality.append({
            "table": "delivery",
            "issue": "Delivery analysis not available in TouchBistro",
            "severity": "info",
        })
    if "reservations" not in results or results.get("reservations") is None:
        data_quality.append({
            "table": "reservations",
            "issue": "Reservation analysis not available in TouchBistro",
            "severity": "info",
        })

    table_row_counts = {}
    for key, value in results.items():
        if isinstance(value, dict) and "kpis" in value:
            if "total_bills" in value.get("kpis", {}):
                table_row_counts["transactions"] = value["kpis"]["total_bills"]

    return {
        "pos_system": "touchbistro",
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
    Build summary_metrics.json from sales KPIs.

    TouchBistro field mappings:
    - sales.kpis.total_net → total_net_revenue
    - sales.kpis.total_gross → total_gross_revenue
    - sales.kpis.avg_daily_revenue → avg_daily_revenue
    - sales.kpis.total_bills → total_transactions
    - sales.kpis.avg_check → avg_check
    - sales.kpis.total_covers → total_covers
    - sales.kpis.total_tips → total_tips
    - sales.kpis.avg_tip_pct → avg_tip_pct
    - sales.kpis.total_discounts → total_discounts
    - sales.kpis.discount_rate_pct → discount_rate_pct
    - labor (stub) → labor_pct=None, splh=None, total_labor_cost=None
    """
    kpis = results.get("sales", {}).get("kpis", {})

    total_net = _safe_get(kpis, "total_net", 0)
    total_gross = _safe_get(kpis, "total_gross", 0)
    total_covers = _safe_get(kpis, "total_covers", 1)

    revenue_per_cover = (
        total_net / total_covers if total_covers > 0 else 0
    )

    return {
        "total_net_revenue": float(_safe_get(kpis, "total_net", 0)),
        "total_gross_revenue": float(_safe_get(kpis, "total_gross", 0)),
        "avg_daily_revenue": float(_safe_get(kpis, "avg_daily_revenue", 0)),
        "total_transactions": int(_safe_get(kpis, "total_bills", 0)),
        "avg_check": float(_safe_get(kpis, "avg_check", 0)),
        "total_covers": int(_safe_get(kpis, "total_covers", 0)),
        "revenue_per_cover": float(revenue_per_cover),
        "total_tips": float(_safe_get(kpis, "total_tips", 0)),
        "avg_tip_pct": float(_safe_get(kpis, "avg_tip_pct", 0)),
        "total_discounts": float(_safe_get(kpis, "total_discounts", 0)),
        "discount_rate_pct": float(_safe_get(kpis, "discount_rate_pct", 0)),
        "labor_pct": None,  # TouchBistro has no labor analysis
        "splh": None,
        "total_labor_cost": None,
        "delivery_net_margin": None,
        "noshow_rate": None,
        "menu_stars_count": None,
        "menu_dogs_count": None,
        "extended": {},
    }


def standardize_sales(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build sales_analysis.json from TouchBistro sales data.

    TouchBistro provides:
    - daily_revenue: Date, net_sales, covers, bill_count, avg_check, revenue_per_cover
    - day_of_week: weekday_name, total_net, total_covers, total_bills, day_count,
                   avg_daily_revenue, avg_daily_covers, avg_check
    - daypart: daypart, total_net, total_covers, total_bills, avg_check, revenue_per_cover, pct_revenue
    - order_type: Order_Type, net_sales, covers, bill_count, avg_check, pct_revenue
    - category_performance: Menu_Category, quantity, gross_sales, net_sales, item_count, pct_revenue, avg_item_revenue
    - top_bottom_items: keys = top_by_revenue, bottom_by_revenue, top_by_quantity, bottom_by_quantity
    - hourly_heatmap: pivot df with weekday_name rows, hour cols, net_sales values
    """
    sales_results = results.get("sales", {})

    # Daily trend
    daily_df = _safe_get(sales_results, "daily_revenue", pd.DataFrame())
    daily_trend = []
    if not daily_df.empty:
        for _, row in daily_df.iterrows():
            daily_trend.append({
                "date": str(_json_serializable(row.get("Date", ""))),
                "net_revenue": float(_safe_get(row, "net_sales", 0)),
                "transactions": int(_safe_get(row, "bill_count", 0)),
                "covers": int(_safe_get(row, "covers", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "day_of_week": pd.Timestamp(row.get("Date")).day_name() if "Date" in row else "",
            })

    # Day of week
    dow_df = _safe_get(sales_results, "day_of_week", pd.DataFrame())
    day_of_week = []
    if not dow_df.empty:
        for _, row in dow_df.iterrows():
            day_of_week.append({
                "day": str(_safe_get(row, "weekday_name", "")),
                "avg_daily_revenue": float(_safe_get(row, "avg_daily_revenue", 0)),
                "avg_transactions": float(_safe_get(row, "total_bills", 0) / max(_safe_get(row, "day_count", 1), 1)),
                "avg_covers": float(_safe_get(row, "avg_daily_covers", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "pct_of_total": 0.0,  # Compute if needed
            })

    # Daypart
    daypart_df = _safe_get(sales_results, "daypart", pd.DataFrame())
    daypart = []
    total_daypart_revenue = daypart_df.get("total_net", pd.Series([0])).sum() if not daypart_df.empty else 1
    if not daypart_df.empty:
        for _, row in daypart_df.iterrows():
            net_rev = _safe_get(row, "total_net", 0)
            daypart.append({
                "daypart": str(_safe_get(row, "daypart", "")),
                "net_revenue": float(net_rev),
                "transactions": int(_safe_get(row, "total_bills", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "pct_of_revenue": float(net_rev / total_daypart_revenue * 100) if total_daypart_revenue > 0 else 0,
            })

    # Order type
    order_df = _safe_get(sales_results, "order_type", pd.DataFrame())
    order_type = []
    total_order_revenue = order_df.get("net_sales", pd.Series([0])).sum() if not order_df.empty else 1
    if not order_df.empty:
        for _, row in order_df.iterrows():
            net_rev = _safe_get(row, "net_sales", 0)
            order_type.append({
                "order_type": str(_safe_get(row, "Order_Type", "")),
                "net_revenue": float(net_rev),
                "transactions": int(_safe_get(row, "bill_count", 0)),
                "avg_check": float(_safe_get(row, "avg_check", 0)),
                "pct_of_revenue": float(net_rev / total_order_revenue * 100) if total_order_revenue > 0 else 0,
            })

    # Category performance
    cat_df = _safe_get(sales_results, "category_performance", pd.DataFrame())
    category_performance = []
    total_cat_revenue = cat_df.get("net_sales", pd.Series([0])).sum() if not cat_df.empty else 1
    if not cat_df.empty:
        for _, row in cat_df.iterrows():
            net_rev = _safe_get(row, "net_sales", 0)
            category_performance.append({
                "category": str(_safe_get(row, "Menu_Category", "")),
                "net_revenue": float(net_rev),
                "quantity_sold": int(_safe_get(row, "quantity", 0)),
                "margin_pct": None,
                "food_cost_pct": None,
                "pct_of_revenue": float(net_rev / total_cat_revenue * 100) if total_cat_revenue > 0 else 0,
            })

    # Top items
    top_items_dict = _safe_get(sales_results, "top_bottom_items", {})
    top_by_rev_df = _safe_get(top_items_dict, "top_by_revenue", pd.DataFrame())
    top_items = []
    if not top_by_rev_df.empty:
        for _, row in top_by_rev_df.iterrows():
            top_items.append({
                "item_name": str(_safe_get(row, "Menu_Item", "")),
                "category": str(_safe_get(row, "Menu_Category", "")),
                "quantity_sold": int(_safe_get(row, "quantity", 0)),
                "net_revenue": float(_safe_get(row, "net_sales", 0)),
                "avg_price": float(_safe_get(row, "net_sales", 0) / max(_safe_get(row, "quantity", 1), 1)),
                "margin_pct": None,
            })

    # Bottom items
    bottom_by_rev_df = _safe_get(top_items_dict, "bottom_by_revenue", pd.DataFrame())
    bottom_items = []
    if not bottom_by_rev_df.empty:
        for _, row in bottom_by_rev_df.iterrows():
            bottom_items.append({
                "item_name": str(_safe_get(row, "Menu_Item", "")),
                "category": str(_safe_get(row, "Menu_Category", "")),
                "quantity_sold": int(_safe_get(row, "quantity", 0)),
                "net_revenue": float(_safe_get(row, "net_sales", 0)),
                "avg_price": float(_safe_get(row, "net_sales", 0) / max(_safe_get(row, "quantity", 1), 1)),
                "margin_pct": None,
            })

    # Hourly heatmap
    heatmap_df = _safe_get(sales_results, "hourly_heatmap", pd.DataFrame())
    hourly_heatmap = []
    if not heatmap_df.empty:
        for day in heatmap_df.index:
            for hour in heatmap_df.columns:
                val = heatmap_df.loc[day, hour]
                if pd.notna(val) and val > 0:
                    hourly_heatmap.append({
                        "day_of_week": str(day),
                        "hour": int(hour),
                        "net_revenue": float(val),
                    })

    return {
        "daily_trend": daily_trend,
        "day_of_week": day_of_week,
        "daypart": daypart,
        "order_type": order_type,
        "category_performance": category_performance,
        "top_items": top_items,
        "bottom_items": bottom_items,
        "hourly_heatmap": hourly_heatmap,
        "extended": {
            "top_bottom_items": _json_serializable(top_items_dict) if top_items_dict else {},
        },
    }


def standardize_menu(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build menu_engineering.json.

    TouchBistro does not have menu engineering analysis by default.
    Return a minimal/empty structure.
    """
    return {
        "matrix": [],
        "food_cost_by_category": [],
        "classification_summary": {},
        "overall_food_cost_pct": 0.0,
        "extended": {
            "note": "Menu engineering not available in TouchBistro",
        },
    }


def standardize_labor(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build labor_analysis.json.

    TouchBistro does not have labor analysis.
    Return a stub structure with all metrics null.
    """
    return {
        "total_labor_cost": None,
        "total_paid_hours": None,
        "labor_pct": None,
        "splh": None,
        "headcount": None,
        "total_overtime_hours": None,
        "overtime_premium_cost": None,
        "benchmark_labor_pct": None,
        "benchmark_splh": None,
        "daily_labor": [],
        "foh_boh_split": [],
        "by_role": [],
        "overtime_detail": [],
        "splh_trend": [],
        "extended": {
            "note": "Labor analysis not available in TouchBistro",
        },
    }


def standardize_payments(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build payment_analysis.json from TouchBistro payment data.

    TouchBistro provides:
    - payment_summary: Payment_Method, Total_Amount, Tips, Transaction_Count, pct_of_total, avg_transaction, tip_rate_pct
    - tip_analysis: overall_tip_pct, total_tips, by_payment, by_daypart
    """
    payments_results = results.get("payments", {})

    payment_summary = _safe_get(payments_results, "payment_summary", pd.DataFrame())
    methods = []
    if not payment_summary.empty:
        for _, row in payment_summary.iterrows():
            methods.append({
                "method": str(_safe_get(row, "Payment_Method", "")),
                "transaction_count": int(_safe_get(row, "Transaction_Count", 0)),
                "total_amount": float(_safe_get(row, "Total_Amount", 0)),
                "total_tips": float(_safe_get(row, "Tips", 0)),
                "pct_of_revenue": float(_safe_get(row, "pct_of_total", 0)),
                "avg_transaction": float(_safe_get(row, "avg_transaction", 0)),
                "avg_tip_pct": float(_safe_get(row, "tip_rate_pct", 0)),
            })

    kpis = results.get("sales", {}).get("kpis", {})
    overall_tip_rate = float(_safe_get(kpis, "avg_tip_pct", 0)) / 100

    return {
        "methods": methods,
        "overall_tip_rate": overall_tip_rate,
        "total_tips": float(_safe_get(kpis, "total_tips", 0)),
        "discount_rate_pct": float(_safe_get(kpis, "discount_rate_pct", 0)) / 100,
        "total_discounts": float(_safe_get(kpis, "total_discounts", 0)),
        "extended": {
            "tip_analysis": _json_serializable(_safe_get(payments_results, "tip_analysis", {})),
        },
    }


def standardize_ops_flags(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build operational_flags.json from TouchBistro ops data.

    TouchBistro provides:
    - ops.voids: void_count, total_items, void_rate_pct, void_revenue_lost, severity
    - ops.refunds: refund_count, refund_amount, refund_rate_pct
    - ops.comps: comp_count, comp_revenue_lost, comp_rate_pct, severity
    - ops.alerts: List[Dict] with category, severity, message, metric, threshold
    """
    ops_results = results.get("ops_flags", {})

    flags = []
    alerts = _safe_get(ops_results, "alerts", [])
    if alerts:
        for alert in alerts:
            flags.append({
                "severity": str(_safe_get(alert, "severity", "INFO")).upper(),
                "category": str(_safe_get(alert, "category", "")),
                "description": str(_safe_get(alert, "message", "")),
                "metric_value": _safe_get(alert, "metric", None),
                "threshold": _safe_get(alert, "threshold", None),
            })

    voids = _safe_get(ops_results, "voids", {})
    void_summary = {
        "void_count": int(_safe_get(voids, "void_count", 0)),
        "void_rate_pct": float(_safe_get(voids, "void_rate_pct", 0)) / 100,
        "void_revenue_lost": float(_safe_get(voids, "void_revenue_lost", 0)),
        "alert_level": str(_safe_get(voids, "severity", "OK")).upper(),
    }

    refunds = _safe_get(ops_results, "refunds", {})
    refund_summary = {
        "refund_count": int(_safe_get(refunds, "refund_count", 0)),
        "refund_amount": float(_safe_get(refunds, "refund_amount", 0)),
        "refund_rate_pct": float(_safe_get(refunds, "refund_rate_pct", 0)) / 100,
    }

    return {
        "flags": flags,
        "void_summary": void_summary,
        "refund_summary": refund_summary,
        "extended": {
            "comps": _json_serializable(_safe_get(ops_results, "comps", {})),
        },
    }


def standardize_delivery(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build delivery_analysis.json.

    TouchBistro does not have delivery analysis.
    Return a null/empty structure.
    """
    return {
        "total_orders": None,
        "completed_orders": None,
        "canceled_orders": None,
        "cancel_rate": None,
        "gross_revenue": None,
        "net_payout": None,
        "effective_margin_pct": None,
        "avg_order_value": None,
        "platform_comparison": [],
        "daily_trend": [],
        "extended": {
            "note": "Delivery analysis not available in TouchBistro",
        },
    }


def standardize_reservations(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build reservation_analysis.json.

    TouchBistro does not have reservation analysis.
    Return a null/empty structure.
    """
    return {
        "total_reservations": None,
        "completed": None,
        "no_shows": None,
        "noshow_rate": None,
        "cancel_rate": None,
        "avg_party_size": None,
        "total_covers": None,
        "avg_turn_time": None,
        "avg_wait_time": None,
        "revpash": None,
        "by_source": [],
        "noshow_by_day": [],
        "extended": {
            "note": "Reservation analysis not available in TouchBistro",
        },
    }


def standardize_customer(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build customer_analysis.json.

    TouchBistro does not have customer analysis.
    Return a minimal structure.
    """
    return {
        "total_customers": None,
        "repeat_rate": None,
        "avg_spend_per_visit": None,
        "avg_visits": None,
        "extended": {
            "note": "Customer analysis not available in TouchBistro",
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
        results: Full analysis results dict from TouchBistro analysis
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
