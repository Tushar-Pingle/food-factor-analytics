"""
Yelp Review Scraper — NEW for Food Factor pipeline.

Follows the same pattern as OpenTable and Google Maps scrapers:
- Selenium with anti-detection
- Pagination via "Next" button clicks
- Fallback selectors for resilience
- Returns NESTED format via BaseScraper._build_result()

Yelp pages render review cards in a paginated list (typically 10 per page).
"""

import time
import re
from typing import Dict, Any, Optional, Callable, List

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper


class YelpScraper(BaseScraper):
    """Scrapes restaurant reviews from Yelp."""

    PLATFORM = "yelp"

    # Yelp selectors — updated for 2025 Yelp DOM
    SELECTORS = {
        "review_cards": [
            "//li[contains(@class, 'margin-b5__09f24__pTvws')]//div[contains(@class, 'review__09f24')]",
            "//div[@data-testid='review-list']//li",
            "//section[contains(@aria-label, 'Reviews')]//li[.//p and .//span]",
            "//ul[contains(@class, 'list__09f24')]/li[.//div[contains(@class, 'comment')]]",
            # Broader fallback
            "//div[contains(@class, 'review')]//div[contains(@class, 'comment')]/..",
        ],
        "reviewer_name": [
            ".//a[contains(@href, '/user_details')]",
            ".//a[contains(@class, 'user-display-name')]",
            ".//span[contains(@class, 'fs-block')]/a",
            ".//a[@data-testid='user-passport-info']",
        ],
        "date": [
            ".//span[contains(@class, 'css-chan6m')]",
            ".//span[contains(text(), '202')]",  # Match year
            ".//span[contains(text(), '/')]",
            ".//time",
        ],
        "rating": [
            ".//div[contains(@class, 'star-rating')]/@aria-label",
            ".//div[contains(@aria-label, 'star rating')]",
            ".//span[contains(@class, 'icon--24-star')]/../..",
            ".//div[contains(@class, 'five-stars')]",
        ],
        "review_text": [
            ".//p[contains(@class, 'comment__09f24')]//span[contains(@class, 'raw__09f24')]",
            ".//span[contains(@class, 'raw__09f24')]",
            ".//p[contains(@class, 'comment')]//span[@lang]",
            ".//p[contains(@class, 'comment')]",
            ".//span[@lang='en']",
        ],
        "next_button": [
            "//a[contains(@class, 'next-link')]",
            "//a[@aria-label='Next']",
            "//a[.//span[text()='Next']]",
            "//link[@rel='next']",
            "//a[contains(@href, 'start=')][@class and contains(@class, 'next')]",
        ],
        "page_loaded": [
            "//section[contains(@aria-label, 'Review')]",
            "//div[@data-testid='review-list']",
            "//h2[contains(text(), 'Review')]",
            "//div[contains(@class, 'review')]",
        ],
    }

    def __init__(self, headless: bool = True, chromedriver_path: Optional[str] = None):
        super().__init__(headless=headless, chromedriver_path=chromedriver_path)

    def _validate_url(self, url: str) -> bool:
        return "yelp.c" in url.lower()

    def _extract_star_rating(self, review_element) -> float:
        """Extract star rating from Yelp review card."""
        # Yelp encodes rating in aria-label like "5 star rating"
        for selector in self.SELECTORS["rating"]:
            try:
                elem = review_element.find_element(By.XPATH, selector)
                # Check aria-label first
                aria = elem.get_attribute("aria-label") or ""
                match = re.search(r"(\d+(?:\.\d+)?)\s*star", aria.lower())
                if match:
                    return float(match.group(1))
                # Some Yelp layouts encode in role="img" with aria-label
                role_img = review_element.find_elements(
                    By.XPATH, ".//div[@role='img'][@aria-label]"
                )
                for ri in role_img:
                    aria2 = ri.get_attribute("aria-label") or ""
                    match2 = re.search(r"(\d+(?:\.\d+)?)\s*star", aria2.lower())
                    if match2:
                        return float(match2.group(1))
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return 0.0

    def _click_next(self) -> bool:
        """Navigate to the next page of reviews."""
        # Scroll to bottom first
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except Exception:
            pass

        for selector in self.SELECTORS["next_button"]:
            try:
                next_btn = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if next_btn:
                    href = next_btn.get_attribute("href")
                    if href:
                        self.driver.get(href)
                        time.sleep(3)
                        return True
                    else:
                        self.driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(3)
                        return True
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
        """Scrape reviews from a Yelp restaurant page."""
        if not self._validate_url(url):
            return self._build_error("Invalid Yelp URL")

        try:
            self._init_driver()
        except Exception as e:
            return self._build_error(f"Browser init failed: {str(e)[:200]}")

        try:
            self._log("🚀 Starting Yelp scraper...", progress_callback)
            self.driver.get(url)

            self._log("⏳ Waiting for page to load...", progress_callback)
            if not self._wait_for_element(self.SELECTORS["page_loaded"], timeout=10):
                time.sleep(3)

            names, dates, ratings, review_texts = [], [], [], []
            page_count = 0

            while True:
                page_count += 1
                self._log(f"📄 Scraping page {page_count}...", progress_callback)

                review_elements = self._find_elements_with_fallback(
                    self.SELECTORS["review_cards"], By.XPATH
                )

                if not review_elements:
                    # Broader fallback: find any element with substantial text
                    self._log("⚠️ Primary selectors failed, trying broader fallback...", progress_callback)
                    review_elements = self.driver.find_elements(
                        By.XPATH, "//li[.//p[string-length(normalize-space()) > 50]]"
                    )

                if not review_elements:
                    self._log("⚠️ No reviews found on page.", progress_callback)
                    break

                self._log(f"✅ Found {len(review_elements)} review cards", progress_callback)

                for idx, review in enumerate(review_elements):
                    if max_reviews and len(review_texts) >= max_reviews:
                        break

                    try:
                        name = self._extract_text_with_fallback(review, self.SELECTORS["reviewer_name"])
                        date = self._extract_text_with_fallback(review, self.SELECTORS["date"])
                        rating = self._extract_star_rating(review)
                        text = self._extract_text_with_fallback(review, self.SELECTORS["review_text"])

                        if text and len(text.strip()) > 10:
                            names.append(name)
                            dates.append(date)
                            ratings.append(rating)
                            review_texts.append(text)

                            if len(review_texts) % 10 == 0:
                                self._log(f"📊 Extracted {len(review_texts)} reviews...", progress_callback)
                    except Exception as e:
                        self._log(f"⚠️ Error on review {idx}: {e}", progress_callback)
                        continue

                if max_reviews and len(review_texts) >= max_reviews:
                    break

                if not self._click_next():
                    self._log("📍 No more pages.", progress_callback)
                    break

            self._log(f"✅ DONE! Scraped {len(review_texts)} Yelp reviews from {page_count} pages", progress_callback)

            return self._build_result(
                success=True,
                names=names,
                dates=dates,
                overall_ratings=ratings,
                review_texts=review_texts,
                url=url,
                pages_or_scrolls=page_count,
            )

        except Exception as e:
            self._log(f"❌ Fatal error: {e}", progress_callback)
            return self._build_error(str(e))
        finally:
            self._cleanup()


def scrape_yelp(
    url: str,
    max_reviews: Optional[int] = None,
    headless: bool = True,
    chromedriver_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function."""
    scraper = YelpScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)
