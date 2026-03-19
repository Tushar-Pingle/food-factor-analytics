"""
pos_analysis.lightspeed.analysis — Lightspeed Revenue & Operational Analysis

Combines five analysis domains into a single module:
    Section 1: Sales & Revenue (trends, daypart, DOW, items, categories, servers)
    Section 2: Payment & Tender (method mix, tips, gift cards, cash handling)
    Section 3: Delivery & Online Platforms (platform comparison, profitability)
    Section 4: Reservations & Capacity (no-shows, turn times, RevPASH)
    Section 5: Operational Flags (voids, discounts, theft indicators)

Each section has its own ``run_*`` function that returns a complete result dict.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List
import logging

from config.settings import BENCHMARKS
from pos_analysis.lightspeed import TOTAL_SEATS, REPORT_PERIOD_DAYS

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
# SECTION 1 — SALES & REVENUE ANALYSIS
# ═════════════════════════════════════════════════════════════════════

def analyze_revenue_summary(receipts: pd.DataFrame) -> Dict[str, Any]:
    """Compute top-line revenue KPIs for the reporting period."""
    valid = receipts[~receipts["is_voided"]].copy()

    total_net = valid["Net_Total"].sum()
    total_tax_incl = valid["Total"].sum()
    total_tips = valid["Tip"].sum()
    txn_count = valid["Receipt_ID"].nunique()
    total_covers = valid["Number_of_Seats"].sum()
    num_days = valid["date"].nunique()

    return {
        "total_net_revenue":    round(total_net, 2),
        "total_with_tax":       round(total_tax_incl, 2),
        "total_tips":           round(total_tips, 2),
        "transaction_count":    txn_count,
        "num_operating_days":   num_days,
        "avg_daily_revenue":    round(total_net / max(num_days, 1), 2),
        "avg_check":            round(total_net / max(txn_count, 1), 2),
        "total_covers":         int(total_covers),
        "avg_daily_covers":     round(total_covers / max(num_days, 1), 1),
        "rev_per_cover":        round(total_net / max(total_covers, 1), 2),
        "avg_tip_rate":         round(total_tips / max(total_net, 1), 4),
    }


def analyze_daily_trend(receipts: pd.DataFrame) -> pd.DataFrame:
    """Daily revenue time series with 7-day rolling average."""
    valid = receipts[~receipts["is_voided"]].copy()

    daily = valid.groupby("date").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        tips=("Tip", "sum"),
    ).reset_index()

    daily["avg_check"] = daily["net_revenue"] / daily["transaction_count"].clip(lower=1)
    daily["rev_per_cover"] = daily["net_revenue"] / daily["covers"].clip(lower=1)
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    daily["revenue_7d_avg"] = daily["net_revenue"].rolling(7, min_periods=1).mean()
    daily["covers_7d_avg"] = daily["covers"].rolling(7, min_periods=1).mean()
    daily["day_of_week"] = daily["date"].dt.day_name()

    return daily


def analyze_day_of_week(receipts: pd.DataFrame) -> pd.DataFrame:
    """Day-of-week performance breakdown."""
    valid = receipts[~receipts["is_voided"]].copy()
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    dow = valid.groupby("day_of_week").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        tips=("Tip", "sum"),
        num_days=("date", "nunique"),
    ).reindex(dow_order)

    dow["avg_daily_revenue"] = dow["net_revenue"] / dow["num_days"].clip(lower=1)
    dow["avg_check"] = dow["net_revenue"] / dow["transaction_count"].clip(lower=1)
    dow["rev_per_cover"] = dow["net_revenue"] / dow["covers"].clip(lower=1)
    dow["pct_of_total"] = dow["net_revenue"] / dow["net_revenue"].sum()

    return dow


def analyze_daypart(receipts: pd.DataFrame) -> pd.DataFrame:
    """Daypart performance breakdown (Brunch, Lunch, Afternoon, Dinner, Late Night)."""
    valid = receipts[~receipts["is_voided"]].copy()
    dp_order = ["Brunch", "Lunch", "Afternoon", "Dinner", "Late Night", "Other"]

    dp = valid.groupby("daypart").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        tips=("Tip", "sum"),
    ).reindex([d for d in dp_order if d in valid["daypart"].unique()])

    dp["avg_check"] = dp["net_revenue"] / dp["transaction_count"].clip(lower=1)
    dp["rev_per_cover"] = dp["net_revenue"] / dp["covers"].clip(lower=1)
    dp["pct_of_total"] = dp["net_revenue"] / dp["net_revenue"].sum()

    return dp


def analyze_hourly_heatmap(receipts: pd.DataFrame) -> pd.DataFrame:
    """Generate hour × day-of-week revenue heatmap data."""
    valid = receipts[~receipts["is_voided"]].copy()
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    heat = valid.groupby(["hour", "day_of_week"])["Net_Total"].sum().reset_index()
    pivot = heat.pivot(index="hour", columns="day_of_week", values="Net_Total")
    pivot = pivot.reindex(columns=dow_order).fillna(0)
    pivot = pivot.loc[pivot.sum(axis=1) > 0]

    return pivot


def analyze_floor_performance(receipts: pd.DataFrame) -> pd.DataFrame:
    """Revenue breakdown by floor/section (Main Dining, Patio, Bar)."""
    valid = receipts[~receipts["is_voided"]].copy()

    floor = valid.groupby("Floor_Name").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        avg_tip=("Tip", "mean"),
    ).sort_values("net_revenue", ascending=False)

    floor["avg_check"] = floor["net_revenue"] / floor["transaction_count"].clip(lower=1)
    floor["rev_per_cover"] = floor["net_revenue"] / floor["covers"].clip(lower=1)
    floor["pct_of_total"] = floor["net_revenue"] / floor["net_revenue"].sum()

    return floor


def analyze_order_type(receipts: pd.DataFrame) -> pd.DataFrame:
    """Revenue breakdown by order type (Dine-In vs Takeout)."""
    valid = receipts[~receipts["is_voided"]].copy()

    ot = valid.groupby("Type").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        avg_tip=("Tip", "mean"),
    ).sort_values("net_revenue", ascending=False)

    ot["avg_check"] = ot["net_revenue"] / ot["transaction_count"].clip(lower=1)
    ot["pct_of_total"] = ot["net_revenue"] / ot["net_revenue"].sum()

    return ot


def analyze_top_bottom_items(
    items: pd.DataFrame,
    products: pd.DataFrame,
    n: int = 10,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Top N and Bottom N menu items by total revenue."""
    merged = items.merge(
        products[["Product_ID", "Cost", "food_cost_pct", "contribution_margin"]],
        on="Product_ID", how="left",
    )

    item_perf = merged.groupby(["Product_ID", "Item_Name", "Category"]).agg(
        total_revenue=("Tax_Exclusive_Price", "sum"),
        quantity_sold=("Amount", "sum"),
        avg_price=("Tax_Exclusive_Price", "mean"),
        total_cogs=("Cost", "sum"),
        avg_food_cost_pct=("food_cost_pct", "mean"),
        avg_margin=("contribution_margin", "mean"),
    ).reset_index()

    item_perf["total_margin"] = item_perf["total_revenue"] - item_perf["total_cogs"]
    item_perf["margin_pct"] = (
        item_perf["total_margin"] / item_perf["total_revenue"].clip(lower=0.01)
    )
    item_perf = item_perf.sort_values("total_revenue", ascending=False)

    top = item_perf.head(n).reset_index(drop=True)
    bottom = item_perf.tail(n).sort_values("total_revenue").reset_index(drop=True)

    return top, bottom


def analyze_category_performance(
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """Category-level performance with revenue, margin, and mix %."""
    merged = items.merge(
        products[["Product_ID", "Cost", "contribution_margin"]],
        on="Product_ID", how="left",
    )

    cat = merged.groupby("Category").agg(
        total_revenue=("Tax_Exclusive_Price", "sum"),
        quantity_sold=("Amount", "sum"),
        total_cogs=("Cost", "sum"),
        unique_items=("Product_ID", "nunique"),
    ).reset_index()

    cat["total_margin"] = cat["total_revenue"] - cat["total_cogs"]
    cat["margin_pct"] = cat["total_margin"] / cat["total_revenue"].clip(lower=0.01)
    cat["food_cost_pct"] = cat["total_cogs"] / cat["total_revenue"].clip(lower=0.01)
    cat["revenue_mix_pct"] = cat["total_revenue"] / cat["total_revenue"].sum()
    cat["avg_revenue_per_item"] = cat["total_revenue"] / cat["unique_items"].clip(lower=1)
    cat = cat.sort_values("total_revenue", ascending=False)

    return cat


def analyze_server_performance(receipts: pd.DataFrame) -> pd.DataFrame:
    """Server-level performance metrics."""
    valid = receipts[~receipts["is_voided"]].copy()

    srv = valid.groupby("Username").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
        total_tips=("Tip", "sum"),
        shifts_seen=("date", "nunique"),
    ).sort_values("net_revenue", ascending=False)

    srv["avg_check"] = srv["net_revenue"] / srv["transaction_count"].clip(lower=1)
    srv["avg_tip_rate"] = srv["total_tips"] / srv["net_revenue"].clip(lower=0.01)
    srv["rev_per_shift"] = srv["net_revenue"] / srv["shifts_seen"].clip(lower=1)

    return srv


def analyze_weekly_trend(receipts: pd.DataFrame) -> pd.DataFrame:
    """Weekly aggregated revenue for trend line."""
    valid = receipts[~receipts["is_voided"]].copy()

    weekly = valid.groupby("week_number").agg(
        net_revenue=("Net_Total", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        covers=("Number_of_Seats", "sum"),
    ).reset_index()

    weekly["avg_check"] = weekly["net_revenue"] / weekly["transaction_count"].clip(lower=1)
    return weekly


def run_sales_analysis(
    receipts: pd.DataFrame,
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> Dict[str, Any]:
    """Execute full sales analysis suite."""
    logger.info("Running sales analysis...")

    results: Dict[str, Any] = {
        "revenue_summary":      analyze_revenue_summary(receipts),
        "daily_trend":          analyze_daily_trend(receipts),
        "day_of_week":          analyze_day_of_week(receipts),
        "daypart":              analyze_daypart(receipts),
        "hourly_heatmap":       analyze_hourly_heatmap(receipts),
        "floor_performance":    analyze_floor_performance(receipts),
        "order_type":           analyze_order_type(receipts),
        "category_performance": analyze_category_performance(items, products),
        "server_performance":   analyze_server_performance(receipts),
        "weekly_trend":         analyze_weekly_trend(receipts),
    }

    top, bottom = analyze_top_bottom_items(items, products)
    results["top_items"] = top
    results["bottom_items"] = bottom

    logger.info("Sales analysis complete.")
    return results


# ═════════════════════════════════════════════════════════════════════
# SECTION 2 — PAYMENT & TENDER ANALYSIS
# ═════════════════════════════════════════════════════════════════════

def analyze_payment_mix(payments: pd.DataFrame) -> pd.DataFrame:
    """Payment method distribution by count and dollar volume."""
    mix = payments.groupby("Payment_Name").agg(
        transaction_count=("Payment_ID", "nunique"),
        total_amount=("Amount", "sum"),
        total_tips=("Tip", "sum"),
        avg_transaction=("Amount", "mean"),
    ).sort_values("total_amount", ascending=False).reset_index()

    mix["pct_by_count"] = mix["transaction_count"] / mix["transaction_count"].sum()
    mix["pct_by_volume"] = mix["total_amount"] / mix["total_amount"].sum()
    mix["avg_tip_rate"] = mix["total_tips"] / (mix["total_amount"] - mix["total_tips"]).clip(lower=0.01)

    return mix


def analyze_payment_type_breakdown(payments: pd.DataFrame) -> pd.DataFrame:
    """Higher-level payment type breakdown (CREDITCARD, DEBITCARD, CASH, GIFTCARD)."""
    ptype = payments.groupby("Payment_Type").agg(
        transaction_count=("Payment_ID", "nunique"),
        total_amount=("Amount", "sum"),
        total_tips=("Tip", "sum"),
    ).sort_values("total_amount", ascending=False).reset_index()

    ptype["pct_by_volume"] = ptype["total_amount"] / ptype["total_amount"].sum()
    return ptype


def analyze_tip_by_payment(payments: pd.DataFrame) -> pd.DataFrame:
    """Tip behavior analysis segmented by payment method."""
    payments = payments.copy()
    payments["base_amount"] = payments["Amount"] - payments["Tip"]
    payments["tip_rate"] = np.where(
        payments["base_amount"] > 0,
        payments["Tip"] / payments["base_amount"],
        0,
    )
    payments["has_tip"] = payments["Tip"] > 0

    tip_by_pay = payments.groupby("Payment_Name").agg(
        avg_tip_rate=("tip_rate", "mean"),
        median_tip_rate=("tip_rate", "median"),
        tip_frequency=("has_tip", "mean"),
        avg_tip_amount=("Tip", "mean"),
        total_tips=("Tip", "sum"),
        count=("Payment_ID", "nunique"),
    ).sort_values("avg_tip_rate", ascending=False).reset_index()

    return tip_by_pay


def analyze_gift_card_usage(payments: pd.DataFrame) -> Dict[str, Any]:
    """Gift card performance metrics."""
    gc = payments[payments["Payment_Type"] == "GIFTCARD"].copy()

    if gc.empty:
        return {
            "total_transactions": 0, "total_amount": 0,
            "avg_amount": 0, "pct_of_total_revenue": 0,
            "daily_trend": pd.DataFrame(),
        }

    gc["date"] = gc["Created_Date"].dt.date
    daily = gc.groupby("date").agg(
        count=("Payment_ID", "nunique"), amount=("Amount", "sum"),
    ).reset_index()

    total_revenue = payments["Amount"].sum()

    return {
        "total_transactions":   len(gc),
        "total_amount":         round(gc["Amount"].sum(), 2),
        "avg_amount":           round(gc["Amount"].mean(), 2),
        "pct_of_total_revenue": round(gc["Amount"].sum() / max(total_revenue, 1), 4),
        "daily_trend":          daily,
    }


def analyze_daily_payment_trend(payments: pd.DataFrame) -> pd.DataFrame:
    """Daily payment volume trend, broken out by payment type."""
    payments = payments.copy()
    payments["date"] = payments["Created_Date"].dt.date

    return payments.groupby(["date", "Payment_Type"]).agg(
        amount=("Amount", "sum"), count=("Payment_ID", "nunique"),
    ).reset_index()


def analyze_register_breakdown(payments: pd.DataFrame) -> pd.DataFrame:
    """Revenue breakdown by cash register/terminal."""
    if "Cash_Drawer_Name" not in payments.columns:
        return pd.DataFrame()

    reg = payments.groupby("Cash_Drawer_Name").agg(
        transaction_count=("Payment_ID", "nunique"),
        total_amount=("Amount", "sum"),
        total_tips=("Tip", "sum"),
    ).sort_values("total_amount", ascending=False).reset_index()

    reg["pct_of_total"] = reg["total_amount"] / reg["total_amount"].sum()
    return reg


def analyze_cash_handling(payments: pd.DataFrame) -> Dict[str, Any]:
    """Cash transaction analysis — important for loss prevention."""
    cash = payments[payments["Payment_Type"] == "CASH"].copy()
    total = payments["Amount"].sum()

    return {
        "cash_transaction_count":   len(cash),
        "cash_total_amount":        round(cash["Amount"].sum(), 2),
        "cash_pct_of_revenue":      round(cash["Amount"].sum() / max(total, 1), 4),
        "cash_avg_transaction":     round(cash["Amount"].mean(), 2) if len(cash) > 0 else 0,
        "cash_tip_rate":            round(
            cash["Tip"].sum() / (cash["Amount"] - cash["Tip"]).sum(), 4
        ) if len(cash) > 0 and (cash["Amount"] - cash["Tip"]).sum() > 0 else 0,
    }


def run_payment_analysis(payments: pd.DataFrame) -> Dict[str, Any]:
    """Execute full payment analysis suite."""
    logger.info("Running payment analysis...")

    results: Dict[str, Any] = {
        "payment_mix":          analyze_payment_mix(payments),
        "payment_type":         analyze_payment_type_breakdown(payments),
        "tip_by_payment":       analyze_tip_by_payment(payments),
        "gift_card":            analyze_gift_card_usage(payments),
        "daily_trend":          analyze_daily_payment_trend(payments),
        "register_breakdown":   analyze_register_breakdown(payments),
        "cash_handling":        analyze_cash_handling(payments),
    }

    logger.info("Payment analysis complete.")
    return results


# ═════════════════════════════════════════════════════════════════════
# SECTION 3 — DELIVERY & ONLINE PLATFORM ANALYSIS
# ═════════════════════════════════════════════════════════════════════

def analyze_delivery_summary(delivery: pd.DataFrame) -> Dict[str, Any]:
    """Top-line delivery KPIs across all platforms."""
    completed = delivery[delivery["is_completed"]].copy()
    canceled = delivery[~delivery["is_completed"]].copy()

    total_orders = len(delivery)
    completed_orders = len(completed)

    gross = completed["Gross_Sales"].sum()
    net = completed["Net_Payout"].sum()
    commissions = completed["Commission_Amount"].abs().sum()
    marketing = completed["Marketing_Fee"].abs().sum()
    service_fees = completed["Service_Fee"].abs().sum()
    adjustments = completed["Adjustments"].sum()

    return {
        "total_orders":         total_orders,
        "completed_orders":     completed_orders,
        "canceled_orders":      len(canceled),
        "cancel_rate":          round(len(canceled) / max(total_orders, 1), 4),
        "gross_revenue":        round(gross, 2),
        "net_payout":           round(net, 2),
        "total_commissions":    round(commissions, 2),
        "total_marketing_fees": round(marketing, 2),
        "total_service_fees":   round(service_fees, 2),
        "total_adjustments":    round(adjustments, 2),
        "effective_take_rate":  round((gross - net) / max(gross, 1), 4),
        "avg_order_value":      round(gross / max(completed_orders, 1), 2),
        "avg_net_per_order":    round(net / max(completed_orders, 1), 2),
        "avg_items_per_order":  round(completed["Item_Count"].mean(), 1),
    }


def analyze_platform_comparison(delivery: pd.DataFrame) -> pd.DataFrame:
    """Head-to-head platform performance comparison."""
    completed = delivery[delivery["is_completed"]].copy()

    plat = completed.groupby("Platform").agg(
        order_count=("Order_ID", "nunique"),
        gross_revenue=("Gross_Sales", "sum"),
        net_payout=("Net_Payout", "sum"),
        total_commissions=("Commission_Amount", lambda x: x.abs().sum()),
        total_marketing=("Marketing_Fee", lambda x: x.abs().sum()),
        total_service_fees=("Service_Fee", lambda x: x.abs().sum()),
        avg_commission_rate=("Commission_Rate", "mean"),
        avg_prep_time=("Prep_Time_Minutes", "mean"),
        avg_delivery_time=("Delivery_Time_Minutes", "mean"),
        avg_rating=("Customer_Rating", lambda x: x[x > 0].mean()),
        new_customers=("Customer_Type", lambda x: (x == "New").sum()),
        returning_customers=("Customer_Type", lambda x: (x == "Returning").sum()),
        avg_items=("Item_Count", "mean"),
    ).reset_index()

    plat["avg_order_value"] = plat["gross_revenue"] / plat["order_count"].clip(lower=1)
    plat["avg_net_per_order"] = plat["net_payout"] / plat["order_count"].clip(lower=1)
    plat["effective_take_rate"] = (
        (plat["gross_revenue"] - plat["net_payout"]) / plat["gross_revenue"].clip(lower=0.01)
    )
    plat["new_customer_pct"] = plat["new_customers"] / plat["order_count"].clip(lower=1)
    plat["revenue_share"] = plat["gross_revenue"] / plat["gross_revenue"].sum()

    return plat


def analyze_delivery_daily_trend(delivery: pd.DataFrame) -> pd.DataFrame:
    """Daily delivery order volume and revenue trend."""
    completed = delivery[delivery["is_completed"]].copy()

    daily = completed.groupby("date").agg(
        order_count=("Order_ID", "nunique"),
        gross_revenue=("Gross_Sales", "sum"),
        net_payout=("Net_Payout", "sum"),
    ).reset_index()

    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")
    daily["orders_7d_avg"] = daily["order_count"].rolling(7, min_periods=1).mean()

    return daily


def analyze_delivery_day_of_week(delivery: pd.DataFrame) -> pd.DataFrame:
    """Day-of-week delivery patterns."""
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    completed = delivery[delivery["is_completed"]].copy()

    dow = completed.groupby("day_of_week").agg(
        order_count=("Order_ID", "nunique"),
        gross_revenue=("Gross_Sales", "sum"),
        net_payout=("Net_Payout", "sum"),
        avg_prep_time=("Prep_Time_Minutes", "mean"),
        num_days=("date", "nunique"),
    ).reindex(dow_order)

    dow["avg_daily_orders"] = dow["order_count"] / dow["num_days"].clip(lower=1)
    dow["avg_daily_revenue"] = dow["gross_revenue"] / dow["num_days"].clip(lower=1)

    return dow


def analyze_delivery_hourly(delivery: pd.DataFrame) -> pd.DataFrame:
    """Hourly delivery distribution for demand forecasting."""
    completed = delivery[delivery["is_completed"]].copy()

    return completed.groupby("hour").agg(
        order_count=("Order_ID", "nunique"),
        gross_revenue=("Gross_Sales", "sum"),
        avg_prep_time=("Prep_Time_Minutes", "mean"),
    ).reset_index()


def analyze_delivery_profitability(delivery: pd.DataFrame) -> Dict[str, Any]:
    """True profitability analysis — what delivery actually costs the restaurant."""
    completed = delivery[delivery["is_completed"]].copy()

    completed["total_fees"] = (
        completed["Commission_Amount"].abs() +
        completed["Marketing_Fee"].abs() +
        completed["Service_Fee"].abs() +
        completed["Promo_Cost_Restaurant"].abs()
    )
    completed["restaurant_margin"] = completed["Gross_Sales"] - completed["total_fees"]
    completed["margin_pct"] = (
        completed["restaurant_margin"] / completed["Gross_Sales"].clip(lower=0.01)
    )

    by_platform = completed.groupby("Platform").agg(
        gross=("Gross_Sales", "sum"),
        total_fees=("total_fees", "sum"),
        net_margin=("restaurant_margin", "sum"),
        avg_margin_pct=("margin_pct", "mean"),
    ).reset_index()
    by_platform["margin_pct"] = by_platform["net_margin"] / by_platform["gross"].clip(lower=0.01)

    return {
        "avg_margin_pct":       round(completed["margin_pct"].mean(), 4),
        "total_fees_paid":      round(completed["total_fees"].sum(), 2),
        "by_platform":          by_platform,
        "below_threshold":      round(
            (completed["margin_pct"] < BENCHMARKS["delivery_net_margin"]).mean(), 4
        ),
        "benchmark":            BENCHMARKS["delivery_net_margin"],
    }


def analyze_delivery_prep_times(delivery: pd.DataFrame) -> Dict[str, Any]:
    """Prep time analysis — affects platform ranking and customer satisfaction."""
    completed = delivery[delivery["is_completed"]].copy()

    by_platform = completed.groupby("Platform").agg(
        avg_prep=("Prep_Time_Minutes", "mean"),
        median_prep=("Prep_Time_Minutes", "median"),
        p90_prep=("Prep_Time_Minutes", lambda x: x.quantile(0.9)),
        avg_delivery=("Delivery_Time_Minutes", "mean"),
    ).reset_index()

    daily_prep = completed.groupby("date")["Prep_Time_Minutes"].mean().reset_index()
    daily_prep["date"] = pd.to_datetime(daily_prep["date"])
    daily_prep = daily_prep.sort_values("date")

    return {
        "by_platform":      by_platform,
        "overall_avg_prep": round(completed["Prep_Time_Minutes"].mean(), 1),
        "overall_p90_prep": round(completed["Prep_Time_Minutes"].quantile(0.9), 1),
        "daily_trend":      daily_prep,
    }


def analyze_delivery_customer_mix(delivery: pd.DataFrame) -> Dict[str, Any]:
    """New vs returning customer analysis for delivery."""
    completed = delivery[delivery["is_completed"]].copy()

    mix = completed.groupby("Customer_Type").agg(
        order_count=("Order_ID", "nunique"),
        gross_revenue=("Gross_Sales", "sum"),
        avg_order_value=("Gross_Sales", "mean"),
    ).reset_index()

    mix["pct_of_orders"] = mix["order_count"] / mix["order_count"].sum()

    platform_mix = completed.groupby(["Platform", "Customer_Type"]).agg(
        order_count=("Order_ID", "nunique"),
    ).reset_index()

    return {
        "overall_mix":  mix,
        "by_platform":  platform_mix,
        "new_pct":      round((completed["Customer_Type"] == "New").mean(), 4),
    }


def run_delivery_analysis(delivery: pd.DataFrame) -> Dict[str, Any]:
    """Execute full delivery analysis suite."""
    logger.info("Running delivery analysis...")

    if delivery.empty:
        logger.warning("No delivery data — skipping delivery analysis.")
        return {"status": "no_data"}

    results: Dict[str, Any] = {
        "summary":          analyze_delivery_summary(delivery),
        "platform_compare": analyze_platform_comparison(delivery),
        "daily_trend":      analyze_delivery_daily_trend(delivery),
        "day_of_week":      analyze_delivery_day_of_week(delivery),
        "hourly":           analyze_delivery_hourly(delivery),
        "profitability":    analyze_delivery_profitability(delivery),
        "prep_times":       analyze_delivery_prep_times(delivery),
        "customer_mix":     analyze_delivery_customer_mix(delivery),
    }

    logger.info(
        f"Delivery analysis complete — "
        f"gross: ${results['summary']['gross_revenue']:,.0f}, "
        f"net: ${results['summary']['net_payout']:,.0f}"
    )
    return results


# ═════════════════════════════════════════════════════════════════════
# SECTION 4 — RESERVATION & CAPACITY ANALYSIS
# ═════════════════════════════════════════════════════════════════════

def analyze_reservation_summary(reservations: pd.DataFrame) -> Dict[str, Any]:
    """Top-line reservation KPIs."""
    total = len(reservations)
    completed = (reservations["Status"] == "Completed").sum()
    no_shows = (reservations["Status"] == "No-Show").sum()
    canceled = (reservations["Status"] == "Canceled").sum()
    late_cancel = (reservations["Status"] == "Late Cancel").sum()

    comp = reservations[reservations["Status"] == "Completed"]

    return {
        "total_reservations":   total,
        "completed":            int(completed),
        "no_shows":             int(no_shows),
        "canceled":             int(canceled),
        "late_cancels":         int(late_cancel),
        "no_show_rate":         round(no_shows / max(total, 1), 4),
        "cancel_rate":          round((canceled + late_cancel) / max(total, 1), 4),
        "late_cancel_rate":     round(late_cancel / max(total, 1), 4),
        "no_show_benchmark":    BENCHMARKS["no_show_rate_max"],
        "avg_party_size":       round(comp["Party_Size"].mean(), 1) if len(comp) > 0 else 0,
        "total_covers_res":     int(comp["Party_Size"].sum()),
        "avg_turn_time":        round(comp["Turn_Time_Minutes"].mean(), 1) if len(comp) > 0 else 0,
        "avg_wait_time":        round(comp["Wait_Time_Minutes"].mean(), 1) if len(comp) > 0 else 0,
        "avg_lead_time_days":   round(reservations["Lead_Time_Days"].mean(), 1),
    }


def analyze_reservation_source(reservations: pd.DataFrame) -> pd.DataFrame:
    """Reservation source performance (OpenTable, Resy, Phone, Walk-In, Website)."""
    src = reservations.groupby("Source").agg(
        total_reservations=("Reservation_ID", "nunique"),
        completed=("Status", lambda x: (x == "Completed").sum()),
        no_shows=("Status", lambda x: (x == "No-Show").sum()),
        canceled=("Status", lambda x: (x == "Canceled").sum()),
        late_cancels=("Status", lambda x: (x == "Late Cancel").sum()),
        avg_party_size=("Party_Size", "mean"),
        avg_lead_time=("Lead_Time_Days", "mean"),
    ).reset_index()

    src["no_show_rate"] = src["no_shows"] / src["total_reservations"].clip(lower=1)
    src["completion_rate"] = src["completed"] / src["total_reservations"].clip(lower=1)
    src["pct_of_total"] = src["total_reservations"] / src["total_reservations"].sum()

    return src.sort_values("total_reservations", ascending=False)


def analyze_reservation_day_of_week(reservations: pd.DataFrame) -> pd.DataFrame:
    """Day-of-week reservation patterns and no-show rates."""
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    dow = reservations.groupby("day_of_week").agg(
        total_res=("Reservation_ID", "nunique"),
        completed=("Status", lambda x: (x == "Completed").sum()),
        no_shows=("Status", lambda x: (x == "No-Show").sum()),
        avg_party_size=("Party_Size", "mean"),
        total_covers=("Party_Size", "sum"),
        num_days=("Date", lambda x: x.dt.date.nunique()),
    ).reindex(dow_order)

    dow["no_show_rate"] = dow["no_shows"] / dow["total_res"].clip(lower=1)
    dow["avg_daily_res"] = dow["total_res"] / dow["num_days"].clip(lower=1)
    dow["avg_daily_covers"] = dow["total_covers"] / dow["num_days"].clip(lower=1)

    return dow


def analyze_reservation_by_service(reservations: pd.DataFrame) -> pd.DataFrame:
    """Service-period breakdown (Lunch, Dinner, Brunch)."""
    svc = reservations.groupby("Service").agg(
        total_res=("Reservation_ID", "nunique"),
        completed=("Status", lambda x: (x == "Completed").sum()),
        no_shows=("Status", lambda x: (x == "No-Show").sum()),
        avg_party_size=("Party_Size", "mean"),
        avg_turn_time=("Turn_Time_Minutes", lambda x: x[x > 0].mean()),
        avg_wait_time=("Wait_Time_Minutes", lambda x: x[x >= 0].mean()),
    ).reset_index()

    svc["no_show_rate"] = svc["no_shows"] / svc["total_res"].clip(lower=1)
    svc["completion_rate"] = svc["completed"] / svc["total_res"].clip(lower=1)

    return svc


def analyze_turn_times(reservations: pd.DataFrame) -> Dict[str, Any]:
    """Turn time analysis for capacity optimization."""
    comp = reservations[reservations["Status"] == "Completed"].copy()

    if comp.empty:
        return {"status": "no_data"}

    by_service = comp.groupby("Service").agg(
        avg_turn=("Turn_Time_Minutes", "mean"),
        median_turn=("Turn_Time_Minutes", "median"),
        p25_turn=("Turn_Time_Minutes", lambda x: x.quantile(0.25)),
        p75_turn=("Turn_Time_Minutes", lambda x: x.quantile(0.75)),
        p90_turn=("Turn_Time_Minutes", lambda x: x.quantile(0.90)),
    ).reset_index()

    comp["party_bucket"] = pd.cut(
        comp["Party_Size"], bins=[0, 2, 4, 6, 10],
        labels=["1-2", "3-4", "5-6", "7+"],
    )
    by_party = comp.groupby("party_bucket", observed=True).agg(
        avg_turn=("Turn_Time_Minutes", "mean"),
        count=("Reservation_ID", "nunique"),
    ).reset_index()

    by_server = comp.groupby("Server_Assigned").agg(
        avg_turn=("Turn_Time_Minutes", "mean"),
        count=("Reservation_ID", "nunique"),
    ).sort_values("avg_turn").reset_index()

    return {
        "overall_avg":      round(comp["Turn_Time_Minutes"].mean(), 1),
        "overall_median":   round(comp["Turn_Time_Minutes"].median(), 1),
        "by_service":       by_service,
        "by_party_size":    by_party,
        "by_server":        by_server,
    }


def analyze_no_show_patterns(reservations: pd.DataFrame) -> Dict[str, Any]:
    """Deep dive on no-show patterns — when and from where."""
    no_shows = reservations[reservations["Status"] == "No-Show"].copy()
    total_no_shows = len(no_shows)

    if total_no_shows == 0:
        return {"total_no_shows": 0}

    lost_covers = no_shows["Party_Size"].sum()

    by_source = no_shows.groupby("Source").agg(
        count=("Reservation_ID", "nunique"),
        lost_covers=("Party_Size", "sum"),
    ).sort_values("count", ascending=False).reset_index()

    by_dow = no_shows.groupby("day_of_week").agg(
        count=("Reservation_ID", "nunique"),
    ).reset_index()

    by_service = no_shows.groupby("Service").agg(
        count=("Reservation_ID", "nunique"),
    ).reset_index()

    no_shows["same_day"] = no_shows["Lead_Time_Days"] == 0

    return {
        "total_no_shows":   total_no_shows,
        "lost_covers":      int(lost_covers),
        "by_source":        by_source,
        "by_day_of_week":   by_dow,
        "by_service":       by_service,
        "same_day_pct":     round(no_shows["same_day"].mean(), 4),
    }


def analyze_revpash(
    reservations: pd.DataFrame,
    receipts: pd.DataFrame,
) -> Dict[str, Any]:
    """Revenue Per Available Seat Hour (RevPASH) — key capacity metric."""
    valid = receipts[~receipts["is_voided"]]
    total_revenue = valid["Net_Total"].sum()
    num_days = valid["date"].nunique()

    operating_hours = 10
    total_seat_hours = TOTAL_SEATS * operating_hours * num_days
    revpash = total_revenue / max(total_seat_hours, 1)

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    daily_rev = valid.groupby("date").agg(revenue=("Net_Total", "sum")).reset_index()
    daily_rev["day_of_week"] = pd.to_datetime(daily_rev["date"]).dt.day_name()
    dow_revpash = daily_rev.groupby("day_of_week")["revenue"].mean().reindex(dow_order)
    dow_revpash = dow_revpash / (TOTAL_SEATS * operating_hours)

    return {
        "overall_revpash":  round(revpash, 2),
        "benchmark":        BENCHMARKS["revpash_target"],
        "by_day_of_week":   dow_revpash.round(2).to_dict(),
        "total_seat_hours": total_seat_hours,
    }


def run_reservation_analysis(
    reservations: pd.DataFrame,
    receipts: pd.DataFrame,
) -> Dict[str, Any]:
    """Execute full reservation analysis suite."""
    logger.info("Running reservation analysis...")

    if reservations.empty:
        logger.warning("No reservation data — skipping.")
        return {"status": "no_data"}

    results: Dict[str, Any] = {
        "summary":          analyze_reservation_summary(reservations),
        "by_source":        analyze_reservation_source(reservations),
        "by_day_of_week":   analyze_reservation_day_of_week(reservations),
        "by_service":       analyze_reservation_by_service(reservations),
        "turn_times":       analyze_turn_times(reservations),
        "no_show_patterns": analyze_no_show_patterns(reservations),
        "revpash":          analyze_revpash(reservations, receipts),
    }

    logger.info(
        f"Reservation analysis complete — "
        f"no-show rate: {results['summary']['no_show_rate']:.1%}, "
        f"RevPASH: ${results['revpash']['overall_revpash']:.2f}"
    )
    return results


# ═════════════════════════════════════════════════════════════════════
# SECTION 5 — OPERATIONAL FLAGS & LOSS PREVENTION
# ═════════════════════════════════════════════════════════════════════

def analyze_void_rate(receipts: pd.DataFrame) -> Dict[str, Any]:
    """Void rate analysis with drill-downs by server, day, and time."""
    total_receipts = len(receipts)
    voided = receipts[receipts["is_voided"]].copy()
    void_count = len(voided)
    void_rate = void_count / max(total_receipts, 1)
    void_revenue = voided["Net_Total"].sum()

    server_voids = receipts.groupby("Username").agg(
        total_txns=("Receipt_ID", "nunique"),
        voided_txns=("is_voided", "sum"),
    ).reset_index()
    server_voids["void_rate"] = server_voids["voided_txns"] / server_voids["total_txns"].clip(lower=1)
    server_voids = server_voids.sort_values("void_rate", ascending=False)

    avg_void = server_voids["void_rate"].mean()
    server_voids["flagged"] = server_voids["void_rate"] > max(avg_void * 1.5, BENCHMARKS["void_rate_max"])

    dow_voids = receipts.groupby("day_of_week").agg(
        total_txns=("Receipt_ID", "nunique"),
        voided_txns=("is_voided", "sum"),
    ).reset_index()
    dow_voids["void_rate"] = dow_voids["voided_txns"] / dow_voids["total_txns"].clip(lower=1)

    hour_voids = receipts.groupby("hour").agg(
        total_txns=("Receipt_ID", "nunique"),
        voided_txns=("is_voided", "sum"),
    ).reset_index()
    hour_voids["void_rate"] = hour_voids["voided_txns"] / hour_voids["total_txns"].clip(lower=1)

    alert_level = "normal"
    if void_rate > BENCHMARKS["void_rate_max"] * 1.5:
        alert_level = "critical"
    elif void_rate > BENCHMARKS["void_rate_max"]:
        alert_level = "warning"

    return {
        "total_receipts":       total_receipts,
        "void_count":           void_count,
        "void_rate":            round(void_rate, 4),
        "void_revenue_lost":    round(void_revenue, 2),
        "benchmark":            BENCHMARKS["void_rate_max"],
        "alert_level":          alert_level,
        "by_server":            server_voids,
        "by_day_of_week":       dow_voids,
        "by_hour":              hour_voids,
        "flagged_servers":      server_voids[server_voids["flagged"]]["Username"].tolist(),
    }


def analyze_discount_patterns(
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> Dict[str, Any]:
    """Identify potential discounts/comps by comparing actual vs. menu prices."""
    merged = items.merge(
        products[["Product_ID", "Price"]].rename(columns={"Price": "Menu_Price"}),
        on="Product_ID", how="left",
    )

    merged["price_diff"] = merged["Tax_Exclusive_Price"] - merged["Menu_Price"]
    merged["is_discounted"] = merged["price_diff"] < -0.01

    discounted = merged[merged["is_discounted"]].copy()
    discount_count = len(discounted)
    total_items = len(merged)
    discount_rate = discount_count / max(total_items, 1)
    total_discount_value = discounted["price_diff"].sum()

    disc_by_server = discounted.groupby("Created_By").agg(
        discount_count=("Receipt_ID", "count"),
        total_discount_value=("price_diff", "sum"),
    ).sort_values("total_discount_value").reset_index()

    disc_by_item = discounted.groupby("Item_Name").agg(
        discount_count=("Receipt_ID", "count"),
        total_discount_value=("price_diff", "sum"),
        avg_discount=("price_diff", "mean"),
    ).sort_values("total_discount_value").reset_index()

    return {
        "total_items_sold":         total_items,
        "discounted_count":         discount_count,
        "discount_rate":            round(discount_rate, 4),
        "total_discount_value":     round(abs(total_discount_value), 2),
        "by_server":                disc_by_server,
        "by_item":                  disc_by_item,
    }


def analyze_high_value_voids(receipts: pd.DataFrame) -> pd.DataFrame:
    """Flag high-value voided transactions (potential theft or major errors)."""
    valid = receipts[~receipts["is_voided"]]
    voided = receipts[receipts["is_voided"]].copy()

    if voided.empty:
        return pd.DataFrame()

    threshold = valid["Net_Total"].quantile(0.75)
    high_value = voided[voided["Net_Total"] > threshold].copy()
    high_value = high_value[
        ["Receipt_ID", "Creation_Date", "Username", "Net_Total", "Table_Name", "Floor_Name"]
    ].sort_values("Net_Total", ascending=False)

    return high_value


def analyze_late_night_voids(receipts: pd.DataFrame) -> Dict[str, Any]:
    """Voids occurring after typical operating hours — common theft pattern."""
    voided = receipts[receipts["is_voided"]].copy()
    late_night = voided[voided["hour"] >= 21]

    return {
        "late_void_count":  len(late_night),
        "total_void_count": len(voided),
        "late_void_pct":    round(len(late_night) / max(len(voided), 1), 4),
        "late_void_value":  round(late_night["Net_Total"].sum(), 2),
        "details":          late_night[
            ["Receipt_ID", "Creation_Date", "Username", "Net_Total"]
        ] if not late_night.empty else pd.DataFrame(),
    }


def analyze_tipout_anomalies(payments: pd.DataFrame) -> Dict[str, Any]:
    """Flag unusual tip patterns that might indicate manipulation."""
    payments = payments.copy()
    payments["base_amount"] = payments["Amount"] - payments["Tip"]
    payments["tip_rate"] = np.where(
        payments["base_amount"] > 0,
        payments["Tip"] / payments["base_amount"],
        0,
    )

    payments["high_tip"] = payments["tip_rate"] > 0.30
    payments["round_tip"] = (payments["Tip"] % 5 == 0) & (payments["Tip"] > 0)

    server_tips = payments.groupby("Tip_Owner_Name").agg(
        avg_tip_rate=("tip_rate", "mean"),
        median_tip_rate=("tip_rate", "median"),
        high_tip_count=("high_tip", "sum"),
        total_payments=("Payment_ID", "nunique"),
        total_tips=("Tip", "sum"),
    ).reset_index()
    server_tips["high_tip_pct"] = (
        server_tips["high_tip_count"] / server_tips["total_payments"].clip(lower=1)
    )

    return {
        "high_tip_transactions":    int(payments["high_tip"].sum()),
        "high_tip_pct":             round(payments["high_tip"].mean(), 4),
        "by_server":                server_tips.sort_values("avg_tip_rate", ascending=False),
    }


def _generate_operational_flags(
    void_analysis: Dict,
    discount_analysis: Dict,
    high_value_voids: pd.DataFrame,
    late_night_voids: Dict,
) -> List[Dict[str, str]]:
    """Synthesize all operational analyses into prioritized flags."""
    flags: List[Dict[str, str]] = []

    if void_analysis["alert_level"] == "critical":
        flags.append({
            "severity":       "CRITICAL",
            "category":       "Voids",
            "description":    f"Void rate of {void_analysis['void_rate']:.1%} is significantly "
                              f"above the {BENCHMARKS['void_rate_max']:.0%} benchmark. "
                              f"Estimated revenue loss: ${void_analysis['void_revenue_lost']:,.0f}.",
            "recommendation": "Implement manager-approval workflow for all voids. "
                              "Review void logs weekly with each server.",
        })
    elif void_analysis["alert_level"] == "warning":
        flags.append({
            "severity":       "WARNING",
            "category":       "Voids",
            "description":    f"Void rate of {void_analysis['void_rate']:.1%} is above "
                              f"the {BENCHMARKS['void_rate_max']:.0%} benchmark.",
            "recommendation": "Monitor void trends weekly. Investigate servers with "
                              "above-average void rates.",
        })

    if void_analysis["flagged_servers"]:
        flags.append({
            "severity":       "WARNING",
            "category":       "Server Voids",
            "description":    f"Servers with elevated void rates: "
                              f"{', '.join(void_analysis['flagged_servers'])}.",
            "recommendation": "Review individual void logs for these servers. "
                              "May indicate training needs or policy concerns.",
        })

    if not high_value_voids.empty and len(high_value_voids) > 2:
        total_val = high_value_voids["Net_Total"].sum()
        flags.append({
            "severity":       "WARNING",
            "category":       "High-Value Voids",
            "description":    f"{len(high_value_voids)} high-value voided transactions "
                              f"totaling ${total_val:,.0f}.",
            "recommendation": "Require dual-authorization for voids above "
                              "the average check amount.",
        })

    if late_night_voids["late_void_pct"] > 0.20:
        flags.append({
            "severity":       "WARNING",
            "category":       "Late-Night Voids",
            "description":    f"{late_night_voids['late_void_count']} voids after 9 PM "
                              f"({late_night_voids['late_void_pct']:.0%} of all voids).",
            "recommendation": "Implement end-of-shift void reconciliation. "
                              "Review closing procedures.",
        })

    if discount_analysis["discount_rate"] > 0.05:
        flags.append({
            "severity":       "INFO",
            "category":       "Discounts",
            "description":    f"{discount_analysis['discount_rate']:.1%} of items sold "
                              f"below menu price (${discount_analysis['total_discount_value']:,.0f} total).",
            "recommendation": "Audit comp/discount authorization process. "
                              "Ensure all discounts require manager approval.",
        })

    return flags


def run_operational_flags(
    receipts: pd.DataFrame,
    items: pd.DataFrame,
    products: pd.DataFrame,
    payments: pd.DataFrame,
) -> Dict[str, Any]:
    """Execute full operational flags analysis."""
    logger.info("Running operational flags analysis...")

    void = analyze_void_rate(receipts)
    discount = analyze_discount_patterns(items, products)
    hv_voids = analyze_high_value_voids(receipts)
    ln_voids = analyze_late_night_voids(receipts)
    tip_anomalies = analyze_tipout_anomalies(payments)

    flags = _generate_operational_flags(void, discount, hv_voids, ln_voids)

    results: Dict[str, Any] = {
        "void_analysis":        void,
        "discount_analysis":    discount,
        "high_value_voids":     hv_voids,
        "late_night_voids":     ln_voids,
        "tip_anomalies":        tip_anomalies,
        "flags":                flags,
        "flag_count": {
            "critical": sum(1 for f in flags if f["severity"] == "CRITICAL"),
            "warning":  sum(1 for f in flags if f["severity"] == "WARNING"),
            "info":     sum(1 for f in flags if f["severity"] == "INFO"),
        },
    }

    logger.info(
        f"Operational flags: {results['flag_count']['critical']} critical, "
        f"{results['flag_count']['warning']} warning, "
        f"{results['flag_count']['info']} info"
    )
    return results
