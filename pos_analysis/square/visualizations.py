"""
pos_analysis/square/visualizations.py — Square Chart Engine
=============================================================
Professional Plotly visualizations styled to Food Factor brand
standards.  Every chart is export-ready for PDF embedding (3× scale
PNG) and falls back to interactive HTML when Chrome is unavailable.

Usage::

    from pos_analysis.square.visualizations import FoodFactorCharts

    charts = FoodFactorCharts(output_dir="output/charts")
    charts.revenue_daily_trend(sales_results["daily_trend"])
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import settings
from config.brand import (
    COLORS, CHART_SERIES_COLORS, FONT_FAMILY,
    TITLE_FONT_SIZE, AXIS_FONT_SIZE, TICK_FONT_SIZE,
    DEFAULT_WIDTH, DEFAULT_HEIGHT, get_plotly_template,
)

logger = logging.getLogger("food_factor.square.viz")


class FoodFactorCharts:
    """
    Generate all charts for the Food Factor monthly report.

    Every chart method:
    1. Creates a Plotly figure with brand styling
    2. Saves to disk as PNG (3× scale for PDF embedding)
    3. Returns the figure object for optional inline display
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else settings.CHARTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─── layout / export helpers ──────────────

    def _base_layout(self, title: str, **overrides: Any) -> dict:
        """Standard layout applied to every chart."""
        layout = dict(
            title=dict(
                text=title,
                font=dict(
                    family=FONT_FAMILY,
                    size=TITLE_FONT_SIZE,
                    color=COLORS["primary"],
                ),
                x=0.02,
                xanchor="left",
            ),
            font=dict(
                family=FONT_FAMILY,
                size=AXIS_FONT_SIZE,
                color=COLORS["text"],
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            margin=dict(l=60, r=30, t=60, b=60),
            legend=dict(
                font=dict(size=TICK_FONT_SIZE),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor=COLORS["light_gray"],
                borderwidth=1,
            ),
            xaxis=dict(
                gridcolor=COLORS["light_gray"],
                gridwidth=0.5,
                tickfont=dict(size=TICK_FONT_SIZE),
                linecolor=COLORS["light_gray"],
            ),
            yaxis=dict(
                gridcolor=COLORS["light_gray"],
                gridwidth=0.5,
                tickfont=dict(size=TICK_FONT_SIZE),
                linecolor=COLORS["light_gray"],
            ),
        )
        layout.update(overrides)
        return layout

    def _save(self, fig: go.Figure, filename: str) -> Path:
        """Export chart to PNG (with HTML fallback)."""
        fpath = self.output_dir / f"{filename}.png"
        try:
            fig.write_image(str(fpath), scale=3)  # 3x resolution for PDF embedding
            logger.info("Chart saved: %s", fpath)
        except Exception as exc:
            logger.warning(
                "Could not export %s: %s. Saving HTML fallback.", fpath, exc,
            )
            html_path = self.output_dir / f"{filename}.html"
            fig.write_html(str(html_path))
            return html_path
        return fpath

    # ═══════════════════════════════════════════
    # SALES CHARTS
    # ═══════════════════════════════════════════

    def revenue_daily_trend(self, daily: pd.DataFrame) -> go.Figure:
        """Daily net sales trend with 7-day moving average."""
        daily = daily.copy()
        daily["ma_7"] = daily["net_sales"].rolling(7, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily["date_only"], y=daily["net_sales"],
            name="Daily Revenue",
            marker_color=COLORS["primary"], opacity=0.6,
        ))
        fig.add_trace(go.Scatter(
            x=daily["date_only"], y=daily["ma_7"],
            name="7-Day Avg",
            line=dict(color=COLORS["secondary"], width=3),
            mode="lines",
        ))
        fig.update_layout(**self._base_layout(
            "Daily Revenue Trend",
            yaxis_title="Net Sales ($)",
            yaxis_tickformat="$,.0f",
            barmode="overlay",
        ))
        self._save(fig, "sales_daily_trend")
        return fig

    def day_of_week_revenue(self, dow: pd.DataFrame) -> go.Figure:
        """Average daily revenue by day of week."""
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dow["day_of_week"],
            y=dow["avg_daily_rev"],
            marker_color=[
                COLORS["accent_2"] if d in ("Friday", "Saturday") else COLORS["primary"]
                for d in dow["day_of_week"]
            ],
            text=[f"${v:,.0f}" for v in dow["avg_daily_rev"]],
            textposition="outside",
            textfont=dict(size=11, color=COLORS["text"]),
        ))
        fig.update_layout(**self._base_layout(
            "Average Daily Revenue by Day of Week",
            yaxis_title="Avg Daily Revenue ($)",
            yaxis_tickformat="$,.0f",
            showlegend=False,
        ))
        self._save(fig, "sales_dow_revenue")
        return fig

    def daypart_breakdown(self, daypart: pd.DataFrame) -> go.Figure:
        """Revenue by daypart as horizontal bar chart."""
        dp = daypart.sort_values("net_sales", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=dp["daypart"], x=dp["net_sales"],
            orientation="h",
            marker_color=CHART_PALETTE[: len(dp)],
            text=[
                f"${v:,.0f} ({p:.0%})"
                for v, p in zip(dp["net_sales"], dp["pct_of_revenue"])
            ],
            textposition="outside",
            textfont=dict(size=11),
        ))
        fig.update_layout(**self._base_layout(
            "Revenue by Daypart",
            xaxis_title="Net Sales ($)",
            xaxis_tickformat="$,.0f",
            showlegend=False,
            height=400,
        ))
        self._save(fig, "sales_daypart")
        return fig

    def order_type_mix(self, ot: pd.DataFrame) -> go.Figure:
        """Revenue by order type — horizontal stacked bar."""
        fig = go.Figure()
        colors = {
            "Dine-In": COLORS["primary"],
            "Takeout": COLORS["secondary"],
            "Delivery": COLORS["accent_1"],
        }
        for _, row in ot.iterrows():
            fig.add_trace(go.Bar(
                y=["Revenue"], x=[row["net_sales"]],
                name=f"{row['order_type']} ({row['pct_of_revenue']:.0%})",
                orientation="h",
                marker_color=colors.get(row["order_type"], COLORS["neutral"]),
                text=[f"${row['net_sales']:,.0f}"],
                textposition="inside",
                textfont=dict(color="white", size=13),
            ))
        fig.update_layout(**self._base_layout(
            "Revenue by Order Type",
            barmode="stack",
            xaxis_tickformat="$,.0f",
            height=250,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        ))
        self._save(fig, "sales_order_type")
        return fig

    def hourly_heatmap(self, heatmap_data: pd.DataFrame) -> go.Figure:
        """Day-of-week × hour revenue heatmap."""
        fig = go.Figure(go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale=[
                [0, "#F8F6F0"],
                [0.3, "#D4A843"],
                [0.6, "#C85C3B"],
                [1.0, "#1B2A4A"],
            ],
            colorbar=dict(title="Revenue ($)", tickformat="$,.0f"),
            hovertemplate=(
                "Day: %{y}<br>Hour: %{x}:00<br>"
                "Revenue: $%{z:,.0f}<extra></extra>"
            ),
        ))
        fig.update_layout(**self._base_layout(
            "Revenue Heatmap — Day of Week × Hour",
            xaxis_title="Hour of Day",
            height=420,
        ))
        self._save(fig, "sales_heatmap")
        return fig

    def category_performance(self, cat: pd.DataFrame) -> go.Figure:
        """Category performance horizontal bar chart."""
        cat = cat.sort_values("net_sales", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=cat["category"], x=cat["net_sales"],
            orientation="h",
            marker_color=COLORS["primary"],
            text=[
                f"${v:,.0f} | {m:.0%} margin"
                for v, m in zip(cat["net_sales"], cat["margin_pct"])
            ],
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig.update_layout(**self._base_layout(
            "Revenue & Margin by Category",
            xaxis_title="Net Sales ($)",
            xaxis_tickformat="$,.0f",
            showlegend=False,
            height=500,
            margin=dict(l=160, r=120, t=80, b=60),
        ))
        self._save(fig, "sales_category")
        return fig

    def avg_check_trend(self, daily: pd.DataFrame) -> go.Figure:
        """Average check size trend over the period."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily["date_only"], y=daily["avg_check"],
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=2),
            marker=dict(size=5, color=COLORS["primary"]),
            name="Avg Check",
        ))
        mean_check = daily["avg_check"].mean()
        fig.add_hline(
            y=mean_check, line_dash="dash", line_color=COLORS["secondary"],
            annotation_text=f"Period Avg: ${mean_check:.2f}",
            annotation_position="top right",
        )
        fig.update_layout(**self._base_layout(
            "Average Check Size Trend",
            yaxis_title="Average Check ($)",
            yaxis_tickformat="$,.2f",
            showlegend=False,
        ))
        self._save(fig, "sales_avg_check")
        return fig

    # ═══════════════════════════════════════════
    # MENU ENGINEERING CHARTS
    # ═══════════════════════════════════════════

    def menu_engineering_matrix(self, matrix: pd.DataFrame) -> go.Figure:
        """BCG-style scatter plot: popularity × contribution margin."""
        color_map = {
            "Star":       COLORS["positive"],
            "Plow Horse": COLORS["secondary"],
            "Puzzle":     COLORS["neutral"],
            "Dog":        COLORS["negative"],
        }
        fig = go.Figure()
        for cls, color in color_map.items():
            subset = matrix[matrix["classification"] == cls]
            fig.add_trace(go.Scatter(
                x=subset["quantity_sold"],
                y=subset["avg_margin"],
                mode="markers+text",
                marker=dict(
                    size=subset["net_sales"] / subset["net_sales"].max() * 40 + 8,
                    color=color, opacity=0.8,
                    line=dict(width=1, color="white"),
                ),
                text=subset["item_name"],
                textposition="top center",
                textfont=dict(size=8),
                name=cls,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Qty Sold: %{x}<br>"
                    "Avg Margin: $%{y:.2f}<br>"
                    f"Classification: {cls}<br>"
                    "<extra></extra>"
                ),
            ))

        pop_med = matrix["pop_median"].iloc[0]
        margin_med = matrix["margin_median"].iloc[0]
        fig.add_vline(x=pop_med, line_dash="dash", line_color=COLORS["light_gray"], line_width=1.5)
        fig.add_hline(y=margin_med, line_dash="dash", line_color=COLORS["light_gray"], line_width=1.5)

        x_range = matrix["quantity_sold"].max()
        y_range = matrix["avg_margin"].max()
        for x, y, label in [
            (x_range * 0.85, y_range * 0.95, "★ Stars"),
            (x_range * 0.15, y_range * 0.95, "? Puzzles"),
            (x_range * 0.85, y_range * 0.05, "🐴 Plow Horses"),
            (x_range * 0.15, y_range * 0.05, "🐕 Dogs"),
        ]:
            fig.add_annotation(
                x=x, y=y, text=label, showarrow=False,
                font=dict(size=13, color=COLORS["neutral"]), opacity=0.6,
            )

        fig.update_layout(**self._base_layout(
            "Menu Engineering Matrix",
            xaxis_title="Quantity Sold (Popularity)",
            yaxis_title="Avg Contribution Margin ($)",
            yaxis_tickformat="$,.2f",
            height=650,
        ))
        self._save(fig, "menu_engineering_matrix")
        return fig

    def food_cost_by_category(self, fc: pd.DataFrame) -> go.Figure:
        """Food cost % by category vs benchmark."""
        fc = fc.sort_values("food_cost_pct", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=fc["category"], x=fc["food_cost_pct"],
            orientation="h",
            marker_color=[
                COLORS["negative"] if v > settings.BENCHMARKS["food_cost_pct"] else COLORS["positive"]
                for v in fc["food_cost_pct"]
            ],
            text=[f"{v:.1%}" for v in fc["food_cost_pct"]],
            textposition="outside",
        ))
        fig.add_vline(
            x=settings.BENCHMARKS["food_cost_pct"],
            line_dash="dash", line_color=COLORS["secondary"], line_width=2,
            annotation_text=f"Target: {settings.BENCHMARKS['food_cost_pct']:.0%}",
            annotation_position="top right",
        )
        fig.update_layout(**self._base_layout(
            "Food Cost % by Category vs Target",
            xaxis_title="Food Cost %",
            xaxis_tickformat=".0%",
            showlegend=False,
            height=450,
            margin=dict(l=160, r=80, t=80, b=60),
        ))
        self._save(fig, "menu_food_cost")
        return fig

    def top_items_chart(
        self, top_items: pd.DataFrame, title_suffix: str = "Revenue",
    ) -> go.Figure:
        """Horizontal bar chart for top items."""
        df = top_items.sort_values("net_sales", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df["item_name"], x=df["net_sales"],
            orientation="h",
            marker_color=COLORS["primary"],
            text=[f"${v:,.0f}" for v in df["net_sales"]],
            textposition="outside",
        ))
        fig.update_layout(**self._base_layout(
            f"Top 10 Items by {title_suffix}",
            xaxis_title="Net Sales ($)",
            xaxis_tickformat="$,.0f",
            showlegend=False,
            height=450,
            margin=dict(l=200, r=80, t=80, b=60),
        ))
        self._save(fig, f"menu_top_{title_suffix.lower()}")
        return fig

    # ═══════════════════════════════════════════
    # PAYMENT CHARTS
    # ═══════════════════════════════════════════

    def payment_method_breakdown(self, pm: pd.DataFrame) -> go.Figure:
        """Payment method by revenue share — horizontal bar."""
        pm = pm.sort_values("net_sales", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=pm["payment_method"], x=pm["net_sales"],
            orientation="h",
            marker_color=CHART_PALETTE[: len(pm)],
            text=[
                f"${v:,.0f} ({p:.0%})"
                for v, p in zip(pm["net_sales"], pm["pct_revenue"])
            ],
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig.update_layout(**self._base_layout(
            "Revenue by Payment Method",
            xaxis_title="Net Sales ($)",
            xaxis_tickformat="$,.0f",
            showlegend=False,
            height=380,
            margin=dict(l=120, r=120, t=80, b=60),
        ))
        self._save(fig, "payment_methods")
        return fig

    # ═══════════════════════════════════════════
    # LABOR CHARTS
    # ═══════════════════════════════════════════

    def labor_vs_sales_trend(self, daily: pd.DataFrame) -> go.Figure:
        """Dual-axis: daily revenue vs labor cost with labor % line."""
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=daily["date_only"], y=daily["net_sales"],
                name="Net Sales", marker_color=COLORS["primary"], opacity=0.5,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Bar(
                x=daily["date_only"], y=daily["labor_cost"],
                name="Labor Cost", marker_color=COLORS["accent_2"], opacity=0.7,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=daily["date_only"], y=daily["labor_pct"],
                name="Labor %", line=dict(color=COLORS["secondary"], width=2.5),
                mode="lines",
            ),
            secondary_y=True,
        )
        fig.add_hline(
            y=settings.BENCHMARKS["labor_cost_pct"],
            line_dash="dot", line_color=COLORS["negative"], secondary_y=True,
            annotation_text=f"Target: {settings.BENCHMARKS['labor_cost_pct']:.0%}",
        )
        fig.update_layout(**self._base_layout(
            "Daily Revenue vs Labor Cost", barmode="group",
        ))
        fig.update_yaxes(title_text="Amount ($)", tickformat="$,.0f", secondary_y=False)
        fig.update_yaxes(title_text="Labor %", tickformat=".0%", secondary_y=True)
        self._save(fig, "labor_vs_sales")
        return fig

    def labor_by_role(self, by_role: pd.DataFrame) -> go.Figure:
        """Labor cost breakdown by job title."""
        by_role = by_role.sort_values("labor_cost", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=by_role["job_title"], x=by_role["labor_cost"],
            orientation="h",
            marker_color=CHART_PALETTE[: len(by_role)],
            text=[
                f"${v:,.0f} ({p:.0%})"
                for v, p in zip(by_role["labor_cost"], by_role["pct_of_total"])
            ],
            textposition="outside",
        ))
        fig.update_layout(**self._base_layout(
            "Labor Cost by Role",
            xaxis_title="Labor Cost ($)",
            xaxis_tickformat="$,.0f",
            showlegend=False,
            height=420,
            margin=dict(l=120, r=100, t=80, b=60),
        ))
        self._save(fig, "labor_by_role")
        return fig

    def splh_trend(self, splh: pd.DataFrame) -> go.Figure:
        """Sales Per Labor Hour trend with benchmark."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=splh["date_only"], y=splh["splh"],
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=2),
            marker=dict(size=5),
            name="SPLH",
        ))
        fig.add_hline(
            y=settings.BENCHMARKS["splh_target"],
            line_dash="dash", line_color=COLORS["secondary"],
            annotation_text=f"Target: ${settings.BENCHMARKS['splh_target']}",
            annotation_position="top right",
        )
        fig.update_layout(**self._base_layout(
            "Sales Per Labor Hour (SPLH) Trend",
            yaxis_title="SPLH ($)",
            yaxis_tickformat="$,.0f",
            showlegend=False,
        ))
        self._save(fig, "labor_splh")
        return fig

    def foh_boh_split(self, split: pd.DataFrame) -> go.Figure:
        """FOH vs BOH labor cost split."""
        fig = go.Figure()
        for _, row in split.iterrows():
            fig.add_trace(go.Bar(
                y=["Labor Split"], x=[row["labor_cost"]],
                name=f"{row['label']} ({row['pct_of_total']:.0%})",
                orientation="h",
                marker_color=COLORS["primary"] if row["label"] == "FOH" else COLORS["accent_1"],
                text=[f"${row['labor_cost']:,.0f}"],
                textposition="inside",
                textfont=dict(color="white", size=13),
            ))
        fig.update_layout(**self._base_layout(
            "FOH vs BOH Labor Cost",
            barmode="stack",
            xaxis_tickformat="$,.0f",
            height=220,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        ))
        self._save(fig, "labor_foh_boh")
        return fig

    # ═══════════════════════════════════════════
    # DELIVERY CHARTS
    # ═══════════════════════════════════════════

    def delivery_platform_compare(self, plat: pd.DataFrame) -> go.Figure:
        """Platform comparison: grouped bar chart."""
        metrics = ["gross_sales", "net_payout", "total_fees"]
        labels = ["Gross Sales", "Net Payout", "Platform Fees"]
        colors_list = [COLORS["primary"], COLORS["positive"], COLORS["negative"]]

        fig = go.Figure()
        for metric, label, color in zip(metrics, labels, colors_list):
            fig.add_trace(go.Bar(
                x=plat["platform"], y=plat[metric],
                name=label, marker_color=color,
                text=[f"${v:,.0f}" for v in plat[metric]],
                textposition="outside",
            ))
        fig.update_layout(**self._base_layout(
            "Delivery Platform Comparison",
            yaxis_title="Amount ($)",
            yaxis_tickformat="$,.0f",
            barmode="group",
            height=450,
        ))
        self._save(fig, "delivery_platform_compare")
        return fig

    def delivery_daily_trend(self, daily: pd.DataFrame) -> go.Figure:
        """Daily delivery order count and revenue."""
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=daily["date_only"], y=daily["gross_sales"],
                name="Gross Sales", marker_color=COLORS["primary"], opacity=0.6,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=daily["date_only"], y=daily["order_count"],
                name="Order Count", line=dict(color=COLORS["secondary"], width=2.5),
                mode="lines+markers", marker=dict(size=4),
            ),
            secondary_y=True,
        )
        fig.update_layout(**self._base_layout("Daily Delivery Performance"))
        fig.update_yaxes(title_text="Gross Sales ($)", tickformat="$,.0f", secondary_y=False)
        fig.update_yaxes(title_text="Orders", secondary_y=True)
        self._save(fig, "delivery_daily_trend")
        return fig

    def delivery_margin_waterfall(self, kpis: Dict[str, float]) -> go.Figure:
        """Waterfall chart showing gross → net payout flow."""
        fig = go.Figure(go.Waterfall(
            x=["Gross Sales", "Platform Fees", "Net Payout"],
            y=[kpis["gross_delivery_rev"], -kpis["total_fees"], kpis["net_payout"]],
            measure=["absolute", "relative", "total"],
            connector=dict(line=dict(color=COLORS["light_gray"])),
            decreasing=dict(marker_color=COLORS["negative"]),
            increasing=dict(marker_color=COLORS["positive"]),
            totals=dict(marker_color=COLORS["primary"]),
            text=[
                f"${kpis['gross_delivery_rev']:,.0f}",
                f"-${kpis['total_fees']:,.0f}",
                f"${kpis['net_payout']:,.0f}",
            ],
            textposition="outside",
        ))
        fig.update_layout(**self._base_layout(
            "Delivery Revenue Waterfall — Gross to Net",
            yaxis_tickformat="$,.0f",
            showlegend=False,
            height=420,
        ))
        self._save(fig, "delivery_waterfall")
        return fig

    # ═══════════════════════════════════════════
    # RESERVATION CHARTS
    # ═══════════════════════════════════════════

    def reservation_source_mix(self, src: pd.DataFrame) -> go.Figure:
        """Reservation volume by booking source."""
        src = src.sort_values("count", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=src["source"], x=src["count"],
            orientation="h",
            marker_color=CHART_PALETTE[: len(src)],
            text=[
                f"{v} ({p:.0%})"
                for v, p in zip(src["count"], src["pct_of_total"])
            ],
            textposition="outside",
        ))
        fig.update_layout(**self._base_layout(
            "Reservations by Booking Source",
            xaxis_title="Count",
            showlegend=False,
            height=380,
            margin=dict(l=100, r=80, t=80, b=60),
        ))
        self._save(fig, "res_source_mix")
        return fig

    def noshow_by_day(self, ns_day: pd.DataFrame) -> go.Figure:
        """No-show rate by day of week."""
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ns_day["day_of_week"], y=ns_day["noshow_rate"],
            marker_color=[
                COLORS["negative"] if v > settings.BENCHMARKS["noshow_rate_target"]
                else COLORS["primary"]
                for v in ns_day["noshow_rate"]
            ],
            text=[f"{v:.1%}" for v in ns_day["noshow_rate"]],
            textposition="outside",
        ))
        fig.add_hline(
            y=settings.BENCHMARKS["noshow_rate_target"],
            line_dash="dash", line_color=COLORS["secondary"],
            annotation_text=f"Target: {settings.BENCHMARKS['noshow_rate_target']:.0%}",
        )
        fig.update_layout(**self._base_layout(
            "No-Show Rate by Day of Week",
            yaxis_title="No-Show Rate",
            yaxis_tickformat=".0%",
            showlegend=False,
            height=400,
        ))
        self._save(fig, "res_noshow_dow")
        return fig

    def reservation_dow_pattern(self, dow: pd.DataFrame) -> go.Figure:
        """Reservation volume and covers by day of week."""
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=dow["day_of_week"], y=dow["reservations"],
                name="Reservations", marker_color=COLORS["primary"], opacity=0.7,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=dow["day_of_week"], y=dow["total_covers"],
                name="Covers", line=dict(color=COLORS["secondary"], width=2.5),
                mode="lines+markers",
            ),
            secondary_y=True,
        )
        fig.update_layout(**self._base_layout(
            "Reservations & Covers by Day of Week",
        ))
        fig.update_yaxes(title_text="Reservations", secondary_y=False)
        fig.update_yaxes(title_text="Total Covers", secondary_y=True)
        self._save(fig, "res_dow_pattern")
        return fig

    # ═══════════════════════════════════════════
    # OPERATIONAL FLAGS CHARTS
    # ═══════════════════════════════════════════

    def server_performance_scatter(self, server: pd.DataFrame) -> go.Figure:
        """Server performance: net sales vs tip % with discount flags."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=server["net_sales"],
            y=server["tip_pct"],
            mode="markers+text",
            marker=dict(
                size=server["txn_count"] / server["txn_count"].max() * 30 + 8,
                color=[
                    COLORS["negative"] if f else COLORS["primary"]
                    for f in server["discount_flag"]
                ],
                opacity=0.8,
                line=dict(width=1, color="white"),
            ),
            text=server["team_member"],
            textposition="top center",
            textfont=dict(size=9),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Net Sales: $%{x:,.0f}<br>"
                "Tip Rate: %{y:.1%}<br>"
                "<extra></extra>"
            ),
        ))
        fig.update_layout(**self._base_layout(
            "Server Performance — Sales vs Tip Rate",
            xaxis_title="Net Sales ($)",
            yaxis_title="Tip Rate",
            xaxis_tickformat="$,.0f",
            yaxis_tickformat=".0%",
            showlegend=False,
            height=500,
        ))
        self._save(fig, "ops_server_performance")
        return fig


# ═══════════════════════════════════════════════
# CONVENIENCE BATCH RUNNER
# ═══════════════════════════════════════════════
def generate_all_charts(
    results: Dict[str, Any],
    output_dir: Optional[str] = None,
) -> Dict[str, Path]:
    """
    Generate every chart from analysis results.

    Parameters
    ----------
    results : dict
        Dictionary with keys: sales, menu, payments, labor,
        delivery, reservations, ops_flags.
    output_dir : str | None
        Override chart output directory.

    Returns
    -------
    dict
        Mapping of chart names to file paths.
    """
    charts = FoodFactorCharts(output_dir=output_dir)
    paths: Dict[str, Path] = {}

    if "sales" in results:
        s = results["sales"]
        paths["daily_trend"] = charts.revenue_daily_trend(s["daily_trend"])
        paths["dow_revenue"] = charts.day_of_week_revenue(s["day_of_week"])
        paths["daypart"]     = charts.daypart_breakdown(s["daypart"])
        paths["order_type"]  = charts.order_type_mix(s["order_type_mix"])
        paths["heatmap"]     = charts.hourly_heatmap(s["hourly_heatmap"])
        paths["category"]    = charts.category_performance(s["category_perf"])
        paths["avg_check"]   = charts.avg_check_trend(s["avg_check_trend"])
        paths["top_items"]   = charts.top_items_chart(s["top_items"]["top_revenue"])

    if "menu" in results:
        m = results["menu"]
        paths["menu_matrix"] = charts.menu_engineering_matrix(m["matrix"])
        paths["food_cost"]   = charts.food_cost_by_category(m["food_cost_by_cat"])

    if "payments" in results:
        p = results["payments"]
        paths["payment_methods"] = charts.payment_method_breakdown(p["method_breakdown"])

    if "labor" in results:
        lb = results["labor"]
        paths["labor_vs_sales"] = charts.labor_vs_sales_trend(lb["daily_labor"])
        paths["labor_by_role"]  = charts.labor_by_role(lb["by_role"])
        paths["splh"]           = charts.splh_trend(lb["splh_trend"])
        paths["foh_boh"]        = charts.foh_boh_split(lb["foh_boh_split"])

    if "delivery" in results:
        d = results["delivery"]
        paths["delivery_compare"]   = charts.delivery_platform_compare(d["platform_compare"])
        paths["delivery_trend"]     = charts.delivery_daily_trend(d["daily_trend"])
        paths["delivery_waterfall"] = charts.delivery_margin_waterfall(d["kpis"])

    if "reservations" in results:
        r = results["reservations"]
        paths["res_source"]  = charts.reservation_source_mix(r["source_mix"])
        paths["res_noshow"]  = charts.noshow_by_day(r["noshow_analysis"]["by_day"])
        paths["res_dow"]     = charts.reservation_dow_pattern(r["dow_pattern"])

    if "ops_flags" in results:
        o = results["ops_flags"]
        paths["server_perf"] = charts.server_performance_scatter(o["server_flags"])

    logger.info("Generated %d charts", len(paths))
    return paths
