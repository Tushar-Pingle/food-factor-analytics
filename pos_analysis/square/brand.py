"""
config/brand.py — Food Factor Brand Standards
===============================================
Color palette, chart styling defaults, and typography rules.
Every client-facing visualization reads from here so the brand
is consistent across all reports and decks.
"""

from typing import Dict, List

# ─────────────────────────────────────────────
# BRAND COLORS — Food Factor palette
# ─────────────────────────────────────────────
COLORS: Dict[str, str] = {
    "primary":    "#1B2A4A",   # Deep Navy
    "secondary":  "#D4A843",   # Warm Gold
    "accent_1":   "#6B8F71",   # Sage Green
    "accent_2":   "#C85C3B",   # Terracotta
    "background": "#F8F6F0",   # Off-White
    "text":       "#2D2D2D",   # Charcoal
    "light_gray": "#E0DDD5",   # Borders / dividers
    "positive":   "#2E7D32",   # Forest Green
    "negative":   "#C62828",   # Deep Red
    "neutral":    "#546E7A",   # Steel Blue
}

# Extended palette for multi-series charts (12 distinct colors)
CHART_PALETTE: List[str] = [
    "#1B2A4A", "#D4A843", "#6B8F71", "#C85C3B",
    "#546E7A", "#8B6914", "#3D5A80", "#E07A5F",
    "#81B29A", "#F2CC8F", "#3C1642", "#A23B72",
]

# ─────────────────────────────────────────────
# CHART STYLING DEFAULTS
# ─────────────────────────────────────────────
CHART_CONFIG: Dict = {
    "font_family":     "Inter, Open Sans, Helvetica, Arial, sans-serif",
    "title_font_size": 18,
    "axis_font_size":  12,
    "tick_font_size":  11,
    "legend_font_size": 11,
    "width":           1000,
    "height":          550,
    "margin":          dict(l=70, r=40, t=80, b=60),
    "export_scale":    3,       # 3× for crisp PDF embedding
    "export_format":   "png",
}
