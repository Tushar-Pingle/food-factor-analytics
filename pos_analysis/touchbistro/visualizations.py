"""
pos_analysis.touchbistro.visualizations
=========================================
Professional data visualization for Food Factor TouchBistro reports.

Custom-themed matplotlib/seaborn charts at 200 DPI, export-ready for PDF.
Enforces Food Factor brand palette — no matplotlib defaults, no 3D, no pie charts.

Chart inventory (14 charts):
    01  chart_daily_revenue          — line + 7-day MA with peak/trough annotations
    02  chart_day_of_week            — vertical bar, avg daily revenue by DOW
    03  chart_daypart                — horizontal bar, revenue by meal period
    04  chart_hourly_heatmap         — heatmap, DOW × hour → revenue
    05  chart_top_items              — horizontal bar, top 10 items by revenue
    06  chart_category_performance   — horizontal bar, revenue by menu category
    07  chart_menu_matrix            — scatter, contribution margin × quantity
    08  chart_food_cost_by_category  — horizontal bar with benchmark band
    09  chart_payment_mix            — horizontal bar, payment method share
    10  chart_server_performance     — grouped bar + line, revenue & avg check
    11  chart_void_rate_by_server    — horizontal bar with alert threshold
    12  chart_delivery_comparison    — grouped bar, gross vs net by platform
    13  chart_reservation_status     — horizontal bar, status distribution
    14  chart_sales_category_split   — horizontal bar, Food vs Alcohol

Utilities:
    apply_food_factor_theme()  — set global matplotlib/seaborn style
    generate_all_charts()      — run all chart functions from analysis results
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server/pipeline use

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from config.brand import COLORS, CHART_SERIES_COLORS
from config.settings import BENCHMARKS

logger = logging.getLogger(__name__)

# TouchBistro-specific visualization settings
CHART_DPI: int = 200
CHART_WIDTH: int = 10       # inches
CHART_HEIGHT: int = 6       # inches
CHART_FONT_SIZE_TITLE: int = 16
CHART_FONT_SIZE_LABEL: int = 12
CHART_FONT_SIZE_TICK: int = 10
CHART_FONT_SIZE_ANNOTATION: int = 9
CHART_FORMAT: str = "png"
CHART_OUTPUT_DIR: Path = Path("charts")

CHART_PALETTE: list = CHART_SERIES_COLORS
RESTAURANT_NAME: str = "Coastal Table"
REPORT_PERIOD: str = "March 1–30, 2026"


# ──────────────────────────────────────────────
# GLOBAL STYLE SETUP
# ──────────────────────────────────────────────

def apply_food_factor_theme() -> None:
    """Apply Food Factor brand styling globally to matplotlib/seaborn."""
    plt.rcParams.update({
        "figure.facecolor":     COLORS["background"],
        "axes.facecolor":       COLORS["background"],
        "axes.edgecolor":       "#E0DDD5",
        "axes.labelcolor":      COLORS["text"],
        "axes.titleweight":     "bold",
        "axes.titlesize":       CHART_FONT_SIZE_TITLE,
        "axes.labelsize":       CHART_FONT_SIZE_LABEL,
        "xtick.labelsize":      CHART_FONT_SIZE_TICK,
        "ytick.labelsize":      CHART_FONT_SIZE_TICK,
        "xtick.color":          COLORS["text"],
        "ytick.color":          COLORS["text"],
        "text.color":           COLORS["text"],
        "font.family":          "sans-serif",
        "font.sans-serif":      [
            "Inter", "Helvetica Neue", "Arial", "DejaVu Sans",
        ],
        "legend.fontsize":      CHART_FONT_SIZE_TICK,
        "legend.framealpha":    0.9,
        "legend.edgecolor":     "#E0DDD5",
        "grid.color":           "#E0DDD5",
        "grid.alpha":           0.5,
        "grid.linewidth":       0.5,
        "figure.dpi":           CHART_DPI,
        "savefig.dpi":          CHART_DPI,
        "savefig.bbox":         "tight",
        "savefig.facecolor":    COLORS["background"],
    })
    sns.set_palette(CHART_PALETTE)


# Apply on import
apply_food_factor_theme()


# ──────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────

def _save_chart(
    fig: plt.Figure,
    filename: str,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Save figure to disk and close it."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.{CHART_FORMAT}"
    fig.savefig(
        filepath, dpi=CHART_DPI, bbox_inches="tight",
        facecolor=COLORS["background"],
    )
    plt.close(fig)
    logger.info(f"Chart saved: {filepath}")
    return filepath


def _add_watermark(ax: plt.Axes, text: str = "Food Factor") -> None:
    """Subtle branded watermark in bottom-right."""
    ax.text(
        0.99, 0.01, text,
        transform=ax.transAxes, fontsize=8, color="#E0DDD5",
        ha="right", va="bottom", style="italic", alpha=0.6,
    )


def _format_currency(x: float, _) -> str:
    """Axis formatter: $14.1K"""
    if abs(x) >= 1000:
        return f"${x / 1000:.0f}K"
    return f"${x:.0f}"


def _format_currency_full(x: float, _) -> str:
    """Axis formatter: $14,100"""
    return f"${x:,.0f}"


# ──────────────────────────────────────────────
# 01. DAILY REVENUE TREND
# ──────────────────────────────────────────────

def chart_daily_revenue(
    daily_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Line chart: daily net revenue with 7-day moving average.
    Annotates peak and trough days."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT))

    dates = pd.to_datetime(daily_df["Date"])
    revenue = daily_df["net_sales"]
    rolling_avg = revenue.rolling(window=7, min_periods=1).mean()

    ax.fill_between(dates, revenue, alpha=0.15, color=COLORS["primary"])
    ax.plot(
        dates, revenue, color=COLORS["primary"], linewidth=1.5,
        label="Daily Revenue", alpha=0.7,
    )
    ax.plot(
        dates, rolling_avg, color=COLORS["secondary"], linewidth=2.5,
        label="7-Day Avg", linestyle="-",
    )

    # Annotate peak
    peak_idx = revenue.idxmax()
    ax.annotate(
        f"Peak: ${revenue[peak_idx]:,.0f}",
        xy=(dates[peak_idx], revenue[peak_idx]),
        xytext=(15, 15), textcoords="offset points",
        fontsize=CHART_FONT_SIZE_ANNOTATION,
        color=COLORS["positive"], fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=COLORS["positive"], lw=1.5),
    )

    # Annotate trough
    trough_idx = revenue.idxmin()
    ax.annotate(
        f"Low: ${revenue[trough_idx]:,.0f}",
        xy=(dates[trough_idx], revenue[trough_idx]),
        xytext=(15, -20), textcoords="offset points",
        fontsize=CHART_FONT_SIZE_ANNOTATION,
        color=COLORS["negative"], fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=COLORS["negative"], lw=1.5),
    )

    ax.set_title(f"Daily Revenue — {RESTAURANT_NAME}", pad=15)
    ax.set_xlabel("")
    ax.set_ylabel("Net Sales")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    plt.xticks(rotation=45)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_xlim(dates.min(), dates.max())
    _add_watermark(ax)

    return _save_chart(fig, "01_daily_revenue", output_dir)


# ──────────────────────────────────────────────
# 02. DAY-OF-WEEK PERFORMANCE
# ──────────────────────────────────────────────

def chart_day_of_week(
    dow_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Vertical bar chart: average daily revenue by day of week."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.8))

    colors = [COLORS["primary"]] * len(dow_df)
    best_idx = dow_df["avg_daily_revenue"].idxmax()
    worst_idx = dow_df["avg_daily_revenue"].idxmin()
    colors[best_idx] = COLORS["positive"]
    colors[worst_idx] = COLORS["negative"]

    bars = ax.bar(
        dow_df["weekday_name"], dow_df["avg_daily_revenue"],
        color=colors, edgecolor="white", linewidth=0.5,
    )

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, height + 200,
            f"${height:,.0f}", ha="center", va="bottom",
            fontsize=CHART_FONT_SIZE_ANNOTATION, fontweight="bold",
            color=COLORS["text"],
        )

    ax.set_title("Average Daily Revenue by Day of Week", pad=15)
    ax.set_xlabel("")
    ax.set_ylabel("Avg Daily Net Sales")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_ylim(0, dow_df["avg_daily_revenue"].max() * 1.15)
    _add_watermark(ax)

    return _save_chart(fig, "02_day_of_week", output_dir)


# ──────────────────────────────────────────────
# MASTER CHART GENERATOR
# ──────────────────────────────────────────────

def generate_all_charts(
    sales_results: Dict[str, Any],
    menu_results: Dict[str, Any],
    payment_results: Dict[str, Any],
    ops_results: Dict[str, Any],
    delivery_df: pd.DataFrame,
    reservations_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Dict[str, Path]:
    """
    Generate core report charts.

    Args:
        sales_results:   Output from analysis.run_sales_analysis()
        menu_results:    Output from shared.menu_engineering.run_menu_engineering()
        payment_results: Output from analysis.run_payment_analysis()
        ops_results:     Output from analysis.run_operational_flags()
        delivery_df:     Cleaned delivery DataFrame from ingest
        reservations_df: Cleaned reservations DataFrame from ingest
        output_dir:      Directory to save chart images

    Returns:
        Dict mapping chart name → saved file path.
    """
    output_dir = Path(output_dir)
    charts: Dict[str, Path] = {}

    logger.info(f"Generating charts → {output_dir}")

    # Sales charts
    charts["daily_revenue"] = chart_daily_revenue(
        sales_results["daily_revenue"], output_dir)
    charts["day_of_week"] = chart_day_of_week(
        sales_results["day_of_week"], output_dir)

    logger.info(f"Generated {len(charts)} charts")
    return charts
