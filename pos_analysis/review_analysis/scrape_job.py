"""
Modal Scrape Job — Parallelized scraping across platforms.

Runs each platform scraper in its own Modal container for parallelism.
"""

import modal
from typing import Dict, Any

from .nlp_job import app, image
from ..config import MODAL_SECRET_BATCH1


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(MODAL_SECRET_BATCH1)],
    timeout=600,
    memory=1024,
)
def scrape_platform(
    platform: str,
    url: str,
    max_reviews: int = 500,
) -> Dict[str, Any]:
    """
    Scrape a single platform in a Modal container.

    Args:
        platform: "opentable", "google", "yelp", "tripadvisor"
        url: Direct URL to the restaurant's page on that platform
        max_reviews: Maximum reviews to scrape

    Returns:
        Standard NESTED result dict from the scraper
    """
    print(f"🕷️ [{platform.upper()}] Scraping up to {max_reviews} reviews from {url[:80]}...")

    try:
        if platform == "opentable":
            from ..scrapers.opentable_scraper import scrape_opentable
            return scrape_opentable(url, max_reviews=max_reviews, headless=True)

        elif platform in ("google", "google_maps"):
            from ..scrapers.google_maps_scraper import scrape_google_maps
            return scrape_google_maps(url, max_reviews=max_reviews, headless=True)

        elif platform == "yelp":
            from ..scrapers.yelp_scraper import scrape_yelp
            return scrape_yelp(url, max_reviews=max_reviews, headless=True)

        elif platform == "tripadvisor":
            from ..scrapers.tripadvisor_scraper import scrape_tripadvisor
            return scrape_tripadvisor(url, max_reviews=max_reviews, headless=True)

        else:
            return {"success": False, "error": f"Unknown platform: {platform}", "reviews": {}}

    except Exception as e:
        print(f"❌ [{platform.upper()}] Scrape failed: {e}")
        return {"success": False, "error": str(e), "reviews": {}}
