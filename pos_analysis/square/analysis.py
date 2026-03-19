"""
pos_analysis/square/analysis.py — Square Sales & Operational Analysis
======================================================================
Core analytical computations for the Food Factor monthly report
derived from Square POS data.  Each analyzer class accepts a
``SquareDataset`` and returns structured results as dictionaries
ready for visualization and report generation.

Classes:
    SalesAnalyzer           — Revenue trends, daypart, day-of-week, covers
    PaymentAnalyzer         — Payment methods, tips, gift card usage
    DeliveryAnalyzer        — Platform comparison, net margins, ratings
    ReservationAnalyzer     — No-shows, turn times, RevPASH, source mix
    OperationalFlagAnalyzer — Refund / discount / void anomaly detection
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from config import settings
from pos_analysis.square.ingest import SquareDataset

logger = logging.getLogger("food_factor.square.analysis")


# ═══════════════════════════════════════════════
# SALES ANALYSIS
# ═══════════════════════════════════════════════
class SalesAnalyzer:
    """
    Revenue and sales performance analysis.

    Produces KPI summary, daily revenue trend, day-of-week patterns,
    daypart breakdown, order-type mix, category performance,
    top / bottom items, hourly heatmap data, and weekly comparison.
    """

    def __init__(self, data: SquareDataset) -> None:
        self.txn = data.transactions
        self.items = data.items
        self.payments = self.txn[~self.txn["is_refund"]].copy()
        self.period_days: int = (data.period_end - data.period_start).days + 1

    def run_all(self) -> Dict[str, Any]:
        """Execute all sales analyses and return combined results."""
        return {
            "kpis":              self.compute_kpis(),
            "daily_trend":       self.daily_revenue_trend(),
            "day_of_week":       self.day_of_week_analysis(),
            "daypart":           self.daypart_analysis(),
            "order_type_mix":    self.order_type_mix(),
            "category_perf":     self.category_performance(),
            "top_items":         self.top_bottom_items(n=10),
            "hourly_heatmap":    self.hourly_heatmap_data(),
            "weekly_comparison": self.weekly_comparison(),
            "avg_check_trend":   self.avg_check_by_day(),
        }

    # ─── KPIs ────────────────────────────────

    def compute_kpis(self) -> Dict[str, float]:
        """Core sales KPIs for the executive summary."""
        p = self.payments
        total_txns = len(p)
        gross = p["gross_sales"].sum()
        discounts = p["discounts"].abs().sum()
        net = p["net_sales"].sum()
        tax = p["tax"].sum()
        tips = p["tip"].sum()
        total_collected = p["total_collected"].sum()
        fees = p["fees"].abs().sum()

        # Covers approximation: dine-in txns × avg party (est. 2.3)
        dinein = p[p["order_type"] == "Dine-In"]
        est_covers = len(dinein) * 2.3

        return {
            "total_transactions": total_txns,
            "gross_sales":        round(gross, 2),
            "total_discounts":    round(discounts, 2),
            "discount_rate":      round(discounts / gross, 4) if gross > 0 else 0,
            "net_sales":          round(net, 2),
            "total_tax":          round(tax, 2),
            "total_tips":         round(tips, 2),
            "avg_tip_pct":        round(tips / net, 4) if net > 0 else 0,
            "total_collected":    round(total_collected, 2),
            "total_fees":         round(fees, 2),
            "avg_check_size":     round(net / total_txns, 2) if total_txns > 0 else 0,
            "avg_daily_revenue":  round(net / self.period_days, 2),
            "estimated_covers":   int(est_covers),
            "revenue_per_cover":  round(net / est_covers, 2) if est_covers > 0 else 0,
            "avg_txns_per_day":   round(total_txns / self.period_days, 1),
        }

    # ─── trend / pattern methods ──────────────

    def daily_revenue_trend(self) -> pd.DataFrame:
        """Daily net sales, transaction count, and average check."""
        daily = self.payments.groupby("date_only").agg(
            net_sales=("net_sales", "sum"),
            gross_sales=("gross_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
            total_tips=("tip", "sum"),
        ).reset_index()
        daily["avg_check"] = daily["net_sales"] / daily["txn_count"]
        daily["day_of_week"] = pd.to_datetime(daily["date_only"]).dt.day_name()
        return daily.sort_values("date_only")

    def day_of_week_analysis(self) -> pd.DataFrame:
        """Aggregated performance by day of week."""
        dow = self.payments.groupby("day_of_week").agg(
            net_sales=("net_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
            avg_check=("net_sales", "mean"),
            total_tips=("tip", "sum"),
        ).reindex(settings.DAY_ORDER).reset_index()
        dow["tip_pct"] = dow["total_tips"] / dow["net_sales"]

        dates = pd.date_range(settings.REPORT_PERIOD_START, settings.REPORT_PERIOD_END)
        day_counts = dates.day_name().value_counts()
        dow["num_days"] = dow["day_of_week"].map(day_counts)
        dow["avg_daily_rev"] = dow["net_sales"] / dow["num_days"]
        return dow

    def daypart_analysis(self) -> pd.DataFrame:
        """Revenue and transaction breakdown by daypart."""
        dp = self.payments.groupby("daypart").agg(
            net_sales=("net_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
            avg_check=("net_sales", "mean"),
        ).reset_index()
        dp["pct_of_revenue"] = dp["net_sales"] / dp["net_sales"].sum()
        dp_order = list(settings.DAYPARTS.keys())
        dp["sort_key"] = dp["daypart"].map(
            {v: i for i, v in enumerate(dp_order)}
        )
        return dp.sort_values("sort_key").drop(columns="sort_key")

    def order_type_mix(self) -> pd.DataFrame:
        """Revenue split by order type (Dine-In, Takeout, Delivery)."""
        ot = self.payments.groupby("order_type").agg(
            net_sales=("net_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
            avg_check=("net_sales", "mean"),
        ).reset_index()
        ot["pct_of_revenue"] = ot["net_sales"] / ot["net_sales"].sum()
        return ot.sort_values("net_sales", ascending=False)

    def category_performance(self) -> pd.DataFrame:
        """Revenue, quantity, and margin by menu category."""
        cat = self.items.groupby("category").agg(
            quantity_sold=("quantity", "sum"),
            gross_sales=("gross_sales", "sum"),
            net_sales=("net_sales", "sum"),
            total_cost=("cost", "sum"),
            total_margin=("contribution_margin", "sum"),
            item_count=("item_name", "nunique"),
        ).reset_index()
        cat["avg_price"]      = cat["net_sales"] / cat["quantity_sold"]
        cat["margin_pct"]     = cat["total_margin"] / cat["net_sales"]
        cat["food_cost_pct"]  = cat["total_cost"] / cat["net_sales"]
        cat["pct_of_revenue"] = cat["net_sales"] / cat["net_sales"].sum()
        return cat.sort_values("net_sales", ascending=False)

    def top_bottom_items(self, n: int = 10) -> Dict[str, pd.DataFrame]:
        """Top and bottom *n* items by net sales."""
        item_perf = self.items.groupby("item_name").agg(
            quantity_sold=("quantity", "sum"),
            net_sales=("net_sales", "sum"),
            total_cost=("cost", "sum"),
            total_margin=("contribution_margin", "sum"),
            category=("category", "first"),
        ).reset_index()
        item_perf["margin_pct"] = item_perf["total_margin"] / item_perf["net_sales"]
        item_perf["avg_price"]  = item_perf["net_sales"] / item_perf["quantity_sold"]

        return {
            "top_revenue":    item_perf.nlargest(n, "net_sales").reset_index(drop=True),
            "bottom_revenue": item_perf.nsmallest(n, "net_sales").reset_index(drop=True),
            "top_quantity":   item_perf.nlargest(n, "quantity_sold").reset_index(drop=True),
            "top_margin":     item_perf.nlargest(n, "total_margin").reset_index(drop=True),
        }

    def hourly_heatmap_data(self) -> pd.DataFrame:
        """Day-of-week × hour matrix for heatmap visualization."""
        hm = self.payments.groupby(["day_of_week", "hour"]).agg(
            net_sales=("net_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
        ).reset_index()
        pivot = hm.pivot_table(
            index="day_of_week", columns="hour",
            values="net_sales", fill_value=0,
        ).reindex(settings.DAY_ORDER)
        return pivot

    def weekly_comparison(self) -> pd.DataFrame:
        """Week-over-week comparison."""
        weekly = self.payments.groupby("week_number").agg(
            net_sales=("net_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
            avg_check=("net_sales", "mean"),
        ).reset_index()
        weekly["wow_change"] = weekly["net_sales"].pct_change()
        return weekly

    def avg_check_by_day(self) -> pd.DataFrame:
        """Average check trend by date."""
        daily = self.payments.groupby("date_only").agg(
            avg_check=("net_sales", "mean"),
            txn_count=("transaction_id", "nunique"),
        ).reset_index()
        return daily.sort_values("date_only")


# ═══════════════════════════════════════════════
# PAYMENT ANALYSIS
# ═══════════════════════════════════════════════
class PaymentAnalyzer:
    """Payment method trends, tip analysis, and gift card usage."""

    def __init__(self, data: SquareDataset) -> None:
        self.payments = data.transactions[~data.transactions["is_refund"]].copy()

    def run_all(self) -> Dict[str, Any]:
        return {
            "method_breakdown": self.payment_method_breakdown(),
            "tip_analysis":     self.tip_analysis(),
            "method_by_dow":    self.method_by_day_of_week(),
            "method_by_order":  self.method_by_order_type(),
        }

    def payment_method_breakdown(self) -> pd.DataFrame:
        """Revenue and transaction share by payment method."""
        pm = self.payments.groupby("payment_method").agg(
            txn_count=("transaction_id", "nunique"),
            net_sales=("net_sales", "sum"),
            total_tips=("tip", "sum"),
        ).reset_index()
        pm["pct_txns"]    = pm["txn_count"] / pm["txn_count"].sum()
        pm["pct_revenue"] = pm["net_sales"] / pm["net_sales"].sum()
        pm["avg_tip_pct"] = np.where(
            pm["net_sales"] > 0, pm["total_tips"] / pm["net_sales"], 0,
        )
        return pm.sort_values("net_sales", ascending=False)

    def tip_analysis(self) -> Dict[str, Any]:
        """Tip rates by order type, daypart, and server."""
        tipped = self.payments[self.payments["tip"] > 0]
        by_order = self.payments.groupby("order_type").agg(
            avg_tip=("tip", "mean"),
            total_tips=("tip", "sum"),
            tip_rate=("tip", lambda x: x.sum() / self.payments.loc[x.index, "net_sales"].sum()),
        ).reset_index()

        by_server = self.payments.groupby("team_member").agg(
            total_tips=("tip", "sum"),
            net_sales=("net_sales", "sum"),
            txn_count=("transaction_id", "nunique"),
        ).reset_index()
        by_server["tip_pct"] = by_server["total_tips"] / by_server["net_sales"]
        by_server = by_server.sort_values("total_tips", ascending=False)

        return {
            "overall_tip_rate": tipped["tip"].sum() / self.payments["net_sales"].sum(),
            "by_order_type":    by_order,
            "by_server":        by_server,
        }

    def method_by_day_of_week(self) -> pd.DataFrame:
        """Payment method distribution across days."""
        cross = self.payments.groupby(["day_of_week", "payment_method"]).agg(
            txn_count=("transaction_id", "nunique"),
        ).reset_index()
        pivot = cross.pivot_table(
            index="day_of_week", columns="payment_method",
            values="txn_count", fill_value=0,
        ).reindex(settings.DAY_ORDER)
        return pivot

    def method_by_order_type(self) -> pd.DataFrame:
        """Payment method split by order type."""
        cross = self.payments.groupby(["order_type", "payment_method"]).agg(
            txn_count=("transaction_id", "nunique"),
            net_sales=("net_sales", "sum"),
        ).reset_index()
        return cross


# ═══════════════════════════════════════════════
# DELIVERY ANALYSIS
# ═══════════════════════════════════════════════
class DeliveryAnalyzer:
    """Delivery platform performance, margins, and optimization."""

    def __init__(self, data: SquareDataset) -> None:
        self.delivery = data.delivery
        self.completed = data.delivery[~data.delivery["is_canceled"]].copy()

    def run_all(self) -> Dict[str, Any]:
        return {
            "kpis":             self.compute_kpis(),
            "platform_compare": self.platform_comparison(),
            "daily_trend":      self.daily_delivery_trend(),
            "hourly_pattern":   self.hourly_pattern(),
            "margin_analysis":  self.margin_deep_dive(),
            "ratings":          self.rating_analysis(),
        }

    def compute_kpis(self) -> Dict[str, float]:
        """Core delivery KPIs."""
        c = self.completed
        gross = c["gross_sales"].sum()
        net = c["net_payout"].sum()
        total_fees = c["total_platform_fees"].sum()

        return {
            "total_orders":       len(self.delivery),
            "completed_orders":   len(c),
            "canceled_orders":    len(self.delivery) - len(c),
            "cancel_rate":        round(1 - len(c) / len(self.delivery), 4) if len(self.delivery) > 0 else 0,
            "gross_delivery_rev": round(gross, 2),
            "net_payout":         round(net, 2),
            "total_fees":         round(total_fees, 2),
            "effective_margin":   round(net / gross, 4) if gross > 0 else 0,
            "avg_order_value":    round(gross / len(c), 2) if len(c) > 0 else 0,
            "avg_prep_time":      round(c["prep_time_minutes"].mean(), 1),
            "avg_delivery_time":  round(c["delivery_time_minutes"].mean(), 1),
            "avg_rating":         round(c["customer_rating"].dropna().mean(), 2),
        }

    def platform_comparison(self) -> pd.DataFrame:
        """Side-by-side comparison of delivery platforms."""
        plat = self.completed.groupby("platform").agg(
            order_count=("order_id", "nunique"),
            gross_sales=("gross_sales", "sum"),
            net_payout=("net_payout", "sum"),
            total_fees=("total_platform_fees", "sum"),
            avg_commission=("commission_rate", "mean"),
            avg_prep_time=("prep_time_minutes", "mean"),
            avg_delivery_time=("delivery_time_minutes", "mean"),
            avg_rating=("customer_rating", "mean"),
            new_customers=("customer_type", lambda x: (x == "New").sum()),
        ).reset_index()
        plat["effective_margin"] = plat["net_payout"] / plat["gross_sales"]
        plat["avg_order_value"]  = plat["gross_sales"] / plat["order_count"]
        return plat

    def daily_delivery_trend(self) -> pd.DataFrame:
        """Daily delivery order count and revenue."""
        daily = self.completed.groupby("date_only").agg(
            order_count=("order_id", "nunique"),
            gross_sales=("gross_sales", "sum"),
            net_payout=("net_payout", "sum"),
        ).reset_index()
        daily["day_of_week"] = pd.to_datetime(daily["date_only"]).dt.day_name()
        return daily.sort_values("date_only")

    def hourly_pattern(self) -> pd.DataFrame:
        """Delivery orders by hour of day."""
        hourly = self.completed.groupby("hour").agg(
            order_count=("order_id", "nunique"),
            gross_sales=("gross_sales", "sum"),
        ).reset_index()
        return hourly

    def margin_deep_dive(self) -> pd.DataFrame:
        """Per-order margin analysis."""
        c = self.completed.copy()
        c["margin_pct"] = c["net_payout"] / c["gross_sales"]
        return c[[
            "platform", "order_id", "gross_sales", "net_payout",
            "commission_amount", "marketing_fee", "service_fee",
            "margin_pct",
        ]].sort_values("margin_pct")

    def rating_analysis(self) -> Dict[str, Any]:
        """Rating distribution and platform comparison."""
        rated = self.completed.dropna(subset=["customer_rating"])
        dist = rated["customer_rating"].value_counts().sort_index()
        by_plat = rated.groupby("platform")["customer_rating"].agg(
            ["mean", "count", "std"],
        )
        return {
            "distribution": dist,
            "by_platform":  by_plat,
            "pct_rated":    len(rated) / len(self.completed) if len(self.completed) > 0 else 0,
        }


# ═══════════════════════════════════════════════
# RESERVATION ANALYSIS
# ═══════════════════════════════════════════════
class ReservationAnalyzer:
    """Reservation patterns, no-shows, turn times, and RevPASH."""

    def __init__(self, data: SquareDataset) -> None:
        self.reservations = data.reservations
        self.completed = data.reservations[data.reservations["is_completed"]].copy()
        self.total_seats: int = settings.TOTAL_SEATS

    def run_all(self) -> Dict[str, Any]:
        return {
            "kpis":            self.compute_kpis(),
            "source_mix":      self.source_mix(),
            "noshow_analysis": self.noshow_analysis(),
            "turn_times":      self.turn_time_analysis(),
            "party_size":      self.party_size_analysis(),
            "dow_pattern":     self.dow_pattern(),
            "revpash":         self.revpash_estimate(),
        }

    def compute_kpis(self) -> Dict[str, float]:
        """Core reservation KPIs."""
        total = len(self.reservations)
        completed = len(self.completed)
        noshows = self.reservations["is_noshow"].sum()
        canceled = self.reservations["is_canceled"].sum()
        total_covers = self.completed["party_size"].sum()

        return {
            "total_reservations": total,
            "completed":          completed,
            "noshows":            int(noshows),
            "noshow_rate":        round(noshows / total, 4) if total > 0 else 0,
            "canceled":           int(canceled),
            "cancel_rate":        round(canceled / total, 4) if total > 0 else 0,
            "total_covers":       int(total_covers),
            "avg_party_size":     round(self.completed["party_size"].mean(), 1),
            "avg_turn_time":      round(self.completed["turn_time_minutes"].mean(), 1),
            "avg_wait_time":      round(self.completed["wait_time_minutes"].mean(), 1),
            "avg_lead_time_days": round(self.reservations["lead_time_days"].mean(), 1),
        }

    def source_mix(self) -> pd.DataFrame:
        """Reservation volume by booking source."""
        src = self.reservations.groupby("source").agg(
            count=("reservation_id", "nunique"),
            avg_party=("party_size", "mean"),
            noshow_count=("is_noshow", "sum"),
        ).reset_index()
        src["pct_of_total"] = src["count"] / src["count"].sum()
        src["noshow_rate"]  = src["noshow_count"] / src["count"]
        return src.sort_values("count", ascending=False)

    def noshow_analysis(self) -> Dict[str, Any]:
        """No-show patterns by day, source, and lead time."""
        ns_by_dow = self.reservations.groupby("day_of_week").agg(
            total=("reservation_id", "nunique"),
            noshows=("is_noshow", "sum"),
        ).reindex(settings.DAY_ORDER).reset_index()
        ns_by_dow["noshow_rate"] = ns_by_dow["noshows"] / ns_by_dow["total"]

        ns_by_source = self.reservations.groupby("source").agg(
            total=("reservation_id", "nunique"),
            noshows=("is_noshow", "sum"),
        ).reset_index()
        ns_by_source["noshow_rate"] = ns_by_source["noshows"] / ns_by_source["total"]

        res = self.reservations.copy()
        res["lead_bucket"] = pd.cut(
            res["lead_time_days"],
            bins=[-1, 0, 1, 3, 7, 30],
            labels=["Same day", "1 day", "2-3 days", "4-7 days", "8+ days"],
        )
        ns_by_lead = res.groupby("lead_bucket", observed=True).agg(
            total=("reservation_id", "nunique"),
            noshows=("is_noshow", "sum"),
        ).reset_index()
        ns_by_lead["noshow_rate"] = ns_by_lead["noshows"] / ns_by_lead["total"]

        return {
            "by_day":       ns_by_dow,
            "by_source":    ns_by_source,
            "by_lead_time": ns_by_lead,
        }

    def turn_time_analysis(self) -> pd.DataFrame:
        """Average turn times by service period."""
        comp = self.completed.copy()
        by_service = comp.groupby("service").agg(
            avg_turn=("turn_time_minutes", "mean"),
            median_turn=("turn_time_minutes", "median"),
            p90_turn=("turn_time_minutes", lambda x: x.quantile(0.9)),
            count=("reservation_id", "nunique"),
        ).reset_index()
        return by_service

    def party_size_analysis(self) -> pd.DataFrame:
        """Distribution and trends in party sizes."""
        ps = self.reservations.groupby("party_size").agg(
            count=("reservation_id", "nunique"),
            noshow_rate=("is_noshow", "mean"),
        ).reset_index()
        ps["pct_of_total"] = ps["count"] / ps["count"].sum()
        return ps

    def dow_pattern(self) -> pd.DataFrame:
        """Reservation volume and covers by day of week."""
        dow = self.reservations.groupby("day_of_week").agg(
            reservations=("reservation_id", "nunique"),
            total_covers=("total_covers", "sum"),
            avg_party=("party_size", "mean"),
        ).reindex(settings.DAY_ORDER).reset_index()
        return dow

    def revpash_estimate(self) -> pd.DataFrame:
        """
        Revenue Per Available Seat Hour (RevPASH) by day of week.

        Uses covers-based proxy.  Assumes 12-hr operating day (10 am – 10 pm).
        """
        operating_hours = 12
        available_seat_hours = self.total_seats * operating_hours

        dow = self.dow_pattern()
        dow["seat_hours"]      = available_seat_hours
        dow["covers_per_seat"] = dow["total_covers"] / self.total_seats
        return dow


# ═══════════════════════════════════════════════
# OPERATIONAL FLAGS
# ═══════════════════════════════════════════════
class OperationalFlagAnalyzer:
    """
    Detect operational anomalies: void rates, refund patterns,
    discount abuse, high-comp servers, and suspicious patterns.
    """

    def __init__(self, data: SquareDataset) -> None:
        self.txn = data.transactions
        self.items = data.items
        self.payments = data.transactions[~data.transactions["is_refund"]].copy()
        self.refunds = data.transactions[data.transactions["is_refund"]].copy()

    def run_all(self) -> Dict[str, Any]:
        return {
            "refund_analysis":   self.refund_analysis(),
            "discount_analysis": self.discount_analysis(),
            "server_flags":      self.server_flags(),
            "summary_flags":     self.generate_flag_summary(),
        }

    def refund_analysis(self) -> Dict[str, Any]:
        """Refund frequency, value, and patterns."""
        total_txns = len(self.payments)
        refund_count = len(self.refunds)
        refund_value = self.refunds["net_sales"].abs().sum()
        gross_sales = self.payments["gross_sales"].sum()

        by_day = self.refunds.groupby("day_of_week").agg(
            count=("transaction_id", "nunique"),
            value=("net_sales", lambda x: x.abs().sum()),
        ).reindex(settings.DAY_ORDER).fillna(0).reset_index()

        return {
            "refund_count":       refund_count,
            "refund_value":       round(refund_value, 2),
            "refund_rate":        round(refund_count / total_txns, 4) if total_txns > 0 else 0,
            "refund_pct_of_sales": round(refund_value / gross_sales, 4) if gross_sales > 0 else 0,
            "by_day":             by_day,
            "flag":               refund_count / total_txns > settings.FLAGS["high_refund_threshold"] if total_txns > 0 else False,
        }

    def discount_analysis(self) -> Dict[str, Any]:
        """Discount frequency and value analysis."""
        discounted = self.payments[self.payments["discounts"] < 0].copy()
        total_discounts = self.payments["discounts"].abs().sum()
        gross_sales = self.payments["gross_sales"].sum()

        by_server = self.payments.groupby("team_member").agg(
            total_discounts=("discounts", lambda x: x.abs().sum()),
            discount_txns=("discounts", lambda x: (x < 0).sum()),
            txn_count=("transaction_id", "nunique"),
            net_sales=("net_sales", "sum"),
        ).reset_index()
        by_server["discount_rate"] = by_server["total_discounts"] / by_server["net_sales"]
        by_server = by_server.sort_values("total_discounts", ascending=False)

        return {
            "total_discount_value": round(total_discounts, 2),
            "discount_rate":        round(total_discounts / gross_sales, 4) if gross_sales > 0 else 0,
            "discounted_txn_count": len(discounted),
            "by_server":            by_server,
            "flag":                 total_discounts / gross_sales > settings.FLAGS["high_discount_threshold"] if gross_sales > 0 else False,
        }

    def server_flags(self) -> pd.DataFrame:
        """Per-server performance metrics for anomaly detection."""
        server = self.payments.groupby("team_member").agg(
            txn_count=("transaction_id", "nunique"),
            net_sales=("net_sales", "sum"),
            total_tips=("tip", "sum"),
            total_discounts=("discounts", lambda x: x.abs().sum()),
            avg_check=("net_sales", "mean"),
        ).reset_index()
        server["tip_pct"]      = server["total_tips"] / server["net_sales"]
        server["discount_pct"] = server["total_discounts"] / server["net_sales"]

        mean_disc = server["discount_pct"].mean()
        std_disc = server["discount_pct"].std()
        server["discount_flag"] = server["discount_pct"] > (mean_disc + 2 * std_disc)

        return server.sort_values("net_sales", ascending=False)

    def generate_flag_summary(self) -> list:
        """Generate list of operational flags / alerts."""
        flags: list = []
        refunds = self.refund_analysis()
        discounts = self.discount_analysis()

        if refunds["flag"]:
            flags.append({
                "severity": "WARNING",
                "area":     "Refunds",
                "message":  (
                    f"Refund rate of {refunds['refund_rate']:.1%} exceeds "
                    f"{settings.FLAGS['high_refund_threshold']:.1%} threshold. "
                    f"Total refund value: ${refunds['refund_value']:,.2f}"
                ),
            })

        if discounts["flag"]:
            flags.append({
                "severity": "WARNING",
                "area":     "Discounts",
                "message":  (
                    f"Discount rate of {discounts['discount_rate']:.1%} exceeds "
                    f"{settings.FLAGS['high_discount_threshold']:.1%} threshold. "
                    f"Total discounts: ${discounts['total_discount_value']:,.2f}"
                ),
            })

        server_df = self.server_flags()
        for _, row in server_df[server_df["discount_flag"]].iterrows():
            flags.append({
                "severity": "REVIEW",
                "area":     "Server Discounts",
                "message":  (
                    f"{row['team_member']} has discount rate of "
                    f"{row['discount_pct']:.1%} — significantly above team average"
                ),
            })

        if not flags:
            flags.append({
                "severity": "OK",
                "area":     "Operations",
                "message":  "All operational metrics within normal ranges.",
            })

        return flags
