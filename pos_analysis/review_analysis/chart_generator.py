"""
Chart Generator — Plotly charts matching Food Factor brand standards.

Color palette, typography, and styling rules from SKILL_food-factor-report.md.

Generates:
- Sentiment trend line
- Top food items horizontal bar
- Top aspects horizontal bar
- Category radar/spider chart
- Rating distribution histogram
- Competitive comparison bar chart
"""

import os
from typing import Dict, Any, List, Optional

from ..config import BRAND_COLORS, BRAND_COLOR_SEQUENCE


def _get_plotly():
    """Lazy import plotly."""
    import plotly.graph_objects as go
    import plotly.io as pio
    return go, pio


def _base_layout(title: str) -> dict:
    """Base Plotly layout matching Food Factor brand."""
    return dict(
        title=dict(
            text=title,
            font=dict(family="Inter, Montserrat, sans-serif", size=18, color=BRAND_COLORS["primary"]),
            x=0.02,
        ),
        font=dict(family="Inter, Open Sans, sans-serif", size=12, color=BRAND_COLORS["text"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BRAND_COLORS["background"],
        margin=dict(l=60, r=30, t=60, b=50),
        xaxis=dict(
            gridcolor=BRAND_COLORS["light_gray"],
            linecolor=BRAND_COLORS["light_gray"],
            zerolinecolor=BRAND_COLORS["light_gray"],
        ),
        yaxis=dict(
            gridcolor=BRAND_COLORS["light_gray"],
            linecolor=BRAND_COLORS["light_gray"],
            zerolinecolor=BRAND_COLORS["light_gray"],
        ),
    )


def generate_all_charts(
    food_items: List[Dict],
    drinks: List[Dict],
    aspects: List[Dict],
    trend_data: List[Dict],
    restaurant_name: str,
    output_dir: str = "output",
    category_analysis: Optional[List[Dict]] = None,
    competitive_analysis: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Generate all standard charts and save as PNG + HTML.

    Returns: list of file paths created.
    """
    go, pio = _get_plotly()
    os.makedirs(output_dir, exist_ok=True)
    safe_name = restaurant_name.lower().replace(" ", "_").replace("'", "")
    paths = []

    # 1. Sentiment trend line
    if trend_data:
        path = _chart_sentiment_trend(go, pio, trend_data, restaurant_name, safe_name, output_dir)
        if path:
            paths.append(path)

    # 2. Top food items bar
    if food_items:
        path = _chart_horizontal_bar(
            go, pio, food_items[:15], "Top Food Items by Mention Count",
            f"{safe_name}_top_food", output_dir,
        )
        if path:
            paths.append(path)

    # 3. Top drinks bar
    if drinks:
        path = _chart_horizontal_bar(
            go, pio, drinks[:15], "Top Drinks by Mention Count",
            f"{safe_name}_top_drinks", output_dir,
        )
        if path:
            paths.append(path)

    # 4. Aspects sentiment bar
    if aspects:
        path = _chart_aspects_sentiment(go, pio, aspects[:15], restaurant_name, safe_name, output_dir)
        if path:
            paths.append(path)

    # 5. Rating distribution
    if trend_data:
        path = _chart_rating_distribution(go, pio, trend_data, restaurant_name, safe_name, output_dir)
        if path:
            paths.append(path)

    # 6. Category radar
    if category_analysis:
        path = _chart_category_radar(go, pio, category_analysis, restaurant_name, safe_name, output_dir)
        if path:
            paths.append(path)

    print(f"📊 Generated {len(paths)} charts in {output_dir}/")
    return paths


def _save_chart(fig, pio, name: str, output_dir: str) -> str:
    """Save chart as HTML (and PNG if kaleido available)."""
    html_path = os.path.join(output_dir, f"{name}.html")
    fig.write_html(html_path)

    try:
        png_path = os.path.join(output_dir, f"{name}.png")
        fig.write_image(png_path, width=900, height=500, scale=2)
        print(f"📊 Chart: {name}.png")
        return png_path
    except Exception:
        print(f"📊 Chart: {name}.html (install kaleido for PNG export)")
        return html_path


def _chart_sentiment_trend(go, pio, trend_data, restaurant_name, safe_name, output_dir):
    """Sentiment trend over time."""
    # Filter data with dates
    dated = [t for t in trend_data if t.get("date")]
    if not dated:
        return None

    dates = [t["date"] for t in dated]
    sentiments = [t["sentiment"] for t in dated]
    ratings = [t["rating"] for t in dated]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=sentiments, mode="markers+lines",
        name="Sentiment", marker=dict(color=BRAND_COLORS["primary"], size=5),
        line=dict(color=BRAND_COLORS["primary"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=ratings, mode="markers",
        name="Rating (0-5)", yaxis="y2",
        marker=dict(color=BRAND_COLORS["secondary"], size=6, symbol="diamond"),
    ))

    layout = _base_layout(f"Review Sentiment & Rating Trend — {restaurant_name}")
    layout["yaxis"]["title"] = "Sentiment (-1 to +1)"
    layout["yaxis2"] = dict(
        title="Rating (0-5)", overlaying="y", side="right",
        gridcolor=BRAND_COLORS["light_gray"],
    )
    layout["legend"] = dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)")
    fig.update_layout(**layout)

    return _save_chart(fig, pio, f"{safe_name}_sentiment_trend", output_dir)


def _chart_horizontal_bar(go, pio, items, title, name, output_dir):
    """Horizontal bar chart for top items."""
    items_sorted = sorted(items, key=lambda x: x.get("mention_count", 0))
    names = [i.get("name", "?").title() for i in items_sorted]
    counts = [i.get("mention_count", 0) for i in items_sorted]
    sentiments = [i.get("sentiment", 0) for i in items_sorted]

    # Color bars by sentiment
    colors = [
        BRAND_COLORS["positive"] if s >= 0.6
        else BRAND_COLORS["negative"] if s < 0
        else BRAND_COLORS["neutral"]
        for s in sentiments
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=counts, y=names, orientation="h",
        marker=dict(color=colors),
        text=[f"{c} mentions" for c in counts],
        textposition="outside",
    ))

    layout = _base_layout(title)
    layout["xaxis"]["title"] = "Mention Count"
    layout["height"] = max(400, len(items) * 30 + 100)
    fig.update_layout(**layout)

    return _save_chart(fig, pio, name, output_dir)


def _chart_aspects_sentiment(go, pio, aspects, restaurant_name, safe_name, output_dir):
    """Horizontal bar chart of aspects colored by sentiment."""
    aspects_sorted = sorted(aspects, key=lambda x: x.get("sentiment", 0))
    names = [a.get("name", "?").title() for a in aspects_sorted]
    sentiments = [a.get("sentiment", 0) for a in aspects_sorted]

    colors = [
        BRAND_COLORS["positive"] if s >= 0.6
        else BRAND_COLORS["negative"] if s < 0
        else BRAND_COLORS["neutral"]
        for s in sentiments
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sentiments, y=names, orientation="h",
        marker=dict(color=colors),
        text=[f"{s:+.2f}" for s in sentiments],
        textposition="outside",
    ))

    layout = _base_layout(f"Aspect Sentiment Analysis — {restaurant_name}")
    layout["xaxis"]["title"] = "Average Sentiment"
    layout["xaxis"]["range"] = [-1, 1]
    layout["height"] = max(400, len(aspects) * 30 + 100)
    fig.update_layout(**layout)

    return _save_chart(fig, pio, f"{safe_name}_aspects_sentiment", output_dir)


def _chart_rating_distribution(go, pio, trend_data, restaurant_name, safe_name, output_dir):
    """Rating distribution histogram."""
    ratings = [t["rating"] for t in trend_data if t["rating"] > 0]
    if not ratings:
        return None

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=ratings, nbinsx=10,
        marker=dict(color=BRAND_COLORS["primary"], line=dict(color=BRAND_COLORS["background"], width=1)),
    ))

    layout = _base_layout(f"Rating Distribution — {restaurant_name}")
    layout["xaxis"]["title"] = "Rating"
    layout["yaxis"]["title"] = "Count"
    fig.update_layout(**layout)

    return _save_chart(fig, pio, f"{safe_name}_rating_dist", output_dir)


def _chart_category_radar(go, pio, category_analysis, restaurant_name, safe_name, output_dir):
    """Radar/spider chart of category performance."""
    if not category_analysis:
        return None

    cats = sorted(category_analysis, key=lambda x: x.get("mention_count", 0), reverse=True)[:10]
    names = [c["name"].title() for c in cats]
    sentiments = [max(-1, min(1, c.get("avg_sentiment", 0))) for c in cats]
    # Normalize to 0-1 range for radar
    normalized = [(s + 1) / 2 for s in sentiments]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=normalized + [normalized[0]],  # Close the polygon
        theta=names + [names[0]],
        fill="toself",
        fillcolor=f"rgba(27, 42, 74, 0.15)",
        line=dict(color=BRAND_COLORS["primary"], width=2),
        marker=dict(size=6),
    ))

    layout = _base_layout(f"Category Performance — {restaurant_name}")
    layout["polar"] = dict(
        radialaxis=dict(visible=True, range=[0, 1], gridcolor=BRAND_COLORS["light_gray"]),
        angularaxis=dict(gridcolor=BRAND_COLORS["light_gray"]),
        bgcolor=BRAND_COLORS["background"],
    )
    fig.update_layout(**layout)

    return _save_chart(fig, pio, f"{safe_name}_category_radar", output_dir)
