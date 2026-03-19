"""
Food Factor Analytics — Square Output Standardizer

Transforms raw Square POS pipeline results into the standard output
contract defined in pos_analysis.shared.output_schema.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("food_factor.square.standardize")


def _safe_get(d: dict, *keys, default=None):
    """Safely navigate nested dicts."""
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def _df_to_records(df: Optional[pd.DataFrame]) -> list:
    """Convert DataFrame to list of dicts, handling None/empty."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return []
    if isinstance(df, pd.DataFrame):
        return json.loads(df.to_json(orient="records", date_format="iso", default_handler=str))
    return []


def _json_serializable(obj: Any) -> Any:
    """Make objects JSON serializable."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, pd.DataFrame):
        return _df_to_records(obj)
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, Path):
        return str(obj)
    return obj


def standardize_metadata(results: Dict[str, Any], dataset: Any) -> dict:
    """Build metadata.json content."""
    return {
        "pos_system": "square",
        "restaurant_name": getattr(dataset, "restaurant_name", "Unknown"),
        "location": "",
        "report_period": "",
        "period_start": str(getattr(dataset, "period_start", "")),
        "period_end": str(getattr(dataset, "period_end", "")),
        "operating_days": _safe_get(results, "sales", "kpis", "avg_txns_per_day", default=0),
        "total_seats": None,
        "generated_at": datetime.now().isoformat(),
        "data_quality": [],
        "table_row_counts": getattr(dataset, "summary", lambda: {})() if hasattr(dataset, "summary") else {},
        "extended": {},
    }


def standardize_summary_metrics(results: Dict[str, Any]) -> dict:
    """Build summary_metrics.json content."""
    s = _safe_get(results, "sales", "kpis", default={})
    l = _safe_get(results, "labor", "kpis", default={})
    d = _safe_get(results, "delivery", "kpis", default={})
    r = _safe_get(results, "reservations", "kpis", default={})
    m = _safe_get(results, "menu", "matrix", default=pd.DataFrame())

    star_count = 0
    dog_count = 0
    if isinstance(m, pd.DataFrame) and not m.empty and "classification" in m.columns:
        star_count = int((m["classification"] == "Star").sum())
        dog_count = int((m["classification"] == "Dog").sum())

    return {
        "total_net_revenue": _safe_get(s, "net_sales", default=0.0),
        "total_gross_revenue": _safe_get(s, "gross_sales", default=0.0),
        "avg_daily_revenue": _safe_get(s, "avg_daily_revenue", default=0.0),
        "total_transactions": _safe_get(s, "total_transactions", default=0),
        "avg_check": _safe_get(s, "avg_check_size", default=0.0),
        "total_covers": _safe_get(s, "estimated_covers", default=0),
        "revenue_per_cover": _safe_get(s, "revenue_per_cover", default=0.0),
        "total_tips": _safe_get(s, "total_tips", default=0.0),
        "avg_tip_pct": _safe_get(s, "avg_tip_pct", default=0.0),
        "total_discounts": _safe_get(s, "total_discounts", default=0.0),
        "discount_rate_pct": _safe_get(s, "discount_rate", default=0.0),
        "labor_pct": _safe_get(l, "labor_pct"),
        "splh": _safe_get(l, "splh"),
        "total_labor_cost": _safe_get(l, "total_labor_cost"),
        "delivery_net_margin": _safe_get(d, "effective_margin"),
        "noshow_rate": _safe_get(r, "noshow_rate"),
        "menu_stars_count": star_count,
        "menu_dogs_count": dog_count,
        "extended": {},
    }


def standardize_sales(results: Dict[str, Any]) -> dict:
    """Build sales_analysis.json content."""
    sales = _safe_get(results, "sales", default={})

    # daily_trend
    daily = _safe_get(sales, "daily_trend")
    daily_records = []
    if isinstance(daily, pd.DataFrame) and not daily.empty:
        for _, row in daily.iterrows():
            daily_records.append({
                "date": str(row.get("date_only", "")),
                "net_revenue": float(row.get("net_sales", 0)),
                "transactions": int(row.get("txn_count", 0)),
                "covers": 0,  # Square doesn't track covers daily
                "avg_check": float(row.get("avg_check", 0)),
                "day_of_week": str(row.get("day_of_week", "")),
            })

    # day_of_week
    dow = _safe_get(sales, "day_of_week")
    dow_records = []
    if isinstance(dow, pd.DataFrame) and not dow.empty:
        for _, row in dow.iterrows():
            dow_records.append({
                "day": str(row.get("day_of_week", "")),
                "avg_daily_revenue": float(row.get("avg_daily_rev", 0)),
                "avg_transactions": float(row.get("txn_count", 0) / max(row.get("num_days", 1), 1)),
                "avg_covers": 0.0,
                "avg_check": float(row.get("avg_check", 0)),
                "pct_of_total": 0.0,
            })

    # daypart
    dp = _safe_get(sales, "daypart")
    dp_records = []
    if isinstance(dp, pd.DataFrame) and not dp.empty:
        for _, row in dp.iterrows():
            dp_records.append({
                "daypart": str(row.get("daypart", "")),
                "net_revenue": float(row.get("net_sales", 0)),
                "transactions": int(row.get("txn_count", 0)),
                "avg_check": float(row.get("avg_check", 0)),
                "pct_of_revenue": float(row.get("pct_of_revenue", 0)),
            })

    # order_type
    ot = _safe_get(sales, "order_type_mix")
    ot_records = []
    if isinstance(ot, pd.DataFrame) and not ot.empty:
        for _, row in ot.iterrows():
            ot_records.append({
                "order_type": str(row.get("order_type", "")),
                "net_revenue": float(row.get("net_sales", 0)),
                "transactions": int(row.get("txn_count", 0)),
                "avg_check": float(row.get("avg_check", 0)),
                "pct_of_revenue": float(row.get("pct_of_revenue", 0)),
            })

    # category_performance
    cat = _safe_get(sales, "category_perf")
    cat_records = []
    if isinstance(cat, pd.DataFrame) and not cat.empty:
        for _, row in cat.iterrows():
            cat_records.append({
                "category": str(row.get("category", "")),
                "net_revenue": float(row.get("net_sales", 0)),
                "quantity_sold": int(row.get("quantity_sold", 0)),
                "margin_pct": float(row.get("margin_pct", 0)) if pd.notna(row.get("margin_pct")) else None,
                "food_cost_pct": float(row.get("food_cost_pct", 0)) if pd.notna(row.get("food_cost_pct")) else None,
                "pct_of_revenue": float(row.get("pct_of_revenue", 0)),
            })

    # top/bottom items
    top = _safe_get(sales, "top_items", "top_revenue")
    top_records = _build_item_records(top)
    bottom = _safe_get(sales, "top_items", "bottom_revenue")
    bottom_records = _build_item_records(bottom)

    # hourly heatmap
    hm = _safe_get(sales, "hourly_heatmap")
    hm_records = []
    if isinstance(hm, pd.DataFrame) and not hm.empty:
        for day in hm.index:
            for hour in hm.columns:
                hm_records.append({
                    "day_of_week": str(day),
                    "hour": int(hour),
                    "net_revenue": float(hm.loc[day, hour]),
                })

    return {
        "daily_trend": daily_records,
        "day_of_week": dow_records,
        "daypart": dp_records,
        "order_type": ot_records,
        "category_performance": cat_records,
        "top_items": top_records,
        "bottom_items": bottom_records,
        "hourly_heatmap": hm_records,
        "extended": {
            "weekly_comparison": _df_to_records(_safe_get(sales, "weekly_comparison")),
            "avg_check_trend": _df_to_records(_safe_get(sales, "avg_check_trend")),
        },
    }


def _build_item_records(df: Optional[pd.DataFrame]) -> list:
    """Convert an items DataFrame to standard TopItemRow records."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return []
    records = []
    for _, row in df.iterrows():
        records.append({
            "item_name": str(row.get("item_name", "")),
            "category": str(row.get("category", "")),
            "quantity_sold": int(row.get("quantity_sold", 0)),
            "net_revenue": float(row.get("net_sales", 0)),
            "avg_price": float(row.get("avg_price", 0)),
            "margin_pct": float(row.get("margin_pct", 0)) if pd.notna(row.get("margin_pct")) else None,
        })
    return records


def standardize_menu(results: Dict[str, Any]) -> dict:
    """Build menu_engineering.json content."""
    menu = _safe_get(results, "menu", default={})
    matrix = _safe_get(menu, "matrix")

    matrix_records = []
    classification_summary = {"Star": 0, "Plow Horse": 0, "Puzzle": 0, "Dog": 0}
    overall_fc = 0.0

    if isinstance(matrix, pd.DataFrame) and not matrix.empty:
        for _, row in matrix.iterrows():
            cls = str(row.get("classification", "Dog"))
            classification_summary[cls] = classification_summary.get(cls, 0) + 1
            matrix_records.append({
                "item_name": str(row.get("item_name", "")),
                "category": str(row.get("category", "")),
                "classification": cls,
                "quantity_sold": int(row.get("quantity_sold", 0)),
                "net_revenue": float(row.get("net_sales", 0)),
                "total_cost": float(row.get("total_cost", 0)),
                "total_margin": float(row.get("total_margin", 0)),
                "avg_price": float(row.get("avg_price", 0)),
                "avg_margin": float(row.get("avg_margin", 0)),
                "food_cost_pct": float(row.get("food_cost_pct", 0)),
                "margin_pct": float(row.get("margin_pct", 0)),
            })
        total_rev = matrix["net_sales"].sum()
        total_cost = matrix["total_cost"].sum()
        if total_rev > 0:
            overall_fc = total_cost / total_rev

    fc_cat = _safe_get(menu, "food_cost_by_cat")
    fc_records = []
    if isinstance(fc_cat, pd.DataFrame) and not fc_cat.empty:
        for _, row in fc_cat.iterrows():
            fc_records.append({
                "category": str(row.get("category", "")),
                "net_revenue": float(row.get("net_sales", 0)),
                "total_cost": float(row.get("total_cost", 0)),
                "food_cost_pct": float(row.get("food_cost_pct", 0)),
                "benchmark": float(row.get("benchmark", 0.30)),
                "vs_benchmark": float(row.get("vs_benchmark", 0)),
            })

    return {
        "matrix": matrix_records,
        "food_cost_by_category": fc_records,
        "classification_summary": classification_summary,
        "overall_food_cost_pct": overall_fc,
        "extended": {
            "modifier_analysis": _df_to_records(_safe_get(menu, "modifier_analysis")),
            "pricing_gaps": _df_to_records(_safe_get(menu, "pricing_gaps")),
            "category_matrix": _df_to_records(_safe_get(menu, "category_matrix")),
        },
    }


def standardize_labor(results: Dict[str, Any]) -> dict:
    """Build labor_analysis.json content."""
    labor = _safe_get(results, "labor", default={})
    kpis = _safe_get(labor, "kpis", default={})

    daily = _safe_get(labor, "daily_labor")
    daily_records = []
    if isinstance(daily, pd.DataFrame) and not daily.empty:
        for _, row in daily.iterrows():
            daily_records.append({
                "date": str(row.get("date_only", "")),
                "labor_cost": float(row.get("labor_cost", 0)),
                "labor_hours": float(row.get("labor_hours", 0)),
                "staff_count": int(row.get("staff_count", 0)),
                "net_revenue": float(row.get("net_sales", 0)),
                "labor_pct": float(row.get("labor_pct", 0)),
                "splh": float(row.get("splh", 0)),
                "day_of_week": str(row.get("day_of_week", "")),
            })

    foh_boh = _safe_get(labor, "foh_boh_split")
    foh_records = []
    if isinstance(foh_boh, pd.DataFrame) and not foh_boh.empty:
        for _, row in foh_boh.iterrows():
            foh_records.append({
                "group": str(row.get("label", "")),
                "labor_cost": float(row.get("labor_cost", 0)),
                "paid_hours": float(row.get("paid_hours", 0)),
                "headcount": int(row.get("headcount", 0)),
                "pct_of_total": float(row.get("pct_of_total", 0)),
            })

    by_role = _safe_get(labor, "by_role")
    role_records = []
    if isinstance(by_role, pd.DataFrame) and not by_role.empty:
        for _, row in by_role.iterrows():
            role_records.append({
                "role": str(row.get("job_title", "")),
                "group": "FOH" if "foh" in str(row.get("job_title", "")).lower() else "BOH",
                "labor_cost": float(row.get("labor_cost", 0)),
                "paid_hours": float(row.get("paid_hours", 0)),
                "headcount": int(row.get("headcount", 0)),
                "avg_hourly_rate": float(row.get("avg_hourly", 0)),
                "pct_of_total": float(row.get("pct_of_total", 0)),
            })

    ot = _safe_get(labor, "overtime", default={})
    ot_detail = _safe_get(ot, "by_person")
    ot_records = []
    if isinstance(ot_detail, pd.DataFrame) and not ot_detail.empty:
        for _, row in ot_detail.iterrows():
            ot_records.append({
                "employee_name": str(row.get("team_member", "")),
                "overtime_hours": float(row.get("total_ot_hours", 0)),
                "overtime_shifts": int(row.get("ot_shifts", 0)),
                "overtime_cost": float(row.get("ot_cost", 0)),
            })

    splh_df = _safe_get(labor, "splh_trend")
    splh_records = []
    if isinstance(splh_df, pd.DataFrame) and not splh_df.empty:
        for _, row in splh_df.iterrows():
            splh_records.append({
                "date": str(row.get("date_only", "")),
                "splh": float(row.get("splh", 0)),
                "day_of_week": str(row.get("day_of_week", "")),
            })

    return {
        "total_labor_cost": _safe_get(kpis, "total_labor_cost", default=0.0),
        "total_paid_hours": _safe_get(kpis, "total_paid_hours", default=0.0),
        "labor_pct": _safe_get(kpis, "labor_pct", default=0.0),
        "splh": _safe_get(kpis, "splh", default=0.0),
        "headcount": _safe_get(kpis, "headcount", default=0),
        "total_overtime_hours": _safe_get(kpis, "total_ot_hours", default=0.0),
        "overtime_premium_cost": _safe_get(ot, "incremental_ot_cost", default=0.0),
        "benchmark_labor_pct": _safe_get(kpis, "benchmark_labor_pct", default=0.28),
        "benchmark_splh": _safe_get(kpis, "benchmark_splh", default=40.0),
        "daily_labor": daily_records,
        "foh_boh_split": foh_records,
        "by_role": role_records,
        "overtime_detail": ot_records,
        "splh_trend": splh_records,
        "extended": {
            "dow_staffing": _df_to_records(_safe_get(labor, "dow_staffing")),
        },
    }


def standardize_payments(results: Dict[str, Any]) -> dict:
    """Build payment_analysis.json content."""
    pay = _safe_get(results, "payments", default={})

    methods_df = _safe_get(pay, "method_breakdown")
    method_records = []
    if isinstance(methods_df, pd.DataFrame) and not methods_df.empty:
        for _, row in methods_df.iterrows():
            method_records.append({
                "method": str(row.get("payment_method", "")),
                "transaction_count": int(row.get("txn_count", 0)),
                "total_amount": float(row.get("net_sales", 0)),
                "total_tips": float(row.get("total_tips", 0)),
                "pct_of_revenue": float(row.get("pct_revenue", 0)),
                "avg_transaction": float(row.get("net_sales", 0) / max(row.get("txn_count", 1), 1)),
                "avg_tip_pct": float(row.get("avg_tip_pct", 0)),
            })

    tip = _safe_get(pay, "tip_analysis", default={})
    sales_kpis = _safe_get(results, "sales", "kpis", default={})

    return {
        "methods": method_records,
        "overall_tip_rate": _safe_get(tip, "overall_tip_rate", default=0.0),
        "total_tips": _safe_get(sales_kpis, "total_tips", default=0.0),
        "discount_rate_pct": _safe_get(sales_kpis, "discount_rate", default=0.0),
        "total_discounts": _safe_get(sales_kpis, "total_discounts", default=0.0),
        "extended": {
            "method_by_dow": _df_to_records(_safe_get(pay, "method_by_dow")),
            "method_by_order": _df_to_records(_safe_get(pay, "method_by_order")),
            "tip_by_server": _df_to_records(_safe_get(tip, "by_server")),
            "tip_by_order_type": _df_to_records(_safe_get(tip, "by_order_type")),
        },
    }


def standardize_ops_flags(results: Dict[str, Any]) -> dict:
    """Build operational_flags.json content."""
    ops = _safe_get(results, "ops_flags", default={})

    refund = _safe_get(ops, "refund_analysis", default={})
    discount = _safe_get(ops, "discount_analysis", default={})
    summary_flags = _safe_get(ops, "summary_flags", default=[])

    flags = []
    for f in summary_flags:
        flags.append({
            "severity": str(f.get("severity", "INFO")),
            "category": str(f.get("area", "")),
            "description": str(f.get("message", "")),
            "metric_value": None,
            "threshold": None,
        })

    return {
        "flags": flags,
        "void_summary": {
            "void_count": 0,
            "void_rate_pct": 0.0,
            "void_revenue_lost": 0.0,
            "alert_level": "OK",
        },
        "refund_summary": {
            "refund_count": _safe_get(refund, "refund_count", default=0),
            "refund_amount": _safe_get(refund, "refund_value", default=0.0),
            "refund_rate_pct": _safe_get(refund, "refund_rate", default=0.0),
        },
        "extended": {
            "discount_by_server": _df_to_records(_safe_get(discount, "by_server")),
            "server_flags": _df_to_records(_safe_get(ops, "server_flags")),
        },
    }


def standardize_delivery(results: Dict[str, Any]) -> Optional[dict]:
    """Build delivery_analysis.json content. Returns None if no delivery data."""
    deliv = _safe_get(results, "delivery", default={})
    kpis = _safe_get(deliv, "kpis", default={})

    if not kpis:
        return {"total_orders": 0, "completed_orders": 0, "canceled_orders": 0,
                "cancel_rate": 0.0, "gross_revenue": 0.0, "net_payout": 0.0,
                "effective_margin_pct": 0.0, "avg_order_value": 0.0,
                "platform_comparison": [], "daily_trend": [], "extended": {}}

    plat = _safe_get(deliv, "platform_compare")
    plat_records = []
    if isinstance(plat, pd.DataFrame) and not plat.empty:
        for _, row in plat.iterrows():
            plat_records.append({
                "platform": str(row.get("platform", "")),
                "order_count": int(row.get("order_count", 0)),
                "gross_revenue": float(row.get("gross_sales", 0)),
                "net_payout": float(row.get("net_payout", 0)),
                "total_fees": float(row.get("total_fees", 0)),
                "effective_margin_pct": float(row.get("effective_margin", 0)),
                "avg_order_value": float(row.get("avg_order_value", 0)),
                "avg_prep_time": float(row.get("avg_prep_time", 0)) if pd.notna(row.get("avg_prep_time")) else None,
                "avg_delivery_time": float(row.get("avg_delivery_time", 0)) if pd.notna(row.get("avg_delivery_time")) else None,
                "avg_rating": float(row.get("avg_rating", 0)) if pd.notna(row.get("avg_rating")) else None,
            })

    return {
        "total_orders": _safe_get(kpis, "total_orders", default=0),
        "completed_orders": _safe_get(kpis, "completed_orders", default=0),
        "canceled_orders": _safe_get(kpis, "canceled_orders", default=0),
        "cancel_rate": _safe_get(kpis, "cancel_rate", default=0.0),
        "gross_revenue": _safe_get(kpis, "gross_delivery_rev", default=0.0),
        "net_payout": _safe_get(kpis, "net_payout", default=0.0),
        "effective_margin_pct": _safe_get(kpis, "effective_margin", default=0.0),
        "avg_order_value": _safe_get(kpis, "avg_order_value", default=0.0),
        "platform_comparison": plat_records,
        "daily_trend": _df_to_records(_safe_get(deliv, "daily_trend")),
        "extended": {
            "hourly_pattern": _df_to_records(_safe_get(deliv, "hourly_pattern")),
            "margin_analysis": _df_to_records(_safe_get(deliv, "margin_analysis")),
            "ratings": {},
        },
    }


def standardize_reservations(results: Dict[str, Any]) -> Optional[dict]:
    """Build reservation_analysis.json content."""
    res = _safe_get(results, "reservations", default={})
    kpis = _safe_get(res, "kpis", default={})

    if not kpis:
        return {"total_reservations": 0, "completed": 0, "no_shows": 0,
                "noshow_rate": 0.0, "cancel_rate": 0.0, "avg_party_size": 0.0,
                "total_covers": 0, "avg_turn_time": None, "avg_wait_time": None,
                "revpash": None, "by_source": [], "noshow_by_day": [], "extended": {}}

    source = _safe_get(res, "source_mix")
    source_records = []
    if isinstance(source, pd.DataFrame) and not source.empty:
        for _, row in source.iterrows():
            source_records.append({
                "source": str(row.get("source", "")),
                "count": int(row.get("count", 0)),
                "noshow_rate": float(row.get("noshow_rate", 0)),
                "avg_party_size": float(row.get("avg_party", 0)),
                "pct_of_total": float(row.get("pct_of_total", 0)),
            })

    noshow_dow = _safe_get(res, "noshow_analysis", "by_day")
    noshow_records = _df_to_records(noshow_dow)

    return {
        "total_reservations": _safe_get(kpis, "total_reservations", default=0),
        "completed": _safe_get(kpis, "completed", default=0),
        "no_shows": _safe_get(kpis, "noshows", default=0),
        "noshow_rate": _safe_get(kpis, "noshow_rate", default=0.0),
        "cancel_rate": _safe_get(kpis, "cancel_rate", default=0.0),
        "avg_party_size": _safe_get(kpis, "avg_party_size", default=0.0),
        "total_covers": _safe_get(kpis, "total_covers", default=0),
        "avg_turn_time": _safe_get(kpis, "avg_turn_time"),
        "avg_wait_time": _safe_get(kpis, "avg_wait_time"),
        "revpash": None,
        "by_source": source_records,
        "noshow_by_day": noshow_records,
        "extended": {
            "turn_times": _df_to_records(_safe_get(res, "turn_times")),
            "party_size": _df_to_records(_safe_get(res, "party_size")),
            "dow_pattern": _df_to_records(_safe_get(res, "dow_pattern")),
            "revpash_detail": _df_to_records(_safe_get(res, "revpash")),
        },
    }


def standardize_customer(results: Dict[str, Any]) -> dict:
    """Build customer_analysis.json content."""
    # Square has customer directory data
    return {
        "total_customers": None,
        "repeat_rate": None,
        "avg_spend_per_visit": None,
        "avg_visits": None,
        "extended": {},
    }


def standardize_all(
    results: Dict[str, Any],
    dataset: Any,
    output_dir: Path,
) -> Path:
    """
    Run all standardizers and write JSON files to the output directory.

    Args:
        results: Raw pipeline results dict from Square's ReportGenerator.
        dataset: SquareDataset instance.
        output_dir: Directory to write standardized output files.

    Returns:
        Path to the output directory.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(exist_ok=True)

    files = {
        "metadata.json": standardize_metadata(results, dataset),
        "summary_metrics.json": standardize_summary_metrics(results),
        "sales_analysis.json": standardize_sales(results),
        "menu_engineering.json": standardize_menu(results),
        "labor_analysis.json": standardize_labor(results),
        "payment_analysis.json": standardize_payments(results),
        "operational_flags.json": standardize_ops_flags(results),
        "delivery_analysis.json": standardize_delivery(results),
        "reservation_analysis.json": standardize_reservations(results),
        "customer_analysis.json": standardize_customer(results),
    }

    for filename, data in files.items():
        path = output_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=_json_serializable)
        logger.info("Wrote %s", path)

    logger.info("Standardized output written to %s", output_dir)
    return output_dir
