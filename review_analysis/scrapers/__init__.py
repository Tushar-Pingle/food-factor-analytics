"""
Review Scrapers — Multi-platform review collection.

Provides scrapers for:
- OpenTable (opentable_scraper)
- Google Maps (google_maps_scraper)
- Yelp (yelp_scraper)
- TripAdvisor (tripadvisor_scraper)

All inherit from BaseScraper and return NESTED dict format.
"""

from .base_scraper import BaseScraper
from .opentable_scraper import scrape_opentable, OpenTableScraper
from .google_maps_scraper import scrape_google_maps, GoogleMapsScraper
from .yelp_scraper import scrape_yelp, YelpScraper
from .tripadvisor_scraper import scrape_tripadvisor, TripAdvisorScraper

__all__ = [
    "BaseScraper",
    "scrape_opentable",
    "OpenTableScraper",
    "scrape_google_maps",
    "GoogleMapsScraper",
    "scrape_yelp",
    "YelpScraper",
    "scrape_tripadvisor",
    "TripAdvisorScraper",
]
