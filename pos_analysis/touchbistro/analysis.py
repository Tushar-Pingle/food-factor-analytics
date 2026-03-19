"""
pos_analysis.touchbistro.analysis
==================================
Sales, payment, and operational integrity analysis for TouchBistro POS data.

Merged from three original modules:
    - sales_analysis.py    → Revenue trends, daypart, DOW, category, server perf
    - payment_analysis.py  → Payment mix, gift cards, discounts, tips
    - operational_flags.py → Void rates, refund patterns, comp patterns, alerts

Key orchestrators:
    - run_sales_analysis()        → All revenue/sales metrics
    - run_payment_analysis()      → All payment/discount/tip metrics
    - run_operational_flags()     → All void/refund/comp/alert metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

from config.settings import BENCHMARKS
from pos_analysis.touchbistro.ingest import DAYPARTS

logger = logging.getLogger(__name__)

# Restaurant-specific thresholds (from ingest.py config)
TOTAL_SEATS: int = 72
ALERT_VOID_RATE_PCT: float = 2.0
ALERT_COMP_RATE_PCT: float = 3.0

# Ordered weekday names for consistent display
WEEKDAY_ORDER: List[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


# ══════════════════════════════════════════════
#  SECTION A: SALES ANALYSIS
#  (originally sales_analysis.py — 14 functions)
# ══════════════════════════════════════════════

def _valid_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to non-void, non-return rows only."""
    return df[(~df["is_void"]) & (~df["is_return"])].copy()


# ──────────────────────────────────────────────
# BILL-LEVEL AGGREGATION
# ──────────────────────────────────────────────

def build_bill_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate line-item data to bill-level.

    TouchBistro denormalizes bill + item data into every row,
    so we GROUP BY Bill_Number to get per-bill metrics.

    Args:
        df: Detailed sales DataFrame from ingest.load_detailed_sales().

    Returns:
        DataFrame with one row per bill: Bill_Number, Date, datetime,
        hour, weekday, weekday_name, daypart, Section, Order_Type,
        Waiter, Seats, Payment_Method, item_count, gross_sales,
        discount_total, net_sales, total_tax, tip, auto_gratuity,
        total_tip, avg_item_price.
    """
    valid = _valid_sales(df)

    bills = valid.groupby("Bill_Number").agg(
        Date=("Date", "first"),
        datetime=("datetime", "first"),
        hour=("hour", "first"),
        weekday=("weekday", "first"),
        weekday_name=("weekday_name", "first"),
        daypart=("daypart", "first"),
        Section=("Section", "first"),
        Order_Type=("Order_Type", "first"),
        Waiter=("Waiter", "first"),
        Seats=("Seats", "first"),
        Payment_Method=("Payment_Method", "first"),
        item_count=("Quantity", "sum"),
        gross_sales=("Gross_Sales", "sum"),
        discount_total=("Discount_Amount", "sum"),
        net_sales=("Net_Sales", "sum"),
        total_tax=("Total_Tax", "sum"),
        tip=("Tip", "sum"),
        auto_gratuity=("Auto_Gratuity", "sum"),
    ).reset_index()

    bills["total_tip"] = bills["tip"] + bills["auto_gratuity"]
    bills["avg_item_price"] = (
        bills["net_sales"] / bills["item_count"].replace(0, np.nan)
    )

    logger.info(f"Built bill summary: {len(bills):,} bills")
    return bills


# ──────────────────────────────────────────────
# TOP-LEVEL KPIs
# ──────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame, bills: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute headline sales KPIs for the executive summary.

    Returns:
        Dict with: total_gross, total_net, total_bills, total_covers,
        avg_check, revenue_per_cover, total_discounts, discount_rate_pct,
        total_tips, avg_tip_pct, items_sold, avg_items_per_bill,
        operating_days, avg_daily_revenue, avg_daily_covers.
    """
    valid = _valid_sales(df)

    total_gross = valid["Gross_Sales"].sum()
    total_net = valid["Net_Sales"].sum()
    total_bills = bills["Bill_Number"].nunique()
    total_covers = bills["Seats"].sum()
    items_sold = valid["Quantity"].sum()
    total_discounts = valid["Discount_Amount"].sum()
    total_tips = bills["total_tip"].sum()
    operating_days = bills["Date"].nunique()

    avg_check = total_net / total_bills if total_bills > 0 else 0
    revenue_per_cover = total_net / total_covers if total_covers > 0 else 0
    discount_rate_pct = (
        abs(total_discounts) / total_gross * 100 if total_gross > 0 else 0
    )
    avg_tip_pct = total_tips / total_net * 100 if total_net > 0 else 0

    kpis = {
        "total_gross":          round(total_gross, 2),
        "total_net":            round(total_net, 2),
        "total_bills":          int(total_bills),
        "total_covers":         int(total_covers),
        "avg_check":            round(avg_check, 2),
        "revenue_per_cover":    round(revenue_per_cover, 2),
        "total_discounts":      round(abs(total_discounts), 2),
        "discount_rate_pct":    round(discount_rate_pct, 2),
        "total_tips":           round(total_tips, 2),
        "avg_tip_pct":          round(avg_tip_pct, 1),
        "items_sold":           int(items_sold),
        "avg_items_per_bill":   round(items_sold / total_bills, 1) if total_bills > 0 else 0,
        "operating_days":       int(operating_days),
        "avg_daily_revenue":    round(total_net / operating_days, 2) if operating_days > 0 else 0,
        "avg_daily_covers":     round(total_covers / operating_days, 1) if operating_days > 0 else 0,
    }

    logger.info(
        f"KPIs computed — Net revenue: ${kpis['total_net']:,.2f}, "
        f"Avg check: ${kpis['avg_check']:.2f}"
    )
    return kpis


# ──────────────────────────────────────────────
# DAILY / WEEKLY REVENUE
# ──────────────────────────────────────────────

def daily_revenue(bills: pd.DataFrame) -> pd.DataFrame:
    """Daily revenue, covers, bill count, avg check, revenue per cover."""
    daily = bills.groupby("Date").agg(
        net_sales=("net_sales", "sum"),
        covers=("Seats", "sum"),
        bill_count=("Bill_Number", "nunique"),
    ).reset_index()

    daily["avg_check"] = (
        daily["net_sales"] / daily["bill_count"].replace(0, np.nan)
    ).round(2)
    daily["revenue_per_cover"] = (
        daily["net_sales"] / daily["covers"].replace(0, np.nan)
    ).round(2)

    return daily.sort_values("Date").reset_index(drop=True)


def weekly_revenue(bills: pd.DataFrame) -> pd.DataFrame:
    """Weekly aggregation using ISO week number."""
    bills = bills.copy()
    bills["week"] = bills["Date"].dt.isocalendar().week.astype(int)

    weekly = bills.groupby("week").agg(
        week_start=("Date", "min"),
        net_sales=("net_sales", "sum"),
        covers=("Seats", "sum"),
        bill_count=("Bill_Number", "nunique"),
    ).reset_index()

    weekly["avg_check"] = (
        weekly["net_sales"] / weekly["bill_count"].replace(0, np.nan)
    ).round(2)

    return weekly.sort_values("week").reset_index(drop=True)


# ──────────────────────────────────────────────
# DAY-OF-WEEK ANALYSIS
# ──────────────────────────────────────────────

def day_of_week_analysis(bills: pd.DataFrame) -> pd.DataFrame:
    """Revenue, covers, avg check by day of week, normalized by occurrence count."""
    dow = bills.groupby("weekday_name").agg(
        total_net=("net_sales", "sum"),
        total_covers=("Seats", "sum"),
        total_bills=("Bill_Number", "nunique"),
        day_count=("Date", "nunique"),
    ).reset_index()

    dow["avg_daily_revenue"] = (dow["total_net"] / dow["day_count"]).round(2)
    dow["avg_daily_covers"] = (dow["total_covers"] / dow["day_count"]).round(1)
    dow["avg_check"] = (
        dow["total_net"] / dow["total_bills"].replace(0, np.nan)
    ).round(2)

    dow["weekday_name"] = pd.Categorical(
        dow["weekday_name"], categories=WEEKDAY_ORDER, ordered=True
    )
    return dow.sort_values("weekday_name").reset_index(drop=True)


# ──────────────────────────────────────────────
# DAYPART ANALYSIS
# ──────────────────────────────────────────────

def daypart_analysis(bills: pd.DataFrame) -> pd.DataFrame:
    """Revenue, covers, avg check broken out by meal period."""
    dp_order = [label for label, _, _ in DAYPARTS]

    dp = bills.groupby("daypart").agg(
        total_net=("net_sales", "sum"),
        total_covers=("Seats", "sum"),
        total_bills=("Bill_Number", "nunique"),
    ).reset_index()

    dp["avg_check"] = (
        dp["total_net"] / dp["total_bills"].replace(0, np.nan)
    ).round(2)
    dp["revenue_per_cover"] = (
        dp["total_net"] / dp["total_covers"].replace(0, np.nan)
    ).round(2)
    dp["pct_revenue"] = (dp["total_net"] / dp["total_net"].sum() * 100).round(1)

    dp["daypart"] = pd.Categorical(dp["daypart"], categories=dp_order, ordered=True)
    return dp.sort_values("daypart").reset_index(drop=True)


# ──────────────────────────────────────────────
# HOURLY HEATMAP DATA (day-of-week × hour)
# ──────────────────────────────────────────────

def hourly_heatmap_data(bills: pd.DataFrame) -> pd.DataFrame:
    """Pivot table: weekday_name (rows) × hour (cols) → net_sales."""
    heatmap = bills.pivot_table(
        index="weekday_name",
        columns="hour",
        values="net_sales",
        aggfunc="sum",
        fill_value=0,
    )
    return heatmap.reindex(WEEKDAY_ORDER)


# ──────────────────────────────────────────────
# TOP / BOTTOM ITEMS
# ──────────────────────────────────────────────

def top_bottom_items(
    df: pd.DataFrame, n: int = 10
) -> Dict[str, pd.DataFrame]:
    """
    Top and bottom menu items by revenue and quantity.

    Returns:
        Dict with keys: top_by_revenue, bottom_by_revenue,
        top_by_quantity, bottom_by_quantity.
    """
    valid = _valid_sales(df)

    items = valid.groupby(
        ["Menu_Item", "Menu_Category", "Sales_Category"]
    ).agg(
        quantity=("Quantity", "sum"),
        gross_sales=("Gross_Sales", "sum"),
        net_sales=("Net_Sales", "sum"),
    ).reset_index()

    return {
        "top_by_revenue":     items.nlargest(n, "net_sales").reset_index(drop=True),
        "bottom_by_revenue":  items.nsmallest(n, "net_sales").reset_index(drop=True),
        "top_by_quantity":    items.nlargest(n, "quantity").reset_index(drop=True),
        "bottom_by_quantity": items.nsmallest(n, "quantity").reset_index(drop=True),
    }


# ──────────────────────────────────────────────
# CATEGORY PERFORMANCE
# ──────────────────────────────────────────────

def category_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and quantity breakdown by Menu_Category."""
    valid = _valid_sales(df)

    cats = valid.groupby("Menu_Category").agg(
        quantity=("Quantity", "sum"),
        gross_sales=("Gross_Sales", "sum"),
        net_sales=("Net_Sales", "sum"),
        item_count=("Menu_Item", "nunique"),
    ).reset_index()

    total_net = cats["net_sales"].sum()
    cats["pct_revenue"] = (cats["net_sales"] / total_net * 100).round(1)
    cats["avg_item_revenue"] = (
        cats["net_sales"] / cats["quantity"].replace(0, np.nan)
    ).round(2)

    return cats.sort_values("net_sales", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# SALES CATEGORY (Food vs Alcohol vs Non-Alcoholic)
# ──────────────────────────────────────────────

def sales_category_split(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue split by Sales_Category (Food / Alcohol / Non-Alcoholic)."""
    valid = _valid_sales(df)

    sc = valid.groupby("Sales_Category").agg(
        net_sales=("Net_Sales", "sum"),
        quantity=("Quantity", "sum"),
    ).reset_index()

    total = sc["net_sales"].sum()
    sc["pct_revenue"] = (sc["net_sales"] / total * 100).round(1)
    return sc.sort_values("net_sales", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# SECTION (FLOOR) PERFORMANCE
# ──────────────────────────────────────────────

def section_performance(bills: pd.DataFrame) -> pd.DataFrame:
    """Revenue and covers by floor section (Main Dining, Patio, Bar, etc.)."""
    sec = bills.groupby("Section").agg(
        net_sales=("net_sales", "sum"),
        covers=("Seats", "sum"),
        bill_count=("Bill_Number", "nunique"),
    ).reset_index()

    sec["avg_check"] = (
        sec["net_sales"] / sec["bill_count"].replace(0, np.nan)
    ).round(2)
    sec["revenue_per_cover"] = (
        sec["net_sales"] / sec["covers"].replace(0, np.nan)
    ).round(2)
    sec["pct_revenue"] = (sec["net_sales"] / sec["net_sales"].sum() * 100).round(1)

    return sec.sort_values("net_sales", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# ORDER TYPE BREAKDOWN (Dine-In / Takeout / Bar Tab)
# ──────────────────────────────────────────────

def order_type_breakdown(bills: pd.DataFrame) -> pd.DataFrame:
    """Revenue and bill count by Order_Type."""
    ot = bills.groupby("Order_Type").agg(
        net_sales=("net_sales", "sum"),
        covers=("Seats", "sum"),
        bill_count=("Bill_Number", "nunique"),
    ).reset_index()

    ot["avg_check"] = (
        ot["net_sales"] / ot["bill_count"].replace(0, np.nan)
    ).round(2)
    ot["pct_revenue"] = (ot["net_sales"] / ot["net_sales"].sum() * 100).round(1)

    return ot.sort_values("net_sales", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# SERVER PERFORMANCE
# ──────────────────────────────────────────────

def server_performance(bills: pd.DataFrame) -> pd.DataFrame:
    """Revenue, covers, avg check, and tip rate per server."""
    srv = bills.groupby("Waiter").agg(
        net_sales=("net_sales", "sum"),
        covers=("Seats", "sum"),
        bill_count=("Bill_Number", "nunique"),
        total_tip=("total_tip", "sum"),
    ).reset_index()

    srv["avg_check"] = (
        srv["net_sales"] / srv["bill_count"].replace(0, np.nan)
    ).round(2)
    srv["tip_rate_pct"] = (
        srv["total_tip"] / srv["net_sales"].replace(0, np.nan) * 100
    ).round(1)
    srv["revenue_per_cover"] = (
        srv["net_sales"] / srv["covers"].replace(0, np.nan)
    ).round(2)

    return srv.sort_values("net_sales", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# DISCOUNT ANALYSIS
# ──────────────────────────────────────────────

def discount_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Breakdown of discounts applied: name, frequency, total amount."""
    valid = _valid_sales(df)
    discounted = valid[valid["Discount_Name"] != ""].copy()

    if discounted.empty:
        return pd.DataFrame(columns=["Discount_Name", "count", "total_amount"])

    disc = discounted.groupby("Discount_Name").agg(
        count=("Bill_Number", "count"),
        total_amount=("Discount_Amount", "sum"),
    ).reset_index()

    disc["total_amount"] = disc["total_amount"].abs()
    return disc.sort_values("total_amount", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
# SALES ORCHESTRATOR
# ──────────────────────────────────────────────

def run_sales_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Execute all sales analysis and return a consolidated dict.

    Args:
        df: Cleaned detailed_sales DataFrame from ingest.load_detailed_sales().

    Returns:
        Dict keyed by analysis name → DataFrame or dict of results.
    """
    bills = build_bill_summary(df)
    kpis = compute_kpis(df, bills)

    results = {
        "bills":                bills,
        "kpis":                 kpis,
        "daily_revenue":        daily_revenue(bills),
        "weekly_revenue":       weekly_revenue(bills),
        "day_of_week":          day_of_week_analysis(bills),
        "daypart":              daypart_analysis(bills),
        "hourly_heatmap":       hourly_heatmap_data(bills),
        "top_bottom_items":     top_bottom_items(df),
        "category_performance": category_performance(df),
        "sales_category_split": sales_category_split(df),
        "section_performance":  section_performance(bills),
        "order_type":           order_type_breakdown(bills),
        "server_performance":   server_performance(bills),
        "discount_analysis":    discount_analysis(df),
    }

    logger.info("Sales analysis complete")
    return results


# ══════════════════════════════════════════════
#  SECTION B: PAYMENT ANALYSIS
#  (originally payment_analysis.py — 6 functions)
# ══════════════════════════════════════════════


def payment_method_summary(payments_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summary of payment methods from TouchBistro_06.
    Adds pct_of_total, avg_transaction, tip_rate_pct.
    """
    df = payments_df.copy()

    total = df["Total_Amount"].sum()
    df["pct_of_total"] = (
        (df["Total_Amount"] / total * 100).round(1) if total > 0 else 0
    )
    df["avg_transaction"] = (
        df["Total_Amount"] / df["Transaction_Count"].replace(0, np.nan)
    ).round(2)
    df["tip_rate_pct"] = (
        df["Tips"] / (df["Total_Amount"] - df["Tips"]).replace(0, np.nan) * 100
    ).round(1)

    return df.sort_values("Total_Amount", ascending=False).reset_index(drop=True)


def payment_method_daily_trend(detailed_sales: pd.DataFrame) -> pd.DataFrame:
    """Daily payment method mix from bill-level data."""
    valid = detailed_sales[
        (~detailed_sales["is_void"]) & (~detailed_sales["is_return"])
    ].copy()

    bills = valid.drop_duplicates(subset=["Bill_Number"]).copy()

    daily = bills.groupby(["Date", "Payment_Method"]).agg(
        bill_count=("Bill_Number", "nunique"),
        net_sales=("Net_Sales", "sum"),
    ).reset_index()

    return daily.sort_values(["Date", "Payment_Method"]).reset_index(drop=True)


def gift_card_analysis(
    payments_df: pd.DataFrame,
    detailed_sales: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Gift card usage metrics.

    Returns:
        Dict with gift_card_revenue, gift_card_pct,
        gift_card_transactions, gift_card_avg_transaction.
    """
    gc_row = payments_df[
        payments_df["Payment_Method"].str.contains("Gift", case=False, na=False)
    ]

    if gc_row.empty:
        return {
            "gift_card_revenue": 0.0,
            "gift_card_pct": 0.0,
            "gift_card_transactions": 0,
            "gift_card_avg_transaction": 0.0,
        }

    gc_revenue = gc_row["Total_Amount"].sum()
    gc_count = gc_row["Transaction_Count"].sum()
    total_revenue = payments_df["Total_Amount"].sum()

    return {
        "gift_card_revenue":         round(gc_revenue, 2),
        "gift_card_pct":             round(gc_revenue / total_revenue * 100, 1) if total_revenue > 0 else 0,
        "gift_card_transactions":    int(gc_count),
        "gift_card_avg_transaction": round(gc_revenue / gc_count, 2) if gc_count > 0 else 0,
    }


def discount_rate_analysis(detailed_sales: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute discount and comp rates.

    Returns:
        Dict with total_discounts, discount_rate_pct,
        discounted_bills, discounted_bills_pct, discount_breakdown.
    """
    valid = detailed_sales[
        (~detailed_sales["is_void"]) & (~detailed_sales["is_return"])
    ].copy()

    total_gross = valid["Gross_Sales"].sum()
    total_discounts = valid["Discount_Amount"].sum()
    total_discounts_abs = abs(total_discounts)

    discounted_bills = valid[valid["Discount_Name"] != ""]["Bill_Number"].nunique()
    total_bills = valid["Bill_Number"].nunique()

    disc_items = valid[valid["Discount_Name"] != ""].copy()
    breakdown = pd.DataFrame()
    if not disc_items.empty:
        breakdown = disc_items.groupby("Discount_Name").agg(
            line_items=("Bill_Number", "count"),
            bills_affected=("Bill_Number", "nunique"),
            total_discount=("Discount_Amount", "sum"),
            gross_sales_affected=("Gross_Sales", "sum"),
        ).reset_index()
        breakdown["total_discount"] = breakdown["total_discount"].abs()
        breakdown["effective_discount_pct"] = (
            breakdown["total_discount"] / breakdown["gross_sales_affected"] * 100
        ).round(1)
        breakdown = breakdown.sort_values(
            "total_discount", ascending=False
        ).reset_index(drop=True)

    return {
        "total_discounts":      round(total_discounts_abs, 2),
        "discount_rate_pct":    round(
            total_discounts_abs / total_gross * 100, 2
        ) if total_gross > 0 else 0,
        "discounted_bills":     int(discounted_bills),
        "discounted_bills_pct": round(
            discounted_bills / total_bills * 100, 1
        ) if total_bills > 0 else 0,
        "discount_breakdown":   breakdown,
    }


def tip_analysis(detailed_sales: pd.DataFrame) -> Dict[str, Any]:
    """
    Tipping patterns: overall rate, by payment method, by daypart.

    Returns:
        Dict with overall_tip_pct, total_tips, by_payment, by_daypart.
    """
    valid = detailed_sales[
        (~detailed_sales["is_void"]) & (~detailed_sales["is_return"])
    ].copy()

    bills = valid.groupby("Bill_Number").agg(
        net_sales=("Net_Sales", "sum"),
        tip=("Tip", "sum"),
        auto_grat=("Auto_Gratuity", "sum"),
        payment=("Payment_Method", "first"),
        daypart=("daypart", "first"),
        waiter=("Waiter", "first"),
    ).reset_index()

    bills["total_tip"] = bills["tip"] + bills["auto_grat"]
    bills["tip_pct"] = (
        bills["total_tip"] / bills["net_sales"].replace(0, np.nan) * 100
    )

    overall_tip_pct = bills["total_tip"].sum() / bills["net_sales"].sum() * 100

    by_payment = bills.groupby("payment").agg(
        avg_tip_pct=("tip_pct", "mean"),
        total_tips=("total_tip", "sum"),
        bill_count=("Bill_Number", "count"),
    ).reset_index().sort_values("total_tips", ascending=False)

    by_daypart = bills.groupby("daypart").agg(
        avg_tip_pct=("tip_pct", "mean"),
        total_tips=("total_tip", "sum"),
    ).reset_index()

    return {
        "overall_tip_pct":  round(overall_tip_pct, 1),
        "total_tips":       round(bills["total_tip"].sum(), 2),
        "by_payment":       by_payment,
        "by_daypart":       by_daypart,
    }


def run_payment_analysis(
    payments_df: pd.DataFrame,
    detailed_sales: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Execute all payment analysis functions.

    Args:
        payments_df: TouchBistro_06 DataFrame.
        detailed_sales: TouchBistro_01 DataFrame.

    Returns:
        Dict with all payment analysis results.
    """
    results = {
        "payment_summary":      payment_method_summary(payments_df),
        "payment_daily_trend":  payment_method_daily_trend(detailed_sales),
        "gift_card":            gift_card_analysis(payments_df, detailed_sales),
        "discount_rates":       discount_rate_analysis(detailed_sales),
        "tip_analysis":         tip_analysis(detailed_sales),
    }

    logger.info("Payment analysis complete")
    return results


# ══════════════════════════════════════════════
#  SECTION C: OPERATIONAL FLAGS
#  (originally operational_flags.py — 5 functions)
# ══════════════════════════════════════════════


def _severity(value: float, threshold: float) -> str:
    """Return severity label based on how far value exceeds threshold."""
    if value <= threshold:
        return "Normal"
    elif value <= threshold * 1.5:
        return "Watch"
    else:
        return "Alert"


def void_analysis(detailed_sales: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze voided items: rate, frequency, by server, by item, by time.

    A void = item sent to kitchen then canceled (Is_Void == 'Yes').
    High void rates may indicate: training issues, kitchen errors,
    POS mistakes, or potential theft (void-and-pocket).

    Returns:
        Dict with void_count, total_items, void_rate_pct,
        void_revenue_lost, severity, threshold,
        by_server, by_item, by_day_of_week, by_hour.
    """
    non_returns = detailed_sales[~detailed_sales["is_return"]].copy()

    total_items = len(non_returns)
    voids = non_returns[non_returns["is_void"]].copy()
    void_count = len(voids)
    void_rate = (void_count / total_items * 100) if total_items > 0 else 0
    void_revenue = voids["Gross_Sales"].sum()

    # By server
    server_totals = non_returns.groupby("Waiter").size().rename("total_items")
    server_voids = voids.groupby("Waiter").size().rename("void_count")
    by_server = pd.concat([server_totals, server_voids], axis=1).fillna(0)
    by_server["void_rate_pct"] = (
        by_server["void_count"] / by_server["total_items"] * 100
    ).round(2)
    by_server["void_revenue"] = voids.groupby("Waiter")["Gross_Sales"].sum()
    by_server = (
        by_server.fillna(0)
        .sort_values("void_rate_pct", ascending=False)
        .reset_index()
    )
    by_server = by_server.rename(columns={"Waiter": "server"})

    # By item
    by_item = voids.groupby("Menu_Item").agg(
        void_count=("Bill_Number", "count"),
        void_revenue=("Gross_Sales", "sum"),
    ).reset_index().sort_values("void_count", ascending=False).reset_index(drop=True)

    # By day of week
    dow_totals = non_returns.groupby("weekday_name").size().rename("total_items")
    dow_voids = voids.groupby("weekday_name").size().rename("void_count")
    by_dow = pd.concat([dow_totals, dow_voids], axis=1).fillna(0)
    by_dow["void_rate_pct"] = (
        by_dow["void_count"] / by_dow["total_items"] * 100
    ).round(2)
    by_dow = by_dow.reset_index().rename(columns={"weekday_name": "day"})

    # By hour
    hour_totals = non_returns.groupby("hour").size().rename("total_items")
    hour_voids = voids.groupby("hour").size().rename("void_count")
    by_hour = pd.concat([hour_totals, hour_voids], axis=1).fillna(0)
    by_hour["void_rate_pct"] = (
        by_hour["void_count"] / by_hour["total_items"] * 100
    ).round(2)
    by_hour = by_hour.reset_index()

    severity_label = "Normal"
    if void_rate > ALERT_VOID_RATE_PCT * 1.5:
        severity_label = "Alert"
    elif void_rate > ALERT_VOID_RATE_PCT:
        severity_label = "Watch"

    logger.info(
        f"Void analysis — rate: {void_rate:.2f}% ({void_count} items), "
        f"severity: {severity_label}"
    )

    return {
        "void_count":       int(void_count),
        "total_items":      int(total_items),
        "void_rate_pct":    round(void_rate, 2),
        "void_revenue_lost": round(void_revenue, 2),
        "severity":         severity_label,
        "threshold":        ALERT_VOID_RATE_PCT,
        "by_server":        by_server,
        "by_item":          by_item,
        "by_day_of_week":   by_dow,
        "by_hour":          by_hour,
    }


def refund_analysis(detailed_sales: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze refund/return patterns.

    A return = Is_Return == 'Yes', typically negative Quantity.

    Returns:
        Dict with refund_count, refund_amount, refund_rate_pct,
        by_item, by_server, by_payment_method.
    """
    all_items = detailed_sales[~detailed_sales["is_void"]].copy()
    returns = all_items[all_items["is_return"]].copy()

    total_gross = all_items[~all_items["is_return"]]["Gross_Sales"].sum()
    refund_count = len(returns)
    refund_amount = returns["Gross_Sales"].abs().sum()
    refund_rate = (refund_amount / total_gross * 100) if total_gross > 0 else 0

    by_item = pd.DataFrame()
    if not returns.empty:
        by_item = returns.groupby("Menu_Item").agg(
            refund_count=("Bill_Number", "count"),
            refund_amount=("Gross_Sales", lambda x: x.abs().sum()),
        ).reset_index().sort_values(
            "refund_count", ascending=False
        ).reset_index(drop=True)

    by_server = pd.DataFrame()
    if not returns.empty:
        by_server = returns.groupby("Waiter").agg(
            refund_count=("Bill_Number", "count"),
            refund_amount=("Gross_Sales", lambda x: x.abs().sum()),
        ).reset_index().sort_values(
            "refund_count", ascending=False
        ).reset_index(drop=True)

    by_payment = pd.DataFrame()
    if not returns.empty:
        by_payment = returns.groupby("Payment_Method").agg(
            refund_count=("Bill_Number", "count"),
            refund_amount=("Gross_Sales", lambda x: x.abs().sum()),
        ).reset_index().sort_values(
            "refund_amount", ascending=False
        ).reset_index(drop=True)

    logger.info(
        f"Refund analysis — {refund_count} returns, "
        f"${refund_amount:,.2f} ({refund_rate:.2f}%)"
    )

    return {
        "refund_count":      int(refund_count),
        "refund_amount":     round(refund_amount, 2),
        "refund_rate_pct":   round(refund_rate, 2),
        "by_item":           by_item,
        "by_server":         by_server,
        "by_payment_method": by_payment,
    }


def comp_pattern_analysis(detailed_sales: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze comps and deep discounts for unauthorized giveaway detection.

    Returns:
        Dict with comp_count, comp_revenue_lost, comp_rate_pct,
        severity, threshold, heavy_discount_servers, late_night_comp_count.
    """
    valid = detailed_sales[
        (~detailed_sales["is_void"]) & (~detailed_sales["is_return"])
    ].copy()

    total_gross = valid["Gross_Sales"].sum()

    # 100% comps: discount_amount >= 90% of gross_sales
    valid["discount_pct"] = (
        valid["Discount_Amount"].abs()
        / valid["Gross_Sales"].replace(0, np.nan) * 100
    )
    comps = valid[valid["discount_pct"] >= 90].copy()
    comp_count = len(comps)
    comp_revenue = comps["Gross_Sales"].sum()
    comp_rate = (comp_revenue / total_gross * 100) if total_gross > 0 else 0

    severity_label = "Normal"
    if comp_rate > ALERT_COMP_RATE_PCT * 1.5:
        severity_label = "Alert"
    elif comp_rate > ALERT_COMP_RATE_PCT:
        severity_label = "Watch"

    # Server-level discount rates
    server_gross = valid.groupby("Waiter")["Gross_Sales"].sum()
    server_disc = valid.groupby("Waiter")["Discount_Amount"].sum().abs()
    server_rates = (server_disc / server_gross * 100).round(2)
    avg_disc_rate = server_rates.mean()
    heavy_discount_servers = server_rates[
        server_rates > avg_disc_rate * 1.5
    ].reset_index()
    heavy_discount_servers.columns = ["server", "discount_rate_pct"]

    # Late-night comps (after 10 PM)
    late_night = comps[comps["hour"] >= 22].copy()

    logger.info(
        f"Comp analysis — {comp_count} full comps, "
        f"${comp_revenue:,.2f} ({comp_rate:.2f}%), severity: {severity_label}"
    )

    return {
        "comp_count":               int(comp_count),
        "comp_revenue_lost":        round(comp_revenue, 2),
        "comp_rate_pct":            round(comp_rate, 2),
        "severity":                 severity_label,
        "threshold":                ALERT_COMP_RATE_PCT,
        "heavy_discount_servers":   heavy_discount_servers,
        "late_night_comp_count":    int(len(late_night)),
    }


def generate_alerts(
    void_results: Dict[str, Any],
    refund_results: Dict[str, Any],
    comp_results: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Consolidate all operational flags into a prioritized alert list.

    Returns:
        List of dicts: [{"category", "severity", "message", "metric", "threshold"}]
    """
    alerts: List[Dict[str, str]] = []

    if void_results["severity"] != "Normal":
        alerts.append({
            "category":  "Voids",
            "severity":  void_results["severity"],
            "message":   (
                f"Void rate at {void_results['void_rate_pct']:.1f}% "
                f"(threshold: {void_results['threshold']:.1f}%). "
                f"${void_results['void_revenue_lost']:,.0f} in lost revenue."
            ),
            "metric":    f"{void_results['void_rate_pct']:.1f}%",
            "threshold": f"{void_results['threshold']:.1f}%",
        })

    for _, row in void_results["by_server"].iterrows():
        if row["void_rate_pct"] > ALERT_VOID_RATE_PCT * 2:
            alerts.append({
                "category":  "Voids — Server",
                "severity":  "Alert",
                "message":   (
                    f"{row['server']} has {row['void_rate_pct']:.1f}% void rate "
                    f"({int(row['void_count'])} items, "
                    f"${row['void_revenue']:.0f} lost)."
                ),
                "metric":    f"{row['void_rate_pct']:.1f}%",
                "threshold": f"{ALERT_VOID_RATE_PCT * 2:.1f}%",
            })

    if comp_results["severity"] != "Normal":
        alerts.append({
            "category":  "Comps",
            "severity":  comp_results["severity"],
            "message":   (
                f"Comp rate at {comp_results['comp_rate_pct']:.2f}% "
                f"(threshold: {comp_results['threshold']:.1f}%). "
                f"${comp_results['comp_revenue_lost']:,.0f} in comped items."
            ),
            "metric":    f"{comp_results['comp_rate_pct']:.2f}%",
            "threshold": f"{comp_results['threshold']:.1f}%",
        })

    if comp_results["late_night_comp_count"] > 3:
        alerts.append({
            "category":  "Late-Night Comps",
            "severity":  "Watch",
            "message":   (
                f"{comp_results['late_night_comp_count']} comps occurred "
                f"after 10 PM. Investigate for unauthorized giveaways."
            ),
            "metric":    str(comp_results["late_night_comp_count"]),
            "threshold": "3",
        })

    severity_order = {"Alert": 0, "Watch": 1, "Normal": 2}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 99))

    logger.info(f"Generated {len(alerts)} operational alerts")
    return alerts


def run_operational_flags(detailed_sales: pd.DataFrame) -> Dict[str, Any]:
    """
    Execute all operational integrity analysis.

    Args:
        detailed_sales: TouchBistro_01 DataFrame.

    Returns:
        Dict with void, refund, comp analysis and consolidated alerts.
    """
    void_results = void_analysis(detailed_sales)
    refund_results = refund_analysis(detailed_sales)
    comp_results = comp_pattern_analysis(detailed_sales)
    alerts = generate_alerts(void_results, refund_results, comp_results)

    results = {
        "voids":    void_results,
        "refunds":  refund_results,
        "comps":    comp_results,
        "alerts":   alerts,
    }

    logger.info("Operational flags analysis complete")
    return results
