"""
OpenTable Review Scraper — EXTRACTED from src/scrapers/opentable_scraper.py

All scraping logic, selectors, and pagination preserved intact.
Only change: inherits from BaseScraper instead of standalone class.

DO NOT ADD:
- Retry logic with delays (breaks things)
- page_load_strategy = 'normal' (too slow)
- Complex _extract_review_text fallbacks (hangs)
- 20+ Chrome options (unnecessary)
"""

import time
from typing import List, Dict, Any, Optional, Callable

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper


class OpenTableScraper(BaseScraper):
    """Scrapes restaurant reviews from OpenTable using production-tested selectors."""

    PLATFORM = "opentable"

    # Production selectors discovered from live DOM inspection (Jan 2025)
    SELECTORS = {
        "review_cards": [
            "//li[@data-test='reviews-list-item']",
            "//section[@id='reviews']//li[contains(., 'Dined')]",
            "//section[.//h2[contains(., 'people are saying') or contains(., 'Reviews')]]//li[.//p or .//span or .//time]",
            "//li[@data-test='review']",
        ],
        "next_button": [
            "//a[@aria-label='Go to the next page']",
            "//*[@data-test='pagination-next']/ancestor::a[1]",
            "//div[@data-test='pagination-next']/ancestor::a[1]",
            "//a[@rel='next' or contains(@href,'page=')][not(@aria-disabled='true')]",
        ],
        "name": [
            ".//p[@data-test='reviewer-name']",
            ".//header//p[1]",
            ".//header//span[1]",
            ".//p[1]",
        ],
        "date": [
            ".//p[contains(., 'Dined')]",
            ".//time",
            ".//p[contains(@class,'date')]",
            ".//div[contains(@class,'date')]",
        ],
        "overall_rating": [
            ".//li[.//*[contains(., 'Overall')]]//span[normalize-space()]",
            ".//li[contains(., 'Overall')]//span",
            ".//span[contains(@data-test,'overall')]",
        ],
        "food_rating": [
            ".//li[.//*[contains(., 'Food')]]//span[normalize-space()]",
            ".//li[contains(., 'Food')]//span",
        ],
        "service_rating": [
            ".//li[.//*[contains(., 'Service')]]//span[normalize-space()]",
            ".//li[contains(., 'Service')]//span",
        ],
        "ambience_rating": [
            ".//li[.//*[contains(., 'Ambience')]]//span[normalize-space()]",
            ".//li[contains(., 'Ambience')]//span",
        ],
        "review_text": [
            ".//span[@data-test='wrapper-tag']",
            ".//div[@data-test='wrapper-tag']",
            ".//p[@data-test='review-text']",
            ".//div[contains(@class,'review')]/p",
            ".//div[contains(@class,'review')]/span",
            ".//p[not(contains(., 'Dined')) and not(.//*) and string-length(normalize-space())>20]",
            ".//span[not(contains(., 'Dined')) and not(.//*) and string-length(normalize-space())>20]",
        ],
        "page_loaded": [
            "//section[@id='reviews']",
            "//section[contains(@class, 'review')]",
            "//li[@data-test='reviews-list-item']",
            "//h2[contains(., 'people are saying') or contains(., 'Reviews')]",
        ],
    }

    def __init__(self, headless: bool = True, chromedriver_path: Optional[str] = None):
        super().__init__(
            headless=headless,
            chromedriver_path=chromedriver_path,
            page_load_strategy="eager",  # KEEP 'eager' — it works!
        )

    def _validate_url(self, url: str) -> bool:
        return "opentable.c" in url.lower()

    def _click_next(self) -> bool:
        """Click 'Next' button — FIXED FOR 2025 OPENTABLE."""
        # Scroll to bottom to ensure pagination is visible
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except Exception:
            pass

        next_selectors = [
            "//a[@aria-label='Go to the next page']",
            "//div[@data-test='pagination-next']/parent::a",
            "//a[.//div[@data-test='pagination-next']]",
            "//a[contains(@class, 'C7Tp-bANpE4')]",
            "//*[@data-test='pagination-next']/ancestor::a[1]",
            "//a[@rel='next']",
        ]

        for selector in next_selectors:
            try:
                next_btn = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if next_btn:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", next_btn
                    )
                    time.sleep(0.5)

                    is_disabled = next_btn.get_attribute("aria-disabled")
                    if is_disabled == "true":
                        return False

                    try:
                        self.driver.execute_script("arguments[0].click();", next_btn)
                        return True
                    except Exception:
                        try:
                            next_btn.click()
                            return True
                        except Exception:
                            continue
            except (TimeoutException, NoSuchElementException):
                continue
            except Exception:
                continue

        return False

    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Scrape reviews from OpenTable restaurant page."""
        if not self._validate_url(url):
            return self._build_error("Invalid OpenTable URL")

        try:
            self._init_driver()
        except Exception as e:
            error_msg = str(e).lower()
            if "chromedriver" in error_msg or "chrome" in error_msg:
                return self._build_error(
                    f"Browser initialization failed. Ensure Chrome/Chromedriver installed. Details: {str(e)[:200]}"
                )
            return self._build_error(f"Browser init failed: {str(e)}")

        try:
            self._log("🚀 Starting OpenTable scraper...", progress_callback)
            self.driver.get(url)

            self._log("⏳ Waiting for page to load...", progress_callback)
            if not self._wait_for_element(self.SELECTORS["page_loaded"], timeout=10):
                self._log("⚠️ Page load check timed out, continuing with fallback...", progress_callback)
                time.sleep(3)

            # Data containers
            names, dates = [], []
            overall_ratings, food_ratings, service_ratings, ambience_ratings = [], [], [], []
            review_texts = []

            page_count = 0
            review_count = 0

            while True:
                page_count += 1
                self._log(f"📄 Scraping page {page_count}...", progress_callback)

                review_elements = self._find_elements_with_fallback(
                    self.SELECTORS["review_cards"], By.XPATH
                )

                if not review_elements:
                    self._log("⚠️ No reviews found on page.", progress_callback)
                    break

                self._log(f"✅ Found {len(review_elements)} review cards", progress_callback)

                for idx, review in enumerate(review_elements):
                    if max_reviews and review_count >= max_reviews:
                        break

                    try:
                        name = self._extract_text_with_fallback(review, self.SELECTORS["name"])
                        date = self._extract_text_with_fallback(review, self.SELECTORS["date"])
                        overall = self._extract_text_with_fallback(review, self.SELECTORS["overall_rating"])
                        food = self._extract_text_with_fallback(review, self.SELECTORS["food_rating"])
                        service = self._extract_text_with_fallback(review, self.SELECTORS["service_rating"])
                        ambience = self._extract_text_with_fallback(review, self.SELECTORS["ambience_rating"])
                        text = self._extract_text_with_fallback(review, self.SELECTORS["review_text"])

                        if text and "Dined on" in text:
                            text = ""

                        if text and len(text.strip()) > 10:
                            names.append(name)
                            dates.append(date)
                            overall_ratings.append(overall)
                            food_ratings.append(food)
                            service_ratings.append(service)
                            ambience_ratings.append(ambience)
                            review_texts.append(text)
                            review_count += 1

                            if review_count % 10 == 0:
                                self._log(f"📊 Extracted {review_count} reviews so far...", progress_callback)
                    except Exception as e:
                        self._log(f"⚠️ Error on review {idx + 1}: {e}", progress_callback)
                        continue

                if max_reviews and review_count >= max_reviews:
                    break

                if not self._click_next():
                    self._log("📍 No more pages. Scraping complete!", progress_callback)
                    break

                time.sleep(3)

            self._log(f"✅ DONE! Scraped {review_count} reviews from {page_count} pages", progress_callback)

            return self._build_result(
                success=True,
                names=names,
                dates=dates,
                overall_ratings=overall_ratings,
                review_texts=review_texts,
                url=url,
                pages_or_scrolls=page_count,
                food_ratings=food_ratings,
                service_ratings=service_ratings,
                ambience_ratings=ambience_ratings,
            )

        except Exception as e:
            self._log(f"❌ Fatal error: {e}", progress_callback)
            return self._build_error(str(e))
        finally:
            self._cleanup()


def scrape_opentable(
    url: str,
    max_reviews: Optional[int] = None,
    headless: bool = True,
    chromedriver_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function matching original API."""
    scraper = OpenTableScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)
