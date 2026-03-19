"""
Food Factor Analytics — Brand Colors & Plotly Chart Template

Defines the Food Factor visual identity and provides a reusable Plotly
layout template so every chart across all POS adapters shares a
consistent, consulting-grade look.
"""

from typing import Dict, List

# ── Brand Color Palette ──────────────────────────────────────────────────
COLORS: Dict[str, str] = {
    "primary": "#1B2A4A",       # Deep Navy
    "secondary": "#D4A843",     # Gold
    "accent1": "#6B8F71",       # Sage Green
    "accent_1": "#6B8F71",      # Sage Green (snake_case alias)
    "accent2": "#C85C3B",       # Terracotta
    "accent_2": "#C85C3B",      # Terracotta (snake_case alias)
    "background": "#F8F6F0",    # Warm White
    "text": "#2D2D2D",          # Near Black
    "positive": "#2E7D32",      # Success Green
    "negative": "#C62828",      # Alert Red
    "light_gray": "#E0DDD5",    # Light Grid/Border
    "neutral": "#999999",       # Neutral Gray
}

# Extended palette for multi-series charts
CHART_SERIES_COLORS: List[str] = [
    "#1B2A4A", "#D4A843", "#6B8F71", "#C85C3B",
    "#5B7FA5", "#8B6914", "#4A6B50", "#E88B6E",
    "#2D4A7A", "#B8922F", "#7DAF83", "#A44828",
]

# ── Typography ───────────────────────────────────────────────────────────
FONT_FAMILY: str = "Inter, Segoe UI, Helvetica Neue, Arial, sans-serif"
TITLE_FONT_SIZE: int = 18
AXIS_FONT_SIZE: int = 12
TICK_FONT_SIZE: int = 10

# ── Chart Dimensions ────────────────────────────────────────────────────
DEFAULT_WIDTH: int = 1000
DEFAULT_HEIGHT: int = 550
HEATMAP_HEIGHT: int = 450
SMALL_CHART_HEIGHT: int = 400

# ── Plotly Layout Template ───────────────────────────────────────────────
PLOTLY_TEMPLATE: dict = {
    "layout": {
        "font": {
            "family": FONT_FAMILY,
            "color": COLORS["text"],
            "size": AXIS_FONT_SIZE,
        },
        "title": {
            "font": {
                "family": FONT_FAMILY,
                "size": TITLE_FONT_SIZE,
                "color": COLORS["primary"],
            },
            "x": 0.5,
            "xanchor": "center",
        },
        "paper_bgcolor": COLORS["background"],
        "plot_bgcolor": COLORS["background"],
        "colorway": CHART_SERIES_COLORS,
        "xaxis": {
            "gridcolor": "#E0DDD5",
            "linecolor": "#C0BDB5",
            "tickfont": {"size": TICK_FONT_SIZE},
        },
        "yaxis": {
            "gridcolor": "#E0DDD5",
            "linecolor": "#C0BDB5",
            "tickfont": {"size": TICK_FONT_SIZE},
        },
        "legend": {
            "bgcolor": "rgba(248, 246, 240, 0.8)",
            "bordercolor": "#E0DDD5",
            "borderwidth": 1,
        },
        "margin": {"l": 60, "r": 30, "t": 60, "b": 60},
    }
}


def get_plotly_template() -> dict:
    """Return a deep copy of the Plotly template for safe mutation."""
    import copy
    return copy.deepcopy(PLOTLY_TEMPLATE)
