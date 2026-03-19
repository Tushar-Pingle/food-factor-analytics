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

from .config import (
    COLORS,
    CHART_PALETTE,
    CHART_DPI,
    CHART_WIDTH,
    CHART_HEIGHT,
    CHART_FONT_SIZE_TITLE,
    CHART_FONT_SIZE_LABEL,
    CHART_FONT_SIZE_TICK,
    CHART_FONT_SIZE_ANNOTATION,
    CHART_FORMAT,
    CHART_OUTPUT_DIR,
    RESTAURANT_NAME,
    REPORT_PERIOD,
    BENCHMARKS,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# GLOBAL STYLE SETUP
# ──────────────────────────────────────────────

def apply_food_factor_theme() -> None:
    """Apply Food Factor brand styling globally to matplotlib/seaborn."""
    plt.rcParams.update({
        "figure.facecolor":     COLORS["background"],
        "axes.facecolor":       COLORS["background"],
        "axes.edgecolor":       COLORS["light_gray"],
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
        "legend.edgecolor":     COLORS["light_gray"],
        "grid.color":           COLORS["light_gray"],
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
        transform=ax.transAxes, fontsize=8, color=COLORS["light_gray"],
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
# 03. DAYPART ANALYSIS
# ──────────────────────────────────────────────

def chart_daypart(
    dp_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: revenue by daypart with percentage labels."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.7))

    dp_sorted = dp_df.sort_values("total_net", ascending=True)

    bars = ax.barh(
        dp_sorted["daypart"], dp_sorted["total_net"],
        color=CHART_PALETTE[:len(dp_sorted)], edgecolor="white", linewidth=0.5,
    )

    for bar, pct in zip(bars, dp_sorted["pct_revenue"]):
        width = bar.get_width()
        ax.text(
            width + 500, bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f} ({pct:.0f}%)",
            ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION, fontweight="bold",
        )

    ax.set_title("Revenue by Daypart", pad=15)
    ax.set_xlabel("Net Sales")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "03_daypart_revenue", output_dir)


# ──────────────────────────────────────────────
# 04. REVENUE HEATMAP (hour × day of week)
# ──────────────────────────────────────────────

def chart_hourly_heatmap(
    heatmap_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Heatmap: revenue by hour (columns) × day of week (rows)."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH * 1.2, CHART_HEIGHT * 0.8))

    heatmap_filtered = heatmap_df.loc[:, (heatmap_df.sum() > 0)]
    hour_labels = [f"{h}:00" for h in heatmap_filtered.columns]

    sns.heatmap(
        heatmap_filtered,
        ax=ax,
        cmap=sns.light_palette(COLORS["primary"], as_cmap=True),
        annot=True, fmt=",.0f",
        annot_kws={"size": 7},
        linewidths=1, linecolor=COLORS["background"],
        cbar_kws={"label": "Net Sales ($)", "shrink": 0.8},
        xticklabels=hour_labels,
    )

    ax.set_title("Revenue Heatmap — Day of Week × Hour", pad=15)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("")
    plt.xticks(rotation=45)
    _add_watermark(ax)

    return _save_chart(fig, "04_hourly_heatmap", output_dir)


# ──────────────────────────────────────────────
# 05. TOP ITEMS BY REVENUE
# ──────────────────────────────────────────────

def chart_top_items(
    top_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: top 10 items by net sales."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.8))

    top_sorted = top_df.sort_values("net_sales", ascending=True)

    bars = ax.barh(
        top_sorted["Menu_Item"], top_sorted["net_sales"],
        color=COLORS["primary"], edgecolor="white", linewidth=0.5,
    )

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 200, bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f}",
            ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION,
        )

    ax.set_title("Top 10 Items by Revenue", pad=15)
    ax.set_xlabel("Net Sales")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "05_top_items_revenue", output_dir)


# ──────────────────────────────────────────────
# 06. CATEGORY PERFORMANCE
# ──────────────────────────────────────────────

def chart_category_performance(
    cat_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: revenue by menu category."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.8))

    cat_sorted = cat_df.sort_values("net_sales", ascending=True)
    n = len(cat_sorted)
    palette = sns.color_palette(
        sns.light_palette(COLORS["primary"], n_colors=n + 2, reverse=True)[1:-1]
    )

    bars = ax.barh(
        cat_sorted["Menu_Category"], cat_sorted["net_sales"],
        color=palette, edgecolor="white", linewidth=0.5,
    )

    for bar, pct in zip(bars, cat_sorted["pct_revenue"]):
        width = bar.get_width()
        ax.text(
            width + 200, bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f} ({pct:.0f}%)",
            ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION,
        )

    ax.set_title("Revenue by Menu Category", pad=15)
    ax.set_xlabel("Net Sales")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "06_category_performance", output_dir)


# ──────────────────────────────────────────────
# 07. MENU ENGINEERING MATRIX (scatter)
# ──────────────────────────────────────────────

def chart_menu_matrix(
    classified_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Scatter plot: contribution margin × quantity sold, colored by quadrant."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_WIDTH * 0.8))

    df = classified_df.copy()
    quadrant_colors = {
        "Star":      COLORS["positive"],
        "Plowhorse": COLORS["secondary"],
        "Puzzle":    COLORS["neutral"],
        "Dog":       COLORS["negative"],
    }

    for quad, color in quadrant_colors.items():
        mask = df["quadrant"] == quad
        subset = df[mask]
        ax.scatter(
            subset["contribution_margin"],
            subset["Quantity_Sold"],
            c=color, s=subset["Net_Sales"] / 50,
            alpha=0.7, edgecolors="white", linewidth=0.5,
            label=f"{quad} ({len(subset)})",
        )
        for _, row in subset.iterrows():
            ax.annotate(
                row["Menu_Item"],
                (row["contribution_margin"], row["Quantity_Sold"]),
                fontsize=7, alpha=0.8,
                xytext=(4, 4), textcoords="offset points",
            )

    # Quadrant divider lines
    avg_margin = df["contribution_margin"].mean()
    avg_qty = df["Quantity_Sold"].mean() * 0.70
    ax.axvline(avg_margin, color=COLORS["light_gray"], linestyle="--", linewidth=1)
    ax.axhline(avg_qty, color=COLORS["light_gray"], linestyle="--", linewidth=1)

    # Quadrant labels
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    label_kw = dict(
        fontsize=12, fontweight="bold", alpha=0.25, ha="center", va="center",
    )
    ax.text(
        (avg_margin + xlim[1]) / 2, (avg_qty + ylim[1]) / 2,
        "STARS", color=COLORS["positive"], **label_kw,
    )
    ax.text(
        (xlim[0] + avg_margin) / 2, (avg_qty + ylim[1]) / 2,
        "PLOWHORSES", color=COLORS["secondary"], **label_kw,
    )
    ax.text(
        (avg_margin + xlim[1]) / 2, (ylim[0] + avg_qty) / 2,
        "PUZZLES", color=COLORS["neutral"], **label_kw,
    )
    ax.text(
        (xlim[0] + avg_margin) / 2, (ylim[0] + avg_qty) / 2,
        "DOGS", color=COLORS["negative"], **label_kw,
    )

    ax.set_title("Menu Engineering Matrix", pad=15)
    ax.set_xlabel("Contribution Margin per Unit ($)")
    ax.set_ylabel("Quantity Sold")
    ax.legend(loc="upper right", frameon=True)
    ax.grid(alpha=0.2)
    _add_watermark(ax)

    return _save_chart(fig, "07_menu_matrix", output_dir)


# ──────────────────────────────────────────────
# 08. FOOD COST BY CATEGORY
# ──────────────────────────────────────────────

def chart_food_cost_by_category(
    food_cost_data: Dict[str, Any],
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: food cost % by category with benchmark band."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.7))

    by_cat = food_cost_data["by_category"].sort_values(
        "food_cost_pct", ascending=True,
    )
    low_bench, high_bench = food_cost_data["benchmark_range"]

    ax.axvspan(
        low_bench, high_bench, alpha=0.1, color=COLORS["positive"],
        label=f"Benchmark: {low_bench}–{high_bench}%",
    )

    bar_colors = []
    for _, row in by_cat.iterrows():
        pct = row["food_cost_pct"]
        if pct > high_bench:
            bar_colors.append(COLORS["negative"])
        elif pct < low_bench:
            bar_colors.append(COLORS["neutral"])
        else:
            bar_colors.append(COLORS["positive"])

    bars = ax.barh(
        by_cat["Menu_Category"], by_cat["food_cost_pct"],
        color=bar_colors, edgecolor="white", linewidth=0.5,
    )

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 0.3, bar.get_y() + bar.get_height() / 2,
            f"{width:.1f}%", ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION, fontweight="bold",
        )

    ax.set_title("Food Cost % by Category", pad=15)
    ax.set_xlabel("Food Cost %")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "08_food_cost_category", output_dir)


# ──────────────────────────────────────────────
# 09. PAYMENT METHOD MIX
# ──────────────────────────────────────────────

def chart_payment_mix(
    payment_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: payment method share of revenue."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.6))

    pay_sorted = payment_df.sort_values("Total_Amount", ascending=True)

    bars = ax.barh(
        pay_sorted["Payment_Method"], pay_sorted["Total_Amount"],
        color=CHART_PALETTE[:len(pay_sorted)], edgecolor="white", linewidth=0.5,
    )

    for bar, pct in zip(bars, pay_sorted["pct_of_total"]):
        width = bar.get_width()
        ax.text(
            width + 500, bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f} ({pct:.0f}%)",
            ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION,
        )

    ax.set_title("Payment Method Breakdown", pad=15)
    ax.set_xlabel("Total Amount")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "09_payment_mix", output_dir)


# ──────────────────────────────────────────────
# 10. SERVER PERFORMANCE
# ──────────────────────────────────────────────

def chart_server_performance(
    server_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Grouped bar + line: revenue and avg check per server (top 8)."""
    fig, ax1 = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.8))

    top_servers = server_df.head(8).copy()
    x = range(len(top_servers))

    ax1.bar(
        x, top_servers["net_sales"],
        color=COLORS["primary"], alpha=0.8, label="Total Revenue",
        edgecolor="white", linewidth=0.5,
    )
    ax1.set_ylabel("Total Net Sales", color=COLORS["primary"])
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))

    ax2 = ax1.twinx()
    ax2.plot(
        x, top_servers["avg_check"],
        color=COLORS["secondary"], marker="o", linewidth=2, markersize=8,
        label="Avg Check",
    )
    ax2.set_ylabel("Avg Check ($)", color=COLORS["secondary"])

    ax1.set_xticks(x)
    ax1.set_xticklabels(top_servers["Waiter"], rotation=45, ha="right")
    ax1.set_title("Server Performance — Revenue & Avg Check", pad=15)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    ax1.grid(axis="y", linestyle="--", alpha=0.3)
    _add_watermark(ax1)

    return _save_chart(fig, "10_server_performance", output_dir)


# ──────────────────────────────────────────────
# 11. VOID RATE BY SERVER
# ──────────────────────────────────────────────

def chart_void_rate_by_server(
    by_server_df: pd.DataFrame,
    threshold: float,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: void rate by server with alert threshold line."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT * 0.7))

    srv = by_server_df.sort_values("void_rate_pct", ascending=True)
    bar_colors = [
        COLORS["negative"] if r > threshold else COLORS["primary"]
        for r in srv["void_rate_pct"]
    ]

    bars = ax.barh(
        srv["server"], srv["void_rate_pct"],
        color=bar_colors, edgecolor="white", linewidth=0.5,
    )

    ax.axvline(
        threshold, color=COLORS["negative"], linestyle="--",
        linewidth=1.5, label=f"Threshold: {threshold}%",
    )

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 0.05, bar.get_y() + bar.get_height() / 2,
            f"{width:.1f}%", ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION,
        )

    ax.set_title("Void Rate by Server", pad=15)
    ax.set_xlabel("Void Rate (%)")
    ax.legend(loc="lower right")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "11_void_rate_server", output_dir)


# ──────────────────────────────────────────────
# 12. DELIVERY PLATFORM COMPARISON
# ──────────────────────────────────────────────

def chart_delivery_comparison(
    delivery_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Grouped bar: gross vs net by platform showing commission impact."""
    completed = delivery_df[~delivery_df["is_canceled"]].copy()
    if completed.empty:
        logger.warning("No completed delivery orders to chart")
        return Path()

    by_platform = completed.groupby("Platform").agg(
        gross=("Gross_Sales", "sum"),
        net_payout=("Net_Payout", "sum"),
        orders=("Order_ID", "count"),
        avg_rating=("Customer_Rating", "mean"),
    ).reset_index()
    by_platform["commission_lost"] = by_platform["gross"] - by_platform["net_payout"]

    fig, ax = plt.subplots(figsize=(CHART_WIDTH * 0.8, CHART_HEIGHT * 0.7))

    x = range(len(by_platform))
    width = 0.35

    ax.bar(
        [i - width / 2 for i in x], by_platform["gross"],
        width, label="Gross Sales", color=COLORS["primary"],
    )
    ax.bar(
        [i + width / 2 for i in x], by_platform["net_payout"],
        width, label="Net Payout", color=COLORS["positive"],
    )

    for i, row in by_platform.iterrows():
        ax.annotate(
            f"-${row['commission_lost']:,.0f}\n"
            f"({row['commission_lost'] / row['gross'] * 100:.0f}%)",
            xy=(i, row["gross"]),
            xytext=(0, 10), textcoords="offset points",
            fontsize=CHART_FONT_SIZE_ANNOTATION,
            color=COLORS["negative"], fontweight="bold", ha="center",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(by_platform["Platform"])
    ax.set_title("Delivery Platforms — Gross vs Net Payout", pad=20)
    ax.set_ylabel("Revenue ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "12_delivery_comparison", output_dir)


# ──────────────────────────────────────────────
# 13. RESERVATION STATUS BREAKDOWN
# ──────────────────────────────────────────────

def chart_reservation_status(
    reservations_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bar chart: reservation status distribution."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH * 0.8, CHART_HEIGHT * 0.5))

    status_counts = reservations_df["Status"].value_counts()
    total = status_counts.sum()
    status_df = status_counts.reset_index()
    status_df.columns = ["Status", "count"]
    status_df["pct"] = (status_df["count"] / total * 100).round(1)
    status_df = status_df.sort_values("count", ascending=True)

    status_colors = {
        "Completed":    COLORS["positive"],
        "No-Show":      COLORS["negative"],
        "Canceled":     COLORS["neutral"],
        "Late Cancel":  COLORS["secondary"],
    }
    bar_colors = [
        status_colors.get(s, COLORS["primary"]) for s in status_df["Status"]
    ]

    bars = ax.barh(
        status_df["Status"], status_df["count"],
        color=bar_colors, edgecolor="white", linewidth=0.5,
    )

    for bar, pct in zip(bars, status_df["pct"]):
        width = bar.get_width()
        ax.text(
            width + 5, bar.get_y() + bar.get_height() / 2,
            f"{int(width)} ({pct:.0f}%)", ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION, fontweight="bold",
        )

    ax.set_title("Reservation Status Breakdown", pad=15)
    ax.set_xlabel("Count")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "13_reservation_status", output_dir)


# ──────────────────────────────────────────────
# 14. SALES CATEGORY SPLIT (Food vs Alcohol)
# ──────────────────────────────────────────────

def chart_sales_category_split(
    sc_df: pd.DataFrame,
    output_dir: Path = CHART_OUTPUT_DIR,
) -> Path:
    """Horizontal bars: Food vs Alcohol vs Non-Alcoholic."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH * 0.8, CHART_HEIGHT * 0.5))

    sc_sorted = sc_df.sort_values("net_sales", ascending=True)
    cat_colors = {
        "Food":           COLORS["primary"],
        "Alcohol":        COLORS["secondary"],
        "Non-Alcoholic":  COLORS["accent_1"],
    }
    bar_colors = [
        cat_colors.get(c, COLORS["neutral"]) for c in sc_sorted["Sales_Category"]
    ]

    bars = ax.barh(
        sc_sorted["Sales_Category"], sc_sorted["net_sales"],
        color=bar_colors, edgecolor="white", linewidth=0.5,
    )

    for bar, pct in zip(bars, sc_sorted["pct_revenue"]):
        width = bar.get_width()
        ax.text(
            width + 500, bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f} ({pct:.0f}%)", ha="left", va="center",
            fontsize=CHART_FONT_SIZE_ANNOTATION, fontweight="bold",
        )

    ax.set_title("Revenue by Sales Category", pad=15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_format_currency))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    _add_watermark(ax)

    return _save_chart(fig, "14_sales_category_split", output_dir)


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
    Generate all 14 report charts.

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

    logger.info(f"Generating all charts → {output_dir}")

    # Sales charts
    charts["daily_revenue"] = chart_daily_revenue(
        sales_results["daily_revenue"], output_dir)
    charts["day_of_week"] = chart_day_of_week(
        sales_results["day_of_week"], output_dir)
    charts["daypart"] = chart_daypart(
        sales_results["daypart"], output_dir)
    charts["hourly_heatmap"] = chart_hourly_heatmap(
        sales_results["hourly_heatmap"], output_dir)
    charts["top_items"] = chart_top_items(
        sales_results["top_bottom_items"]["top_by_revenue"], output_dir)
    charts["category_performance"] = chart_category_performance(
        sales_results["category_performance"], output_dir)
    charts["sales_category_split"] = chart_sales_category_split(
        sales_results["sales_category_split"], output_dir)
    charts["server_performance"] = chart_server_performance(
        sales_results["server_performance"], output_dir)

    # Menu engineering charts
    charts["menu_matrix"] = chart_menu_matrix(
        menu_results["classified_items"], output_dir)
    charts["food_cost_category"] = chart_food_cost_by_category(
        menu_results["food_cost"], output_dir)

    # Payment charts
    charts["payment_mix"] = chart_payment_mix(
        payment_results["payment_summary"], output_dir)

    # Operational charts
    charts["void_rate_server"] = chart_void_rate_by_server(
        ops_results["voids"]["by_server"],
        ops_results["voids"]["threshold"],
        output_dir,
    )

    # Delivery charts
    if not delivery_df.empty:
        charts["delivery_comparison"] = chart_delivery_comparison(
            delivery_df, output_dir)

    # Reservation charts
    if not reservations_df.empty:
        charts["reservation_status"] = chart_reservation_status(
            reservations_df, output_dir)

    logger.info(f"Generated {len(charts)} charts")
    return charts
