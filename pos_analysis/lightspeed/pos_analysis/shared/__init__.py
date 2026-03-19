"""
pos_analysis.shared — Food Factor Shared Configuration & Utilities

Brand standards, industry benchmarks, chart export settings, daypart
definitions, and the Plotly template used across all POS system modules.

Imported by:
    pos_analysis.lightspeed.*
    pos_analysis.square.*
    pos_analysis.touchbistro.*
    pos_analysis.shared.menu_engineering
    pos_analysis.shared.cross_domain
    pos_analysis.shared.exporters
"""

from typing import Dict, Any

# ─────────────────────────────────────────────
# FOOD FACTOR BRAND STANDARDS
# ─────────────────────────────────────────────

COLORS: Dict[str, str] = {
    "primary":      "#1B2A4A",   # Deep Navy
    "secondary":    "#D4A843",   # Warm Gold
    "accent_1":     "#6B8F71",   # Sage Green
    "accent_2":     "#C85C3B",   # Terracotta
    "background":   "#F8F6F0",   # Off-White
    "text":         "#2D2D2D",   # Charcoal
    "light_gray":   "#E0DDD5",   # Borders / Dividers
    "positive":     "#2E7D32",   # Forest Green
    "negative":     "#C62828",   # Deep Red
    "neutral":      "#546E7A",   # Steel Blue
}

CHART_PALETTE = [
    COLORS["primary"],
    COLORS["secondary"],
    COLORS["accent_1"],
    COLORS["accent_2"],
    COLORS["neutral"],
    "#8E6C88",   # Muted plum (extended)
    "#3E7CB1",   # Dusty blue (extended)
    "#D98E63",   # Warm sienna (extended)
]

FONT_FAMILY: str = "Inter, Montserrat, Raleway, Arial, sans-serif"
CHART_FONT_SIZE: int = 12
TITLE_FONT_SIZE: int = 16
ANNOTATION_FONT_SIZE: int = 10


# ─────────────────────────────────────────────
# INDUSTRY BENCHMARKS (Upscale Casual — Vancouver)
# ─────────────────────────────────────────────

BENCHMARKS: Dict[str, float] = {
    "food_cost_pct":        0.30,    # Target food cost %
    "food_cost_pct_max":    0.35,    # Alarm threshold
    "bev_cost_pct":         0.22,    # Beverage cost target
    "labor_pct":            0.28,    # Target labor % of net sales
    "labor_pct_max":        0.32,    # Alarm threshold
    "prime_cost_pct":       0.60,    # Food + labor combined target
    "void_rate_max":        0.02,    # 2% void rate alarm
    "no_show_rate_max":     0.08,    # 8% no-show alarm
    "avg_tip_pct":          0.18,    # Expected tip rate
    "revpash_target":       12.00,   # Revenue per available seat hour
    "splh_target":          55.00,   # Sales per labor hour
    "delivery_net_margin":  0.15,    # Minimum delivery margin after commissions
}


# ─────────────────────────────────────────────
# DAYPART DEFINITIONS (24h format boundaries)
# ─────────────────────────────────────────────

DAYPARTS: Dict[str, tuple] = {
    "Brunch":     (10, 14),   # 10:00 – 13:59 (Sunday only)
    "Lunch":      (11, 15),   # 11:00 – 14:59
    "Afternoon":  (15, 17),   # 15:00 – 16:59
    "Dinner":     (17, 22),   # 17:00 – 21:59
    "Late Night": (22, 24),   # 22:00+
}


# ─────────────────────────────────────────────
# MENU ENGINEERING THRESHOLDS
# ─────────────────────────────────────────────

MENU_ENGINEERING: Dict[str, str] = {
    "popularity_method":  "median",  # "median" or "mean" for popularity cutoff
    "margin_method":      "median",  # "median" or "mean" for margin cutoff
}


# ─────────────────────────────────────────────
# CHART EXPORT SETTINGS
# ─────────────────────────────────────────────

CHART_WIDTH: int = 1000
CHART_HEIGHT: int = 600
CHART_SCALE: int = 2       # Retina export (2x resolution)
CHART_FORMAT: str = "png"  # "png", "svg", or "pdf"


# ─────────────────────────────────────────────
# PLOTLY TEMPLATE (applied globally)
# ─────────────────────────────────────────────

def get_plotly_template():
    """Return a custom Plotly template matching Food Factor brand standards."""
    import plotly.graph_objects as go

    template = go.layout.Template()

    template.layout = go.Layout(
        font=dict(family=FONT_FAMILY, size=CHART_FONT_SIZE, color=COLORS["text"]),
        title=dict(
            font=dict(size=TITLE_FONT_SIZE, color=COLORS["primary"]),
            x=0.0, xanchor="left",
        ),
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        colorway=CHART_PALETTE,
        xaxis=dict(
            gridcolor=COLORS["light_gray"],
            linecolor=COLORS["light_gray"],
            zerolinecolor=COLORS["light_gray"],
            title_font=dict(size=CHART_FONT_SIZE),
        ),
        yaxis=dict(
            gridcolor=COLORS["light_gray"],
            linecolor=COLORS["light_gray"],
            zerolinecolor=COLORS["light_gray"],
            title_font=dict(size=CHART_FONT_SIZE),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=ANNOTATION_FONT_SIZE),
        ),
        margin=dict(l=60, r=30, t=60, b=50),
    )

    return template
