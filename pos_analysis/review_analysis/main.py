#!/usr/bin/env python3
"""
Food Factor Review Pipeline — CLI Orchestrator

Usage:
    # Full analysis with competitors
    python main.py --restaurant "Coastal Table" --location "Vancouver" \
        --platforms google,opentable --max-reviews 500 \
        --competitors "Nightingale,Hawksworth,Boulevard"

    # Quick single-platform run
    python main.py --restaurant "Miku" --google-url "https://www.google.com/maps/place/Miku+Vancouver" \
        --platforms google --max-reviews 100

    # Local mode (no Modal — slower, sequential)
    python main.py --restaurant "Test Restaurant" --platforms google \
        --google-url "https://..." --max-reviews 50 --local

Execution flow:
    1. Parse CLI args
    2. Scrape reviews (parallel via Modal or local)
    3. Clean & deduplicate
    4. Batch NLP extraction (parallel via Modal or local)
    5. Merge batches
    6. Category analysis + menu item analysis
    7. Chef + manager insights (parallel via Modal or local)
    8. Summary generation
    9. Competitor pipeline (if specified)
    10. Competitive comparison
    11. Trend data
    12. Export: JSON, CSV, Charts
"""

import argparse
import os
import sys
import time
import json
from typing import Dict, Any, List, Optional

import pandas as pd

from .config import (
    PipelineConfig,
    BATCH_SIZE,
    SUMMARY_FOOD_COUNT,
    SUMMARY_DRINKS_COUNT,
    SUMMARY_ASPECTS_COUNT,
    get_api_key,
)
from .processors.cleaner import clean_reviews_for_ai
from .processors.sentiment import parse_rating, calculate_sentiment
from .processors.theme_extractor import (
    process_batch,
    merge_batch_results,
    generate_summaries,
    apply_summaries,
)
from .analyzers.trend_analyzer import build_trend_data, compute_trend_stats
from .analyzers.insights_generator import generate_insights
from .analyzers.category_analyzer import analyze_categories
from .analyzers.menu_item_analyzer import analyze_menu_items
from .analyzers.competitive_analyzer import build_comparison
from .outputs.json_exporter import export_full_report_json, export_prompt17_json
from .outputs.csv_exporter import export_all_csvs
from .outputs.chart_generator import generate_all_charts


# ============================================================================
# LOCAL SCRAPING (no Modal)
# ============================================================================

def scrape_local(platform: str, url: str, max_reviews: int, headless: bool = True) -> Dict[str, Any]:
    """Run a scraper locally (no Modal)."""
    print(f"🕷️ [{platform.upper()}] Scraping locally: {url[:80]}...")

    if platform == "opentable":
        from .scrapers.opentable_scraper import scrape_opentable
        return scrape_opentable(url, max_reviews=max_reviews, headless=headless)
    elif platform in ("google", "google_maps"):
        from .scrapers.google_maps_scraper import scrape_google_maps
        return scrape_google_maps(url, max_reviews=max_reviews, headless=headless)
    elif platform == "yelp":
        from .scrapers.yelp_scraper import scrape_yelp
        return scrape_yelp(url, max_reviews=max_reviews, headless=headless)
    elif platform == "tripadvisor":
        from .scrapers.tripadvisor_scraper import scrape_tripadvisor
        return scrape_tripadvisor(url, max_reviews=max_reviews, headless=headless)
    else:
        return {"success": False, "error": f"Unknown platform: {platform}", "reviews": {}}


# ============================================================================
# UNIFY SCRAPER RESULTS INTO A SINGLE DATAFRAME
# ============================================================================

def unify_scraper_results(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Merge scraper results from multiple platforms into one DataFrame.
    Handles the NESTED format from all scrapers.
    """
    frames = []

    for result in results:
        if not result.get("success"):
            continue

        reviews_data = result.get("reviews", {})
        if not isinstance(reviews_data, dict) or "review_texts" not in reviews_data:
            continue

        review_texts = reviews_data.get("review_texts", [])
        n = len(review_texts)
        if n == 0:
            continue

        source = result.get("metadata", {}).get("source", "unknown")

        df = pd.DataFrame({
            "name": (reviews_data.get("names", []) + [""] * n)[:n],
            "date": (reviews_data.get("dates", []) + [""] * n)[:n],
            "overall_rating": (reviews_data.get("overall_ratings", []) + [0.0] * n)[:n],
            "food_rating": reviews_data.get("food_ratings", [0.0] * n)[:n],
            "service_rating": reviews_data.get("service_ratings", [0.0] * n)[:n],
            "ambience_rating": reviews_data.get("ambience_ratings", [0.0] * n)[:n],
            "review_text": review_texts,
            "source": [source] * n,
        })

        # Parse ratings to numeric
        for col in ["overall_rating", "food_rating", "service_rating", "ambience_rating"]:
            df[col] = df[col].apply(parse_rating)

        frames.append(df)
        print(f"📦 [{source}] {len(df)} reviews loaded")

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    print(f"📊 Total unified reviews: {len(combined)}")
    return combined


# ============================================================================
# CORE PIPELINE (runs for one restaurant)
# ============================================================================

def run_pipeline(
    restaurant_name: str,
    platform_urls: Dict[str, str],
    max_reviews: int = 500,
    output_dir: str = "output",
    use_modal: bool = True,
    headless: bool = True,
    run_category: bool = True,
    run_menu_items: bool = True,
) -> Dict[str, Any]:
    """
    Run the full analysis pipeline for one restaurant.

    Args:
        restaurant_name: Display name
        platform_urls: {"google": "url", "opentable": "url", ...}
        max_reviews: Max reviews per platform
        output_dir: Output directory
        use_modal: Use Modal for parallelism (False = local sequential)
        headless: Run browsers headless
        run_category: Run category analysis
        run_menu_items: Run menu item analysis

    Returns:
        Full result dict
    """
    start_time = time.time()
    api_key = get_api_key()

    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set! Set it in your environment.")
        print("   export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🍽️  FOOD FACTOR REVIEW PIPELINE — {restaurant_name}")
    print(f"{'='*70}")
    print(f"📋 Platforms: {', '.join(platform_urls.keys())}")
    print(f"📊 Max reviews per platform: {max_reviews}")
    print(f"⚙️  Mode: {'Modal (parallel)' if use_modal else 'Local (sequential)'}")
    print(f"{'='*70}\n")

    # ------------------------------------------------------------------
    # Phase 1: Scrape
    # ------------------------------------------------------------------
    print("=" * 50)
    print("📥 PHASE 1: Scraping Reviews")
    print("=" * 50)
    scrape_start = time.time()

    scrape_results = []
    if use_modal:
        try:
            from .modal_jobs.scrape_job import scrape_platform
            futures = []
            for platform, url in platform_urls.items():
                futures.append(scrape_platform.spawn(platform, url, max_reviews))
            for future in futures:
                scrape_results.append(future.get())
        except Exception as e:
            print(f"⚠️ Modal scraping failed ({e}), falling back to local...")
            for platform, url in platform_urls.items():
                scrape_results.append(scrape_local(platform, url, max_reviews, headless))
    else:
        for platform, url in platform_urls.items():
            scrape_results.append(scrape_local(platform, url, max_reviews, headless))

    print(f"✅ Scraping done in {time.time() - scrape_start:.1f}s")

    # Unify into DataFrame
    df = unify_scraper_results(scrape_results)
    if df.empty:
        return {"success": False, "error": "No reviews scraped from any platform"}

    # ------------------------------------------------------------------
    # Phase 2: Clean & Deduplicate
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("🧹 PHASE 2: Cleaning & Deduplication")
    print("=" * 50)

    reviews = clean_reviews_for_ai(df["review_text"].dropna().tolist(), verbose=True)
    print(f"📊 Clean reviews ready for NLP: {len(reviews)}")

    if not reviews:
        return {"success": False, "error": "No valid reviews after cleaning"}

    # ------------------------------------------------------------------
    # Phase 3: Batch NLP Extraction
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("🔄 PHASE 3: Batch NLP Extraction")
    print("=" * 50)
    extract_start = time.time()

    batches = []
    batch_num = 1
    for i in range(0, len(reviews), BATCH_SIZE):
        batch_reviews = reviews[i : i + BATCH_SIZE]
        batches.append({
            "reviews": batch_reviews,
            "restaurant_name": restaurant_name,
            "batch_index": batch_num,
            "start_index": i,
        })
        batch_num += 1

    print(f"📦 Created {len(batches)} batches of {BATCH_SIZE} reviews")

    batch_results = []
    if use_modal:
        try:
            from .modal_jobs.nlp_job import process_batch_odd, process_batch_even
            odd_batches = [b for b in batches if b["batch_index"] % 2 == 1]
            even_batches = [b for b in batches if b["batch_index"] % 2 == 0]

            print(f"🚀 Processing {len(odd_batches)} odd + {len(even_batches)} even batches in parallel...")
            odd_results = list(process_batch_odd.map(odd_batches)) if odd_batches else []
            even_results = list(process_batch_even.map(even_batches)) if even_batches else []
            batch_results = odd_results + even_results
        except Exception as e:
            print(f"⚠️ Modal NLP failed ({e}), falling back to local...")
            batch_results = _run_batches_local(batches, api_key)
    else:
        batch_results = _run_batches_local(batches, api_key)

    print(f"✅ Extraction done in {time.time() - extract_start:.1f}s")

    # Merge batch results
    merged = merge_batch_results(batch_results)
    food_items = merged["food_items"]
    drinks = merged["drinks"]
    aspects = merged["aspects"]

    # ------------------------------------------------------------------
    # Phase 4: Summaries
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("📝 PHASE 4: Summary Generation")
    print("=" * 50)

    if use_modal:
        try:
            from .modal_jobs.insights_job import generate_summaries_modal
            summaries = generate_summaries_modal.remote(
                food_items[:SUMMARY_FOOD_COUNT],
                drinks[:SUMMARY_DRINKS_COUNT],
                aspects[:SUMMARY_ASPECTS_COUNT],
                restaurant_name,
            )
        except Exception:
            summaries = generate_summaries(
                food_items, drinks, aspects, restaurant_name, api_key
            )
    else:
        summaries = generate_summaries(
            food_items, drinks, aspects, restaurant_name, api_key
        )

    apply_summaries(food_items, drinks, aspects, summaries)

    # ------------------------------------------------------------------
    # Phase 5: Insights (Chef + Manager in parallel)
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("🧠 PHASE 5: Chef & Manager Insights")
    print("=" * 50)
    insights_start = time.time()

    analysis_data = {
        "menu_analysis": {"food_items": food_items, "drinks": drinks},
        "aspect_analysis": {"aspects": aspects},
    }

    if use_modal:
        try:
            from .modal_jobs.insights_job import generate_chef_insights_modal, generate_manager_insights_modal
            chef_future = generate_chef_insights_modal.spawn(analysis_data, restaurant_name)
            manager_future = generate_manager_insights_modal.spawn(analysis_data, restaurant_name)
            chef_result = chef_future.get()
            manager_result = manager_future.get()
        except Exception:
            chef_result = generate_insights(analysis_data, restaurant_name, "chef", api_key)
            manager_result = generate_insights(analysis_data, restaurant_name, "manager", api_key)
    else:
        chef_result = generate_insights(analysis_data, restaurant_name, "chef", api_key)
        manager_result = generate_insights(analysis_data, restaurant_name, "manager", api_key)

    insights = {
        "chef": chef_result.get("insights", {}),
        "manager": manager_result.get("insights", {}),
    }
    print(f"✅ Insights done in {time.time() - insights_start:.1f}s")

    # ------------------------------------------------------------------
    # Phase 6: Category Analysis (NEW)
    # ------------------------------------------------------------------
    category_analysis = []
    if run_category:
        print("\n" + "=" * 50)
        print("📊 PHASE 6: Category Analysis")
        print("=" * 50)
        category_analysis = analyze_categories(reviews, restaurant_name, api_key)

    # ------------------------------------------------------------------
    # Phase 7: Menu Item Analysis (NEW)
    # ------------------------------------------------------------------
    menu_item_analysis = {}
    if run_menu_items:
        print("\n" + "=" * 50)
        print("🍽️  PHASE 7: Menu Item Analysis")
        print("=" * 50)
        menu_item_analysis = analyze_menu_items(food_items, drinks, restaurant_name, api_key)

    # ------------------------------------------------------------------
    # Phase 8: Trend Data
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("📈 PHASE 8: Trend Data")
    print("=" * 50)

    trend_result = build_trend_data(df)
    trend_data = trend_result["trend_data"]
    trend_stats = compute_trend_stats(trend_data)

    print(f"📊 Trend stats: avg rating {trend_stats['avg_rating']}, "
          f"avg sentiment {trend_stats['avg_sentiment']}, "
          f"{trend_stats['positive_pct']}% positive")

    # ------------------------------------------------------------------
    # Build final result
    # ------------------------------------------------------------------
    total_time = time.time() - start_time

    result = {
        "success": True,
        "restaurant_name": restaurant_name,
        "menu_analysis": {"food_items": food_items, "drinks": drinks},
        "aspect_analysis": {"aspects": aspects},
        "insights": insights,
        "trend_data": trend_data,
        "trend_stats": trend_stats,
        "category_analysis": category_analysis,
        "menu_item_analysis": menu_item_analysis,
        "stats": {
            "total_reviews": len(reviews),
            "food_items": len(food_items),
            "drinks": len(drinks),
            "aspects": len(aspects),
            "processing_time_seconds": round(total_time, 1),
            "estimated_ratings": trend_result["estimated_rating_count"],
        },
    }

    print(f"\n🎉 Pipeline complete in {total_time:.1f}s ({total_time/60:.1f} min)")
    return result


def _run_batches_local(batches: list, api_key: str) -> list:
    """Run NLP batches locally (sequential)."""
    results = []
    for batch_data in batches:
        result = process_batch(
            reviews=batch_data["reviews"],
            restaurant_name=batch_data["restaurant_name"],
            batch_index=batch_data["batch_index"],
            start_index=batch_data["start_index"],
            api_key=api_key,
        )
        results.append(result)
    return results


# ============================================================================
# EXPORT PHASE
# ============================================================================

def export_results(
    result: Dict[str, Any],
    output_dir: str = "output",
    competitive_analysis: Optional[Dict] = None,
):
    """Export all outputs: JSON, CSV, Charts."""
    print("\n" + "=" * 50)
    print("💾 EXPORTING RESULTS")
    print("=" * 50)

    restaurant_name = result["restaurant_name"]
    food_items = result["menu_analysis"]["food_items"]
    drinks_list = result["menu_analysis"]["drinks"]
    aspects = result["aspect_analysis"]["aspects"]
    trend_data = result["trend_data"]

    # JSON
    json_path = export_full_report_json(
        restaurant_name=restaurant_name,
        platform="multi",
        menu_analysis=result["menu_analysis"],
        aspect_analysis=result["aspect_analysis"],
        insights=result["insights"],
        trend_data=trend_data,
        trend_stats=result["trend_stats"],
        category_analysis=result.get("category_analysis"),
        menu_item_analysis=result.get("menu_item_analysis"),
        competitive_analysis=competitive_analysis,
        stats=result["stats"],
        output_dir=output_dir,
    )

    # Prompt 17 JSON
    export_prompt17_json(json_path, output_dir=output_dir)

    # CSVs
    export_all_csvs(
        restaurant_name=restaurant_name,
        food_items=food_items,
        drinks=drinks_list,
        aspects=aspects,
        trend_data=trend_data,
        category_analysis=result.get("category_analysis"),
        menu_item_analysis=result.get("menu_item_analysis"),
        output_dir=output_dir,
    )

    # Charts
    try:
        generate_all_charts(
            food_items=food_items,
            drinks=drinks_list,
            aspects=aspects,
            trend_data=trend_data,
            restaurant_name=restaurant_name,
            output_dir=output_dir,
            category_analysis=result.get("category_analysis"),
            competitive_analysis=competitive_analysis,
        )
    except ImportError:
        print("⚠️ Plotly not installed — skipping charts. pip install plotly kaleido")

    print(f"\n✅ All outputs saved to {output_dir}/")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Food Factor Review Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --restaurant "Coastal Table" --platforms google,opentable \\
      --google-url "https://..." --opentable-url "https://..." --max-reviews 500

  python main.py --restaurant "Miku" --platforms google --max-reviews 100 \\
      --google-url "https://..." --competitors "Minami,Tojo" --local
        """,
    )

    parser.add_argument("--restaurant", required=True, help="Restaurant name")
    parser.add_argument("--location", default="Vancouver", help="City/location (default: Vancouver)")
    parser.add_argument("--platforms", default="google", help="Comma-separated: google,opentable,yelp,tripadvisor")
    parser.add_argument("--max-reviews", type=int, default=500, help="Max reviews per platform (default: 500)")
    parser.add_argument("--competitors", default="", help="Comma-separated competitor names")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--local", action="store_true", help="Run locally without Modal")
    parser.add_argument("--no-headless", action="store_true", help="Show browser windows")

    # Direct URLs (optional — skip search)
    parser.add_argument("--google-url", default="", help="Google Maps URL")
    parser.add_argument("--opentable-url", default="", help="OpenTable URL")
    parser.add_argument("--yelp-url", default="", help="Yelp URL")
    parser.add_argument("--tripadvisor-url", default="", help="TripAdvisor URL")

    # Skip analysis phases
    parser.add_argument("--skip-category", action="store_true", help="Skip category analysis")
    parser.add_argument("--skip-menu-items", action="store_true", help="Skip menu item analysis")
    parser.add_argument("--skip-competitors", action="store_true", help="Skip competitor analysis")

    return parser.parse_args()


def main():
    args = parse_args()

    # Build platform URL map
    platforms = [p.strip() for p in args.platforms.split(",")]
    url_map = {
        "google": args.google_url,
        "opentable": args.opentable_url,
        "yelp": args.yelp_url,
        "tripadvisor": args.tripadvisor_url,
    }

    platform_urls = {}
    for p in platforms:
        if p in url_map and url_map[p]:
            platform_urls[p] = url_map[p]
        else:
            print(f"⚠️ No URL provided for {p} — skipping. Use --{p.replace('_', '-')}-url to provide one.")

    if not platform_urls:
        print("❌ No valid platform URLs provided. Exiting.")
        sys.exit(1)

    # Run main pipeline
    result = run_pipeline(
        restaurant_name=args.restaurant,
        platform_urls=platform_urls,
        max_reviews=args.max_reviews,
        output_dir=args.output_dir,
        use_modal=not args.local,
        headless=not args.no_headless,
        run_category=not args.skip_category,
        run_menu_items=not args.skip_menu_items,
    )

    if not result.get("success"):
        print(f"\n❌ Pipeline failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    # Competitor analysis
    competitive_analysis = None
    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]
    if competitors and not args.skip_competitors:
        print(f"\n{'='*70}")
        print(f"🏆 COMPETITOR ANALYSIS: {len(competitors)} competitors")
        print(f"{'='*70}")

        competitor_results = []
        for comp_name in competitors:
            print(f"\n--- Competitor: {comp_name} ---")
            # For competitors, we'd need URLs too — for now, this is a placeholder
            # In production, use the research skill to find URLs first
            print(f"⚠️ Competitor '{comp_name}' requires manual URL input for now.")
            print(f"   Future: auto-search via Food Factor research skill.")

        if competitor_results:
            api_key = get_api_key()
            competitive_analysis = build_comparison(result, competitor_results, api_key)

    # Export everything
    export_results(result, args.output_dir, competitive_analysis)

    print(f"\n{'='*70}")
    print(f"🎉 FOOD FACTOR PIPELINE COMPLETE")
    print(f"   Restaurant: {args.restaurant}")
    print(f"   Reviews analyzed: {result['stats']['total_reviews']}")
    print(f"   Food items: {result['stats']['food_items']}")
    print(f"   Drinks: {result['stats']['drinks']}")
    print(f"   Aspects: {result['stats']['aspects']}")
    print(f"   Time: {result['stats']['processing_time_seconds']}s")
    print(f"   Output: {args.output_dir}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
