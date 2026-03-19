"""
Food Factor Analytics — Standard Output Schema

Defines the canonical JSON output structure that every POS adapter must produce.
The report assembly prompt consumes these schemas identically regardless of
whether the source is Square, TouchBistro, or Lightspeed.

Each JSON file in the standard output directory maps to one TypedDict below.
Fields marked Optional may be null if the POS system cannot produce them.
Each schema includes an 'extended' key for POS-specific bonus data.
"""

from __future__ import annotations
from typing import TypedDict, Optional, List, Dict, Any


# ── metadata.json ────────────────────────────────────────────────────────

class DataQualityNote(TypedDict):
    table: str
    issue: str
    severity: str  # "info" | "warning" | "error"


class Metadata(TypedDict):
    pos_system: str                     # "square" | "touchbistro" | "lightspeed"
    restaurant_name: str
    location: str
    report_period: str                  # e.g. "March 2026"
    period_start: str                   # ISO date
    period_end: str                     # ISO date
    operating_days: int
    total_seats: Optional[int]
    generated_at: str                   # ISO timestamp
    data_quality: List[DataQualityNote]
    table_row_counts: Dict[str, int]    # e.g. {"transactions": 4200, ...}
    extended: Dict[str, Any]


# ── summary_metrics.json ────────────────────────────────────────────────

class SummaryMetrics(TypedDict):
    total_net_revenue: float
    total_gross_revenue: float
    avg_daily_revenue: float
    total_transactions: int
    avg_check: float
    total_covers: int
    revenue_per_cover: float
    total_tips: float
    avg_tip_pct: float
    total_discounts: float
    discount_rate_pct: float
    labor_pct: Optional[float]
    splh: Optional[float]
    total_labor_cost: Optional[float]
    delivery_net_margin: Optional[float]
    noshow_rate: Optional[float]
    menu_stars_count: Optional[int]
    menu_dogs_count: Optional[int]
    extended: Dict[str, Any]


# ── sales_analysis.json ─────────────────────────────────────────────────

class DailyTrendRow(TypedDict):
    date: str                  # ISO date
    net_revenue: float
    transactions: int
    covers: int
    avg_check: float
    day_of_week: str


class DayOfWeekRow(TypedDict):
    day: str                   # Monday-Sunday
    avg_daily_revenue: float
    avg_transactions: float
    avg_covers: float
    avg_check: float
    pct_of_total: float


class DaypartRow(TypedDict):
    daypart: str               # Early Morning, Breakfast, Lunch, etc.
    net_revenue: float
    transactions: int
    avg_check: float
    pct_of_revenue: float


class OrderTypeRow(TypedDict):
    order_type: str            # Dine-In, Takeout, Delivery
    net_revenue: float
    transactions: int
    avg_check: float
    pct_of_revenue: float


class CategoryRow(TypedDict):
    category: str
    net_revenue: float
    quantity_sold: int
    margin_pct: Optional[float]
    food_cost_pct: Optional[float]
    pct_of_revenue: float


class TopItemRow(TypedDict):
    item_name: str
    category: str
    quantity_sold: int
    net_revenue: float
    avg_price: float
    margin_pct: Optional[float]


class HourlyHeatmapRow(TypedDict):
    day_of_week: str
    hour: int
    net_revenue: float


class SalesAnalysis(TypedDict):
    daily_trend: List[DailyTrendRow]
    day_of_week: List[DayOfWeekRow]
    daypart: List[DaypartRow]
    order_type: List[OrderTypeRow]
    category_performance: List[CategoryRow]
    top_items: List[TopItemRow]
    bottom_items: List[TopItemRow]
    hourly_heatmap: List[HourlyHeatmapRow]
    extended: Dict[str, Any]


# ── menu_engineering.json ────────────────────────────────────────────────

class MenuItemClassification(TypedDict):
    item_name: str
    category: str
    classification: str        # "Star" | "Plow Horse" | "Puzzle" | "Dog"
    quantity_sold: int
    net_revenue: float
    total_cost: float
    total_margin: float
    avg_price: float
    avg_margin: float
    food_cost_pct: float
    margin_pct: float


class FoodCostByCategoryRow(TypedDict):
    category: str
    net_revenue: float
    total_cost: float
    food_cost_pct: float
    benchmark: float
    vs_benchmark: float


class MenuEngineering(TypedDict):
    matrix: List[MenuItemClassification]
    food_cost_by_category: List[FoodCostByCategoryRow]
    classification_summary: Dict[str, int]  # {"Star": 12, "Plow Horse": 8, ...}
    overall_food_cost_pct: float
    extended: Dict[str, Any]


# ── labor_analysis.json ──────────────────────────────────────────────────

class LaborDailyRow(TypedDict):
    date: str
    labor_cost: float
    labor_hours: float
    staff_count: int
    net_revenue: float
    labor_pct: float
    splh: float
    day_of_week: str


class FOHBOHRow(TypedDict):
    group: str                 # "FOH" | "BOH"
    labor_cost: float
    paid_hours: float
    headcount: int
    pct_of_total: float


class LaborByRoleRow(TypedDict):
    role: str
    group: str                 # "FOH" | "BOH"
    labor_cost: float
    paid_hours: float
    headcount: int
    avg_hourly_rate: float
    pct_of_total: float


class OvertimeRow(TypedDict):
    employee_name: str
    overtime_hours: float
    overtime_shifts: int
    overtime_cost: float


class LaborAnalysis(TypedDict):
    total_labor_cost: float
    total_paid_hours: float
    labor_pct: float
    splh: float
    headcount: int
    total_overtime_hours: float
    overtime_premium_cost: float
    benchmark_labor_pct: float
    benchmark_splh: float
    daily_labor: List[LaborDailyRow]
    foh_boh_split: List[FOHBOHRow]
    by_role: List[LaborByRoleRow]
    overtime_detail: List[OvertimeRow]
    splh_trend: List[Dict[str, Any]]  # [{date, splh, day_of_week}]
    extended: Dict[str, Any]


# ── payment_analysis.json ────────────────────────────────────────────────

class PaymentMethodRow(TypedDict):
    method: str
    transaction_count: int
    total_amount: float
    total_tips: float
    pct_of_revenue: float
    avg_transaction: float
    avg_tip_pct: float


class PaymentAnalysis(TypedDict):
    methods: List[PaymentMethodRow]
    overall_tip_rate: float
    total_tips: float
    discount_rate_pct: float
    total_discounts: float
    extended: Dict[str, Any]


# ── operational_flags.json ───────────────────────────────────────────────

class OperationalFlag(TypedDict):
    severity: str              # "CRITICAL" | "WARNING" | "INFO" | "OK"
    category: str              # "voids" | "refunds" | "discounts" | "comps" | "tips"
    description: str
    metric_value: Optional[float]
    threshold: Optional[float]


class VoidSummary(TypedDict):
    void_count: int
    void_rate_pct: float
    void_revenue_lost: float
    alert_level: str


class RefundSummary(TypedDict):
    refund_count: int
    refund_amount: float
    refund_rate_pct: float


class OperationalFlags(TypedDict):
    flags: List[OperationalFlag]
    void_summary: VoidSummary
    refund_summary: RefundSummary
    extended: Dict[str, Any]


# ── delivery_analysis.json ───────────────────────────────────────────────

class DeliveryPlatformRow(TypedDict):
    platform: str
    order_count: int
    gross_revenue: float
    net_payout: float
    total_fees: float
    effective_margin_pct: float
    avg_order_value: float
    avg_prep_time: Optional[float]
    avg_delivery_time: Optional[float]
    avg_rating: Optional[float]


class DeliveryAnalysis(TypedDict, total=False):
    total_orders: int
    completed_orders: int
    canceled_orders: int
    cancel_rate: float
    gross_revenue: float
    net_payout: float
    effective_margin_pct: float
    avg_order_value: float
    platform_comparison: List[DeliveryPlatformRow]
    daily_trend: List[Dict[str, Any]]
    extended: Dict[str, Any]


# ── reservation_analysis.json ────────────────────────────────────────────

class ReservationSourceRow(TypedDict):
    source: str
    count: int
    noshow_rate: float
    avg_party_size: float
    pct_of_total: float


class ReservationAnalysis(TypedDict, total=False):
    total_reservations: int
    completed: int
    no_shows: int
    noshow_rate: float
    cancel_rate: float
    avg_party_size: float
    total_covers: int
    avg_turn_time: Optional[float]
    avg_wait_time: Optional[float]
    revpash: Optional[float]
    by_source: List[ReservationSourceRow]
    noshow_by_day: List[Dict[str, Any]]
    extended: Dict[str, Any]


# ── customer_analysis.json ───────────────────────────────────────────────

class CustomerAnalysis(TypedDict, total=False):
    total_customers: Optional[int]
    repeat_rate: Optional[float]
    avg_spend_per_visit: Optional[float]
    avg_visits: Optional[float]
    extended: Dict[str, Any]


# ── Standard chart file names ────────────────────────────────────────────

STANDARD_CHART_NAMES: List[str] = [
    "revenue_trend.png",
    "day_of_week.png",
    "daypart_heatmap.png",
    "order_type_mix.png",
    "category_performance.png",
    "menu_engineering_matrix.png",
    "food_cost_by_category.png",
    "top_items.png",
    "payment_methods.png",
    "labor_by_day.png",
    "splh_trend.png",
    "foh_boh_split.png",
    "delivery_comparison.png",
    "reservation_sources.png",
    "noshow_by_day.png",
    "operational_flags.png",
]

# Files that must exist in every standard output directory
REQUIRED_JSON_FILES: List[str] = [
    "metadata.json",
    "summary_metrics.json",
    "sales_analysis.json",
    "menu_engineering.json",
    "labor_analysis.json",
    "payment_analysis.json",
    "operational_flags.json",
    "delivery_analysis.json",
    "reservation_analysis.json",
    "customer_analysis.json",
]

REQUIRED_CHARTS: List[str] = STANDARD_CHART_NAMES
