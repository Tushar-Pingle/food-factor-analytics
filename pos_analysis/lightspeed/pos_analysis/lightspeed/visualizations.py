"""
pos_analysis.lightspeed.visualizations — Professional Data Visualization

All 20 charts for the monthly consulting report, styled to Food Factor
brand standards using Plotly. Every chart is export-ready for PDF insertion.

Chart catalog:
    00  KPI Scorecard (executive dashboard)
    01  Daily Revenue Trend (bar + 7d rolling)
    02  Day-of-Week Revenue (bar)
    03  Daypart Breakdown (dual horizontal bar)
    04  Hourly Heatmap (hour × DOW)
    05  Floor Performance (horizontal bar)
    06  Menu Engineering Matrix (scatter quadrant)
    07  Top Items by Revenue (horizontal bar)
    08  Category Performance (stacked bar)
    09  Food Cost by Category (horizontal bar + benchmark)
    10  Payment Mix (horizontal bar)
    11  Tip by Payment Method (bar + benchmark)
    12  Labor by Day (grouped bar + labor % line)
    13  FOH/BOH Split (stacked horizontal)
    14  SPLH Trend (line + benchmark)
    15  Delivery Platform Comparison (grouped bar)
    16  Delivery Daily Trend (bar + rolling)
    17  Reservation Source (bar + no-show line)
    18  No-Show by Day (bar + benchmark)
    19  Void by Server (horizontal bar + benchmark)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from pos_analysis.shared import (
    COLORS, CHART_PALETTE, FONT_FAMILY, CHART_FONT_SIZE, TITLE_FONT_SIZE,
    ANNOTATION_FONT_SIZE, CHART_WIDTH, CHART_HEIGHT, CHART_SCALE,
    CHART_FORMAT, BENCHMARKS, get_plotly_template,
)
from pos_analysis.lightspeed import RESTAURANT_NAME, REPORT_PERIOD, CHART_DIR

logger = logging.getLogger(__name__)

TEMPLATE = None


def _get_template():
    global TEMPLATE
    if TEMPLATE is None:
        TEMPLATE = get_plotly_template()
    return TEMPLATE


def _save_chart(fig: go.Figure, filename: str, output_dir: Optional[Path] = None) -> Path:
    """Save chart to output directory at 2x resolution."""
    out = output_dir or CHART_DIR
    out.mkdir(parents=True, exist_ok=True)
    filepath = out / f"{filename}.{CHART_FORMAT}"
    fig.write_image(str(filepath), width=CHART_WIDTH, height=CHART_HEIGHT, scale=CHART_SCALE)
    logger.info(f"Saved chart: {filepath}")
    return filepath


def _brand_layout(fig: go.Figure, title: str = "", **overrides) -> go.Figure:
    """Apply Food Factor brand layout to any figure."""
    fig.update_layout(
        template=_get_template(),
        title=dict(text=title, font=dict(size=TITLE_FONT_SIZE, color=COLORS["primary"])),
        **overrides,
    )
    return fig


def _fmt_currency(val: float) -> str:
    return f"${val:,.0f}" if val >= 1000 else f"${val:,.2f}"


# ── SECTION 1: REVENUE CHARTS ───────────────────────────────────────

def chart_daily_revenue_trend(daily_trend: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Daily revenue line chart with 7-day rolling average."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily_trend["date"], y=daily_trend["net_revenue"],
        name="Daily Revenue", marker_color=COLORS["light_gray"], opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=daily_trend["date"], y=daily_trend["revenue_7d_avg"],
        name="7-Day Average", line=dict(color=COLORS["primary"], width=3), mode="lines",
    ))
    peak_idx = daily_trend["net_revenue"].idxmax()
    peak = daily_trend.loc[peak_idx]
    fig.add_annotation(
        x=peak["date"], y=peak["net_revenue"],
        text=f"Peak: {_fmt_currency(peak['net_revenue'])}",
        showarrow=True, arrowhead=2,
        font=dict(size=ANNOTATION_FONT_SIZE, color=COLORS["accent_2"]),
    )
    _brand_layout(fig, title="Daily Net Revenue — March 2026",
                  xaxis_title="Date", yaxis_title="Net Revenue ($)",
                  yaxis_tickprefix="$", yaxis_tickformat=",",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
    _save_chart(fig, "01_daily_revenue_trend", output_dir)
    return fig


def chart_day_of_week(dow_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Day-of-week average revenue bar chart."""
    fig = go.Figure()
    colors = [COLORS["primary"] if i < 5 else COLORS["secondary"] for i in range(len(dow_data))]
    fig.add_trace(go.Bar(
        x=dow_data.index, y=dow_data["avg_daily_revenue"], marker_color=colors,
        text=[_fmt_currency(v) for v in dow_data["avg_daily_revenue"]],
        textposition="outside", textfont=dict(size=ANNOTATION_FONT_SIZE),
    ))
    _brand_layout(fig, title="Average Daily Revenue by Day of Week",
                  xaxis_title="", yaxis_title="Avg Daily Revenue ($)",
                  yaxis_tickprefix="$", yaxis_tickformat=",", showlegend=False)
    _save_chart(fig, "02_day_of_week_revenue", output_dir)
    return fig


def chart_daypart_breakdown(daypart_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Daypart revenue and transaction count side-by-side."""
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Revenue by Daypart", "Transactions by Daypart"),
                        specs=[[{"type": "bar"}, {"type": "bar"}]])
    fig.add_trace(go.Bar(
        y=daypart_data.index, x=daypart_data["net_revenue"], orientation="h",
        marker_color=COLORS["primary"],
        text=[_fmt_currency(v) for v in daypart_data["net_revenue"]], textposition="outside",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        y=daypart_data.index, x=daypart_data["transaction_count"], orientation="h",
        marker_color=COLORS["secondary"],
        text=daypart_data["transaction_count"].astype(int).astype(str), textposition="outside",
    ), row=1, col=2)
    _brand_layout(fig, title="Daypart Performance", showlegend=False, height=450)
    _save_chart(fig, "03_daypart_breakdown", output_dir)
    return fig


def chart_hourly_heatmap(heatmap_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Hour × Day-of-Week revenue heatmap."""
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values, x=heatmap_data.columns,
        y=[f"{h}:00" for h in heatmap_data.index],
        colorscale=[
            [0.0, COLORS["background"]], [0.3, COLORS["secondary"]],
            [0.7, COLORS["accent_2"]], [1.0, COLORS["primary"]],
        ],
        text=[[_fmt_currency(v) for v in row] for row in heatmap_data.values],
        texttemplate="%{text}", textfont=dict(size=9),
        hovertemplate="<b>%{x} %{y}</b><br>Revenue: %{text}<extra></extra>",
    ))
    _brand_layout(fig, title="Revenue Heatmap — Hour × Day of Week",
                  xaxis_title="", yaxis_title="Hour", yaxis=dict(autorange="reversed"))
    _save_chart(fig, "04_hourly_heatmap", output_dir)
    return fig


def chart_floor_performance(floor_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Revenue by floor/section horizontal bar."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=floor_data.index, x=floor_data["net_revenue"], orientation="h",
        marker_color=[COLORS["primary"], COLORS["secondary"], COLORS["accent_1"]],
        text=[f"{_fmt_currency(v)} ({p:.0%})"
              for v, p in zip(floor_data["net_revenue"], floor_data["pct_of_total"])],
        textposition="outside",
    ))
    _brand_layout(fig, title="Revenue by Section",
                  xaxis_title="Net Revenue ($)", xaxis_tickprefix="$",
                  xaxis_tickformat=",", showlegend=False)
    _save_chart(fig, "05_floor_performance", output_dir)
    return fig


# ── SECTION 2: MENU ENGINEERING CHARTS ──────────────────────────────

def chart_menu_matrix(menu_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Menu engineering scatter plot — Stars/Plow Horses/Puzzles/Dogs."""
    quad_colors = {
        "Star": COLORS["positive"], "Plow Horse": COLORS["secondary"],
        "Puzzle": COLORS["neutral"], "Dog": COLORS["negative"],
    }
    fig = go.Figure()
    for classification, color in quad_colors.items():
        subset = menu_data[menu_data["classification"] == classification]
        fig.add_trace(go.Scatter(
            x=subset["quantity_sold"], y=subset["unit_margin"],
            mode="markers+text", name=classification,
            marker=dict(
                size=subset["total_revenue"] / menu_data["total_revenue"].max() * 40 + 8,
                color=color, opacity=0.8, line=dict(width=1, color=COLORS["text"]),
            ),
            text=subset["Name"], textposition="top center", textfont=dict(size=8),
            hovertemplate=(
                "<b>%{text}</b><br>Qty Sold: %{x}<br>"
                "Margin: $%{y:.2f}<br>Revenue: $%{customdata[0]:,.0f}<extra></extra>"
            ),
            customdata=subset[["total_revenue"]].values,
        ))

    pop_threshold = menu_data.attrs.get("pop_threshold", menu_data["quantity_sold"].median())
    margin_threshold = menu_data.attrs.get("margin_threshold", menu_data["unit_margin"].median())
    fig.add_hline(y=margin_threshold, line_dash="dash", line_color=COLORS["light_gray"], line_width=1,
                  annotation_text="Margin Threshold", annotation_position="bottom right")
    fig.add_vline(x=pop_threshold, line_dash="dash", line_color=COLORS["light_gray"], line_width=1,
                  annotation_text="Popularity Threshold", annotation_position="top right")

    x_range = menu_data["quantity_sold"].max()
    y_range = menu_data["unit_margin"].max()
    for label, x_pos, y_pos in [
        ("★ STARS", x_range * 0.85, y_range * 0.95),
        ("🐴 PLOW HORSES", x_range * 0.85, y_range * 0.05),
        ("🧩 PUZZLES", x_range * 0.05, y_range * 0.95),
        ("🐕 DOGS", x_range * 0.05, y_range * 0.05),
    ]:
        fig.add_annotation(x=x_pos, y=y_pos, text=f"<b>{label}</b>",
                          showarrow=False, font=dict(size=11, color=COLORS["text"]), opacity=0.5)

    _brand_layout(fig, title="Menu Engineering Matrix",
                  xaxis_title="Quantity Sold (Popularity)", yaxis_title="Contribution Margin ($)",
                  yaxis_tickprefix="$", height=700)
    _save_chart(fig, "06_menu_matrix", output_dir)
    return fig


def chart_top_items_revenue(top_items: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Top 10 items by revenue — horizontal bar."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top_items["Item_Name"][::-1], x=top_items["total_revenue"][::-1],
        orientation="h", marker_color=COLORS["primary"],
        text=[_fmt_currency(v) for v in top_items["total_revenue"][::-1]], textposition="outside",
    ))
    _brand_layout(fig, title="Top 10 Menu Items by Revenue",
                  xaxis_title="Total Revenue ($)", xaxis_tickprefix="$",
                  xaxis_tickformat=",", showlegend=False, margin=dict(l=200))
    _save_chart(fig, "07_top_items_revenue", output_dir)
    return fig


def chart_category_performance(cat_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Category revenue and margin stacked view."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Margin", y=cat_data["Category"], x=cat_data["total_margin"],
                         orientation="h", marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(name="COGS", y=cat_data["Category"], x=cat_data["total_cogs"],
                         orientation="h", marker_color=COLORS["negative"], opacity=0.6))
    _brand_layout(fig, title="Category Performance — Revenue Decomposition",
                  xaxis_title="Amount ($)", xaxis_tickprefix="$", barmode="stack",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02), margin=dict(l=150))
    _save_chart(fig, "08_category_performance", output_dir)
    return fig


def chart_food_cost_by_category(cat_cost: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Food cost % by category with benchmark line."""
    fig = go.Figure()
    colors = [COLORS["negative"] if v > BENCHMARKS["food_cost_pct_max"]
              else COLORS["secondary"] if v > BENCHMARKS["food_cost_pct"]
              else COLORS["positive"] for v in cat_cost["food_cost_pct"]]
    fig.add_trace(go.Bar(
        y=cat_cost["Category_Name"], x=cat_cost["food_cost_pct"] * 100, orientation="h",
        marker_color=colors,
        text=[f"{v:.1%}" for v in cat_cost["food_cost_pct"]], textposition="outside",
    ))
    fig.add_vline(x=BENCHMARKS["food_cost_pct"] * 100, line_dash="dash",
                  line_color=COLORS["primary"], line_width=2,
                  annotation_text=f"Target: {BENCHMARKS['food_cost_pct']:.0%}", annotation_position="top")
    _brand_layout(fig, title="Food Cost % by Category",
                  xaxis_title="Food Cost %", showlegend=False, margin=dict(l=150))
    _save_chart(fig, "09_food_cost_category", output_dir)
    return fig


# ── SECTION 3: PAYMENT CHARTS ──────────────────────────────────────

def chart_payment_mix(payment_mix: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Payment method distribution — horizontal bar."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=payment_mix["Payment_Name"], x=payment_mix["pct_by_volume"] * 100, orientation="h",
        marker_color=CHART_PALETTE[:len(payment_mix)],
        text=[f"{v:.1%}" for v in payment_mix["pct_by_volume"]], textposition="outside",
    ))
    _brand_layout(fig, title="Payment Method Distribution (by Volume)",
                  xaxis_title="% of Total Revenue", showlegend=False, margin=dict(l=150))
    _save_chart(fig, "10_payment_mix", output_dir)
    return fig


def chart_tip_by_payment(tip_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Average tip rate by payment method."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tip_data["Payment_Name"], y=tip_data["avg_tip_rate"] * 100,
        marker_color=COLORS["secondary"],
        text=[f"{v:.1%}" for v in tip_data["avg_tip_rate"]], textposition="outside",
    ))
    fig.add_hline(y=BENCHMARKS["avg_tip_pct"] * 100, line_dash="dash", line_color=COLORS["primary"],
                  annotation_text=f"Benchmark: {BENCHMARKS['avg_tip_pct']:.0%}")
    _brand_layout(fig, title="Average Tip Rate by Payment Method",
                  xaxis_title="", yaxis_title="Avg Tip %", showlegend=False)
    _save_chart(fig, "11_tip_by_payment", output_dir)
    return fig


# ── SECTION 4: LABOR CHARTS ────────────────────────────────────────

def chart_labor_by_day(labor_dow: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Labor cost and revenue overlay by day of week."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=labor_dow.index, y=labor_dow["avg_daily_revenue"],
                         name="Avg Revenue", marker_color=COLORS["primary"], opacity=0.7), secondary_y=False)
    fig.add_trace(go.Bar(x=labor_dow.index, y=labor_dow["avg_daily_cost"],
                         name="Avg Labor Cost", marker_color=COLORS["negative"], opacity=0.7), secondary_y=False)
    fig.add_trace(go.Scatter(x=labor_dow.index, y=labor_dow["labor_pct"] * 100,
                             name="Labor %", line=dict(color=COLORS["secondary"], width=3),
                             mode="lines+markers"), secondary_y=True)
    fig.add_hline(y=BENCHMARKS["labor_pct"] * 100, line_dash="dash", line_color=COLORS["accent_1"],
                  secondary_y=True, annotation_text=f"Target: {BENCHMARKS['labor_pct']:.0%}")
    _brand_layout(fig, title="Revenue vs Labor Cost by Day of Week",
                  barmode="group", legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(title_text="Amount ($)", tickprefix="$", secondary_y=False)
    fig.update_yaxes(title_text="Labor %", ticksuffix="%", secondary_y=True)
    _save_chart(fig, "12_labor_by_day", output_dir)
    return fig


def chart_foh_boh_split(split_data: Dict[str, Any], output_dir: Optional[Path] = None) -> go.Figure:
    """FOH vs BOH labor cost split — stacked horizontal bar."""
    breakdown = split_data.get("breakdown", pd.DataFrame())
    if breakdown.empty:
        return go.Figure()
    fig = go.Figure()
    for _, row in breakdown.iterrows():
        fig.add_trace(go.Bar(
            y=["Labor Split"], x=[row["labor_cost"]], name=row["User_Group"],
            orientation="h",
            marker_color=COLORS["primary"] if row["User_Group"] == "FOH" else COLORS["accent_2"],
            text=[f"{row['User_Group']}: {_fmt_currency(row['labor_cost'])} ({row['pct_of_total']:.0%})"],
            textposition="inside", textfont=dict(color="white", size=14),
        ))
    _brand_layout(fig, title="FOH vs BOH Labor Split",
                  barmode="stack", showlegend=False, height=250, margin=dict(l=100))
    _save_chart(fig, "13_foh_boh_split", output_dir)
    return fig


def chart_splh_trend(daily_summary: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Sales Per Labor Hour daily trend."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(daily_summary["date"]), y=daily_summary["splh"],
        mode="lines+markers", line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=4), name="SPLH",
    ))
    fig.add_hline(y=BENCHMARKS["splh_target"], line_dash="dash", line_color=COLORS["positive"],
                  annotation_text=f"Target: ${BENCHMARKS['splh_target']:.0f}")
    _brand_layout(fig, title="Sales Per Labor Hour (SPLH) — Daily Trend",
                  xaxis_title="Date", yaxis_title="SPLH ($)", yaxis_tickprefix="$")
    _save_chart(fig, "14_splh_trend", output_dir)
    return fig


# ── SECTION 5: DELIVERY CHARTS ─────────────────────────────────────

def chart_delivery_platform_compare(platform_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Platform comparison — gross vs net revenue."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=platform_data["Platform"], y=platform_data["gross_revenue"],
                         name="Gross Revenue", marker_color=COLORS["primary"]))
    fig.add_trace(go.Bar(x=platform_data["Platform"], y=platform_data["net_payout"],
                         name="Net Payout", marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(x=platform_data["Platform"], y=platform_data["total_commissions"],
                         name="Commissions", marker_color=COLORS["negative"]))
    _brand_layout(fig, title="Delivery Platform Comparison — Revenue Breakdown",
                  yaxis_title="Amount ($)", yaxis_tickprefix="$", barmode="group",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
    _save_chart(fig, "15_delivery_platform_compare", output_dir)
    return fig


def chart_delivery_daily_trend(daily_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Daily delivery order volume with rolling average."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily_data["date"], y=daily_data["order_count"],
                         name="Daily Orders", marker_color=COLORS["light_gray"], opacity=0.6))
    fig.add_trace(go.Scatter(x=daily_data["date"], y=daily_data["orders_7d_avg"],
                             name="7-Day Avg", line=dict(color=COLORS["accent_2"], width=3)))
    _brand_layout(fig, title="Daily Delivery Order Volume",
                  xaxis_title="Date", yaxis_title="Orders",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
    _save_chart(fig, "16_delivery_daily_trend", output_dir)
    return fig


# ── SECTION 6: RESERVATION CHARTS ──────────────────────────────────

def chart_reservation_source(source_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Reservation source distribution with no-show rates."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=source_data["Source"], y=source_data["total_reservations"],
                         name="Reservations", marker_color=COLORS["primary"]), secondary_y=False)
    fig.add_trace(go.Scatter(x=source_data["Source"], y=source_data["no_show_rate"] * 100,
                             name="No-Show Rate", mode="lines+markers",
                             line=dict(color=COLORS["negative"], width=3),
                             marker=dict(size=10)), secondary_y=True)
    fig.add_hline(y=BENCHMARKS["no_show_rate_max"] * 100, line_dash="dash",
                  line_color=COLORS["negative"], secondary_y=True,
                  annotation_text=f"Alarm: {BENCHMARKS['no_show_rate_max']:.0%}", opacity=0.5)
    _brand_layout(fig, title="Reservations by Source & No-Show Rate",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(title_text="Reservations", secondary_y=False)
    fig.update_yaxes(title_text="No-Show Rate %", ticksuffix="%", secondary_y=True)
    _save_chart(fig, "17_reservation_source", output_dir)
    return fig


def chart_no_show_by_day(dow_data: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """No-show rate by day of week."""
    fig = go.Figure()
    colors = [COLORS["negative"] if v > BENCHMARKS["no_show_rate_max"]
              else COLORS["secondary"] for v in dow_data["no_show_rate"]]
    fig.add_trace(go.Bar(
        x=dow_data.index, y=dow_data["no_show_rate"] * 100, marker_color=colors,
        text=[f"{v:.1%}" for v in dow_data["no_show_rate"]], textposition="outside",
    ))
    fig.add_hline(y=BENCHMARKS["no_show_rate_max"] * 100, line_dash="dash",
                  line_color=COLORS["negative"],
                  annotation_text=f"Benchmark: {BENCHMARKS['no_show_rate_max']:.0%}")
    _brand_layout(fig, title="No-Show Rate by Day of Week",
                  xaxis_title="", yaxis_title="No-Show Rate %", showlegend=False)
    _save_chart(fig, "18_no_show_by_day", output_dir)
    return fig


# ── SECTION 7: OPERATIONAL FLAGS CHARTS ─────────────────────────────

def chart_void_by_server(server_voids: pd.DataFrame, output_dir: Optional[Path] = None) -> go.Figure:
    """Void rate by server — flag outliers."""
    fig = go.Figure()
    colors = [COLORS["negative"] if f else COLORS["primary"] for f in server_voids["flagged"]]
    fig.add_trace(go.Bar(
        y=server_voids["Username"], x=server_voids["void_rate"] * 100, orientation="h",
        marker_color=colors,
        text=[f"{v:.1%}" for v in server_voids["void_rate"]], textposition="outside",
    ))
    fig.add_vline(x=BENCHMARKS["void_rate_max"] * 100, line_dash="dash",
                  line_color=COLORS["negative"],
                  annotation_text=f"Benchmark: {BENCHMARKS['void_rate_max']:.0%}")
    _brand_layout(fig, title="Void Rate by Server",
                  xaxis_title="Void Rate %", showlegend=False, margin=dict(l=120))
    _save_chart(fig, "19_void_by_server", output_dir)
    return fig


# ── SECTION 8: KPI SCORECARD ───────────────────────────────────────

def chart_kpi_scorecard(
    revenue_summary: Dict, labor_summary: Dict,
    reservation_summary: Dict, delivery_summary: Dict,
    output_dir: Optional[Path] = None,
) -> go.Figure:
    """Executive KPI scorecard — single-page visual with key metrics."""
    fig = go.Figure()
    metrics = [
        ("Net Revenue",   _fmt_currency(revenue_summary["total_net_revenue"]), ""),
        ("Avg Check",     _fmt_currency(revenue_summary["avg_check"]), ""),
        ("Total Covers",  f"{revenue_summary['total_covers']:,}", ""),
        ("Labor %",       f"{labor_summary['labor_pct']:.1%}",
         "🟢" if labor_summary["labor_pct"] <= BENCHMARKS["labor_pct"] else "🔴"),
        ("SPLH",          f"${labor_summary['splh']:.0f}",
         "🟢" if labor_summary["splh"] >= BENCHMARKS["splh_target"] else "🔴"),
        ("No-Show Rate",  f"{reservation_summary.get('no_show_rate', 0):.1%}",
         "🟢" if reservation_summary.get("no_show_rate", 0) <= BENCHMARKS["no_show_rate_max"] else "🔴"),
        ("Delivery Net",  _fmt_currency(delivery_summary.get("net_payout", 0)), ""),
        ("Tip Rate",      f"{revenue_summary['avg_tip_rate']:.1%}", ""),
    ]

    n_cols, n_rows = 4, 2
    for i, (label, value, status) in enumerate(metrics):
        row, col = i // n_cols, i % n_cols
        x = col / n_cols + 0.5 / n_cols
        y = 1 - (row / n_rows + 0.5 / n_rows)
        fig.add_annotation(x=x, y=y + 0.08, text=f"<b>{value}</b>",
                          font=dict(size=28, color=COLORS["primary"]),
                          showarrow=False, xref="paper", yref="paper")
        fig.add_annotation(x=x, y=y - 0.08, text=f"{status} {label}",
                          font=dict(size=13, color=COLORS["text"]),
                          showarrow=False, xref="paper", yref="paper")

    fig.update_layout(
        template=_get_template(),
        title=dict(
            text=f"<b>{RESTAURANT_NAME}</b> — Executive Dashboard — {REPORT_PERIOD}",
            font=dict(size=18, color=COLORS["primary"]), x=0.5, xanchor="center",
        ),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=350, margin=dict(l=30, r=30, t=70, b=30),
    )
    _save_chart(fig, "00_kpi_scorecard", output_dir)
    return fig


# ── MASTER CHART GENERATOR ──────────────────────────────────────────

def generate_all_charts(
    sales_results: Dict, menu_results: Dict, payment_results: Dict,
    labor_results: Dict, delivery_results: Dict, reservation_results: Dict,
    ops_results: Dict, daily_summary: pd.DataFrame,
    output_dir: Optional[Path] = None,
) -> Dict[str, go.Figure]:
    """Generate all 20 charts for the monthly report."""
    logger.info("Generating all charts...")
    out = output_dir or CHART_DIR
    charts: Dict[str, go.Figure] = {}

    charts["kpi_scorecard"] = chart_kpi_scorecard(
        sales_results["revenue_summary"], labor_results["labor_summary"],
        reservation_results.get("summary", {}), delivery_results.get("summary", {}), out)

    charts["daily_revenue"] = chart_daily_revenue_trend(sales_results["daily_trend"], out)
    charts["day_of_week"] = chart_day_of_week(sales_results["day_of_week"], out)
    charts["daypart"] = chart_daypart_breakdown(sales_results["daypart"], out)
    charts["heatmap"] = chart_hourly_heatmap(sales_results["hourly_heatmap"], out)
    charts["floor"] = chart_floor_performance(sales_results["floor_performance"], out)

    charts["menu_matrix"] = chart_menu_matrix(menu_results["menu_matrix"], out)
    charts["top_items"] = chart_top_items_revenue(sales_results["top_items"], out)
    charts["category"] = chart_category_performance(sales_results["category_performance"], out)
    charts["food_cost"] = chart_food_cost_by_category(menu_results["food_cost"]["by_category"], out)

    charts["payment_mix"] = chart_payment_mix(payment_results["payment_mix"], out)
    charts["tip_by_payment"] = chart_tip_by_payment(payment_results["tip_by_payment"], out)

    charts["labor_day"] = chart_labor_by_day(labor_results["by_day"], out)
    charts["foh_boh"] = chart_foh_boh_split(labor_results["foh_boh_split"], out)
    charts["splh"] = chart_splh_trend(daily_summary, out)

    if delivery_results.get("status") != "no_data":
        charts["delivery_platform"] = chart_delivery_platform_compare(delivery_results["platform_compare"], out)
        charts["delivery_daily"] = chart_delivery_daily_trend(delivery_results["daily_trend"], out)

    if reservation_results.get("status") != "no_data":
        charts["res_source"] = chart_reservation_source(reservation_results["by_source"], out)
        charts["no_show_dow"] = chart_no_show_by_day(reservation_results["by_day_of_week"], out)

    charts["void_server"] = chart_void_by_server(ops_results["void_analysis"]["by_server"], out)

    logger.info(f"Generated {len(charts)} charts → {out}")
    return charts
