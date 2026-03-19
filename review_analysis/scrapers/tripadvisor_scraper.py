"""
TripAdvisor Review Scraper — NEW for Food Factor pipeline.

Follows the same pattern as other scrapers. TripAdvisor paginates reviews
with offset-based URLs (or-XX in the URL path).
"""

import time
import re
from typing import Dict, Any, Optional, Callable, List

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper


class TripAdvisorScraper(BaseScraper):
    """Scrapes restaurant reviews from TripAdvisor."""

    PLATFORM = "tripadvisor"

    SELECTORS = {
        "review_cards": [
            "//div[@data-automation='reviewCard']",
            "//div[contains(@class, 'review-container')]",
            "//div[@data-test-target='HR_CC_CARD']",
            "//div[contains(@class, '_c')]//div[contains(@class, 'YibKl')]",
            # Broader fallback
            "//div[contains(@class, 'review')]//div[.//span[string-length(normalize-space()) > 50]]",
        ],
        "reviewer_name": [
            ".//a[contains(@class, 'ui_header_link')]",
            ".//span[contains(@class, 'socialMemberName')]//a",
            ".//a[@class and contains(@href, '/Profile/')]",
            ".//span[contains(@class, 'username')]",
        ],
        "date": [
            ".//span[contains(@class, 'ratingDate')]/@title",
            ".//span[contains(@class, 'ratingDate')]",
            ".//div[contains(@class, 'cRVSd')]",
            ".//span[contains(text(), '202')]",
            ".//time",
        ],
        "rating": [
            ".//span[contains(@class, 'ui_bubble_rating')]",
            ".//svg[contains(@class, 'UctUV')]",
            ".//div[contains(@class, 'Hlmiy')]//span[contains(@class, 'ui_bubble')]",
        ],
        "review_text": [
            ".//span[@data-automation='reviewText']//span",
            ".//span[contains(@class, 'QewHA')]//span",
            ".//div[contains(@class, 'review-body')]//p",
            ".//q//span",
            ".//div[contains(@class, 'entry')]//p",
            ".//span[@class and string-length(normalize-space()) > 30]",
        ],
        "read_more": [
            ".//span[contains(text(), 'Read more')]/..",
            ".//button[contains(text(), 'Read more')]",
            ".//div[contains(@data-automation, 'readMore')]",
            ".//span[contains(@class, 'Ignyf')]",
        ],
        "next_button": [
            "//a[contains(@class, 'next')]",
            "//a[@data-page-number and contains(@class, 'next')]",
            "//a[contains(@aria-label, 'Next')]",
            "//a[.//span[text()='Next']]",
        ],
        "page_loaded": [
            "//div[@data-automation='reviewCard']",
            "//div[contains(@class, 'review-container')]",
            "//h2[contains(text(), 'Review')]",
            "//div[@id='REVIEWS']",
        ],
    }

    def __init__(self, headless: bool = True, chromedriver_path: Optional[str] = None):
        super().__init__(headless=headless, chromedriver_path=chromedriver_path)

    def _validate_url(self, url: str) -> bool:
        return "tripadvisor.c" in url.lower()

    def _extract_bubble_rating(self, review_element) -> float:
        """Extract rating from TripAdvisor's bubble rating system."""
        for selector in self.SELECTORS["rating"]:
            try:
                elem = review_element.find_element(By.XPATH, selector)
                # TripAdvisor uses class like 'bubble_50' for 5.0 stars
                class_attr = elem.get_attribute("class") or ""
                match = re.search(r"bubble_(\d)(\d)", class_attr)
                if match:
                    return float(f"{match.group(1)}.{match.group(2)}")

                # Newer layout uses aria-label
                aria = elem.get_attribute("aria-label") or ""
                match2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:of\s*5|bubble|star)", aria.lower())
                if match2:
                    return float(match2.group(1))

                # SVG-based: count filled circles or check title
                title = elem.get_attribute("title") or ""
                match3 = re.search(r"(\d+(?:\.\d+)?)\s*of\s*5", title.lower())
                if match3:
                    return float(match3.group(1))

            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return 0.0

    def _expand_reviews(self, progress_callback=None):
        """Click 'Read more' on truncated reviews."""
        for selector in self.SELECTORS["read_more"]:
            try:
                buttons = self.driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    try:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            self._random_delay(0.2, 0.4)
                    except Exception:
                        continue
            except Exception:
                continue

    def _click_next(self) -> bool:
        """Navigate to the next page of reviews."""
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
        return False

    def _extract_date(self, review_element) -> str:
        """Extract date, handling both attribute and text approaches."""
        for selector in self.SELECTORS["date"]:
            try:
                if selector.endswith("/@title"):
                    base_sel = selector.replace("/@title", "")
                    elem = review_element.find_element(By.XPATH, base_sel)
                    title = elem.get_attribute("title")
                    if title:
                        return title.strip()
                else:
                    elem = review_element.find_element(By.XPATH, selector)
                    text = elem.text.strip()
                    if text:
                        return text
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return ""

    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Scrape reviews from a TripAdvisor restaurant page."""
        if not self._validate_url(url):
            return self._build_error("Invalid TripAdvisor URL")

        try:
            self._init_driver()
        except Exception as e:
            return self._build_error(f"Browser init failed: {str(e)[:200]}")

        try:
            self._log("🚀 Starting TripAdvisor scraper...", progress_callback)
            self.driver.get(url)

            self._log("⏳ Waiting for page to load...", progress_callback)
            if not self._wait_for_element(self.SELECTORS["page_loaded"], timeout=10):
                time.sleep(3)

            names, dates, ratings, review_texts = [], [], [], []
            page_count = 0

            while True:
                page_count += 1
                self._log(f"📄 Scraping page {page_count}...", progress_callback)

                # Expand truncated reviews before extracting
                self._expand_reviews(progress_callback)
                time.sleep(1)

                review_elements = self._find_elements_with_fallback(
                    self.SELECTORS["review_cards"], By.XPATH
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
                        date = self._extract_date(review)
                        rating = self._extract_bubble_rating(review)
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

            self._log(f"✅ DONE! Scraped {len(review_texts)} TripAdvisor reviews from {page_count} pages", progress_callback)

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


def scrape_tripadvisor(
    url: str,
    max_reviews: Optional[int] = None,
    headless: bool = True,
    chromedriver_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function."""
    scraper = TripAdvisorScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)
