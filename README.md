# Food Factor Analytics

Enterprise-grade restaurant analytics platform by **Food Factor**. Ingests POS
export data from Square, TouchBistro, and Lightspeed, then produces
consulting-quality insights, charts, and reports.

## Quick Start

```bash
git clone https://github.com/Tushar-Pingle/food-factor-analytics.git
cd food-factor-analytics
pip install -r requirements.txt
```

### Environment Variables

| Variable              | Purpose                            |
|-----------------------|------------------------------------|
| `ANTHROPIC_API_KEY`   | Claude API for NLP / review analysis |
| `MODAL_TOKEN_ID`      | Modal.com parallel processing (optional) |
| `MODAL_TOKEN_SECRET`  | Modal.com secret (optional)        |

### Run POS Analysis

```bash
# Square
python -m pos_analysis.main --system square --data-dir ./data/client/

# TouchBistro
python -m pos_analysis.main --system touchbistro --data-dir ./data/client/

# Lightspeed
python -m pos_analysis.main --system lightspeed --data-dir ./data/client/
```

### Run Review Analysis

```bash
python -m review_analysis.main \
    --restaurant "My Restaurant" \
    --platforms google_maps opentable yelp tripadvisor
```

## Architecture

```
food-factor-analytics/
├── config/                 # Shared settings, brand colors, Plotly template
│   ├── settings.py
│   └── brand.py
├── pos_analysis/           # POS data analysis pipeline
│   ├── main.py             # CLI entry point (--system square|touchbistro|lightspeed)
│   ├── square/             # Square POS adapter
│   ├── touchbistro/        # TouchBistro POS adapter
│   ├── lightspeed/         # Lightspeed POS adapter
│   └── shared/             # POS-agnostic modules
│       ├── menu_engineering.py   # Stars / Plowhorses / Puzzles / Dogs
│       ├── cross_domain.py       # Combined POS + delivery + reservation insights
│       └── exporters.py          # JSON / CSV output formatters
├── review_analysis/        # Online review NLP pipeline
│   ├── main.py             # CLI entry point
│   ├── config.py           # Review pipeline settings
│   ├── scrapers/           # Platform scrapers (Google, OpenTable, Yelp, TripAdvisor)
│   ├── processors/         # Text cleaning, sentiment, theme extraction
│   ├── analyzers/          # Trend, category, menu item, competitive analysis
│   ├── outputs/            # JSON, CSV, chart exporters
│   └── modal_jobs/         # Modal.com parallel processing
├── data/                   # Input data (client/ is gitignored)
│   ├── dummy/
│   └── client/
├── outputs/                # Generated reports and charts (gitignored)
├── docs/                   # Documentation
└── tests/                  # Test suite
```

## POS Adapters

Each POS adapter follows the same module pattern:

| Module              | Responsibility                                      |
|---------------------|-----------------------------------------------------|
| `ingest.py`         | CSV reading, normalization, derived columns          |
| `analysis.py`       | Sales, revenue, daypart, category, payment analysis  |
| `labor.py`          | Labor cost %, SPLH, overtime, staffing optimization   |
| `visualizations.py` | Plotly charts with Food Factor brand styling          |

## Shared Modules

- **Menu Engineering** — BCG matrix classification (Star, Plow Horse, Puzzle, Dog)
- **Cross-Domain Analysis** — Synthesizes POS + delivery + reservation data
- **Exporters** — Structured JSON/CSV output with executive summaries

## Brand Standards

All charts use the Food Factor color palette defined in `config/brand.py`:

| Color       | Hex       | Usage           |
|-------------|-----------|-----------------|
| Primary     | `#1B2A4A` | Deep Navy       |
| Secondary   | `#D4A843` | Gold            |
| Accent 1    | `#6B8F71` | Sage Green      |
| Accent 2    | `#C85C3B` | Terracotta      |
| Background  | `#F8F6F0` | Warm White      |
| Text        | `#2D2D2D` | Near Black      |
| Positive    | `#2E7D32` | Success Green   |
| Negative    | `#C62828` | Alert Red       |

## License

Proprietary — Food Factor Inc.
