"""
Base Scraper — Shared Selenium setup, anti-detection, retry logic.

Extracted from:
- src/scrapers/opentable_scraper.py (_init_driver, _find_chromedriver, _cleanup, etc.)
- src/scrapers/google_maps_scraper.py (_init_driver, _random_delay, anti-detection CDP)

All subclass scrapers inherit from this.
"""

import os
import time
import random
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from ..config import SCRAPER_USER_AGENT


class BaseScraper(ABC):
    """
    Abstract base for all review scrapers.

    Provides:
    - Chrome/Selenium lifecycle (_init_driver, _cleanup)
    - Anti-detection setup (user-agent, CDP overrides)
    - Shared DOM helpers (_find_elements_with_fallback, _extract_text_with_fallback)
    - Progress logging
    - Unified return format (NESTED dict)
    """

    PLATFORM: str = "unknown"  # Override in subclass

    def __init__(
        self,
        headless: bool = True,
        chromedriver_path: Optional[str] = None,
        page_load_strategy: str = "eager",
    ):
        self.headless = headless
        self.page_load_strategy = page_load_strategy
        self.driver = None
        self.wait = None
        self.chromedriver_path = chromedriver_path or self._find_chromedriver()

    # ------------------------------------------------------------------
    # Chrome lifecycle
    # ------------------------------------------------------------------

    def _find_chromedriver(self) -> str:
        """Find chromedriver in common locations (extracted from both scrapers)."""
        common_paths = [
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver",
            "/opt/chromedriver",
            "chromedriver",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path

        try:
            from webdriver_manager.chrome import ChromeDriverManager
            return ChromeDriverManager().install()
        except (ImportError, Exception):
            pass

        return "/usr/local/bin/chromedriver"

    def _init_driver(self):
        """Initialize Chrome WebDriver with anti-detection settings."""
        chrome_options = Options()
        chrome_options.page_load_strategy = self.page_load_strategy

        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument(f"--user-agent={SCRAPER_USER_AGENT}")

        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        try:
            service = Service(self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.set_page_load_timeout(60)
        self.wait = WebDriverWait(self.driver, 20)

        # CDP anti-detection (from google_maps_scraper)
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    """
                },
            )
        except Exception:
            pass  # Not all drivers support CDP

    def _cleanup(self):
        """Close browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ------------------------------------------------------------------
    # DOM helpers
    # ------------------------------------------------------------------

    def _find_elements_with_fallback(
        self, selectors: List[str], by: By = By.XPATH
    ) -> List:
        """Try multiple selectors until one returns elements."""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    return elements
            except Exception:
                continue
        return []

    def _extract_text_with_fallback(
        self, parent_element, selectors: List[str]
    ) -> str:
        """Try multiple selectors to extract text from a parent element."""
        for selector in selectors:
            try:
                element = parent_element.find_element(By.XPATH, selector)
                text = element.text.strip()
                if text:
                    return text
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return ""

    def _extract_rating_from_aria(self, element, selectors: List[str]) -> float:
        """Extract numeric rating from aria-label attributes."""
        for selector in selectors:
            try:
                elem = element.find_element(By.XPATH, selector)
                aria_label = elem.get_attribute("aria-label")
                if aria_label:
                    match = re.search(r"(\d+(?:\.\d+)?)\s*star", aria_label.lower())
                    if match:
                        return float(match.group(1))
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return 0.0

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    def _random_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """Add random delay for anti-detection."""
        time.sleep(random.uniform(min_sec, max_sec))

    def _wait_for_element(self, selectors: List[str], timeout: int = 10) -> bool:
        """Wait for any of the given selectors to appear."""
        for selector in selectors:
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                return True
            except TimeoutException:
                continue
        return False

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message: str, callback: Optional[Callable] = None):
        """Log progress."""
        print(message)
        if callback:
            callback(message)

    # ------------------------------------------------------------------
    # Unified return format
    # ------------------------------------------------------------------

    def _build_result(
        self,
        success: bool,
        names: List[str],
        dates: List[str],
        overall_ratings: List[float],
        review_texts: List[str],
        url: str,
        pages_or_scrolls: int,
        food_ratings: Optional[List[float]] = None,
        service_ratings: Optional[List[float]] = None,
        ambience_ratings: Optional[List[float]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the standard NESTED result dict used by all scrapers."""
        n = len(review_texts)
        if not success or n == 0:
            return {
                "success": False,
                "error": error or "No reviews found",
                "reviews": {},
            }

        return {
            "success": True,
            "total_reviews": n,
            "total_pages": pages_or_scrolls,
            "reviews": {
                "names": names[:n],
                "dates": dates[:n],
                "overall_ratings": overall_ratings[:n],
                "food_ratings": (food_ratings or [0.0] * n)[:n],
                "service_ratings": (service_ratings or [0.0] * n)[:n],
                "ambience_ratings": (ambience_ratings or [0.0] * n)[:n],
                "review_texts": review_texts[:n],
            },
            "metadata": {
                "source": self.PLATFORM,
                "url": url,
                "pages_scraped": pages_or_scrolls,
            },
        }

    def _build_error(self, error: str) -> Dict[str, Any]:
        return {"success": False, "error": error, "reviews": {}}

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Scrape reviews and return NESTED result dict."""
        ...

    def __del__(self):
        self._cleanup()
