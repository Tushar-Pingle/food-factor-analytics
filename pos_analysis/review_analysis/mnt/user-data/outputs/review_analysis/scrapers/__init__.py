"""
Scrapers package — platform-specific review scrapers.

All scrapers return the NESTED format:
{
    "success": True,
    "total_reviews": N,
    "reviews": {
        "names": [...],
        "dates": [...],
        "overall_ratings": [...],
        "food_ratings": [...],
        "service_ratings": [...],
        "ambience_ratings": [...],
        "review_texts": [...]
    },
    "metadata": {"source": "platform_name", "url": "...", "pages_scraped": N}
}
"""

from .opentable_scraper import OpenTableScraper, scrape_opentable
from .google_maps_scraper import GoogleMapsScraper, scrape_google_maps
from .yelp_scraper import YelpScraper, scrape_yelp
from .tripadvisor_scraper import TripAdvisorScraper, scrape_tripadvisor

__all__ = [
    "OpenTableScraper",
    "GoogleMapsScraper",
    "YelpScraper",
    "TripAdvisorScraper",
    "scrape_opentable",
    "scrape_google_maps",
    "scrape_yelp",
    "scrape_tripadvisor",
]
