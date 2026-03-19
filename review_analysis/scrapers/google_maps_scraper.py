"""
Google Maps Review Scraper — EXTRACTED from src/scrapers/google_maps_scraper.py

All scraping logic, selectors, scroll-based pagination, and "More" expansion preserved.
Only change: inherits from BaseScraper instead of standalone class.

VERIFIED selectors (Nov 2025):
- Review cards: div.jftiEf.fontBodyMedium with data-review-id
- Reviewer name: div.d4r55
- Star rating: span.kvMYJc > span[aria-label*="star"]
- Date: span.rsqaWe
- Review text: span.wiI7pd (truncated) or span[jsname='fbQN7e'] (full)
- More button: button.w8nwRe or button.kyuUzc
- Scrollable container: div.m6QErb.DxyBCb or div.XiKgde
"""

import time
import re
import random
from typing import List, Dict, Any, Optional, Callable

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper


class GoogleMapsScraper(BaseScraper):
    """Scrapes restaurant reviews from Google Maps."""

    PLATFORM = "google_maps"

    SELECTORS = {
        "reviews_tab": [
            "//button[contains(@aria-label, 'Reviews')]",
            "//button[@role='tab'][contains(., 'Reviews')]",
            "//button[@role='tab'][contains(., 'reviews')]",
            "//div[@role='tablist']//button[contains(., 'Review')]",
            "//button[@data-tab-index='1']",
            "//button[contains(@class, 'hh2c6')]",
        ],
        "scrollable_div": [
            "//div[contains(@class, 'm6QErb') and contains(@class, 'DxyBCb')]",
            "//div[contains(@class, 'XiKgde')]",
            "//div[@role='feed']",
            "//div[contains(@class, 'm6QErb')][@tabindex='-1']",
            "//div[contains(@class, 'm6QErb')]",
        ],
        "review_cards": [
            "//div[@data-review-id]",
            "//div[contains(@class, 'jftiEf') and contains(@class, 'fontBodyMedium')]",
            "//div[contains(@class, 'jftiEf')]",
        ],
        "reviewer_name": [
            ".//div[contains(@class, 'd4r55')]",
            ".//button[contains(@class, 'WEBjve')]//div",
            ".//a[contains(@class, 'WNBkOb')]//div[1]",
        ],
        "rating": [
            ".//span[contains(@class, 'kvMYJc')]//span[@aria-label]",
            ".//span[@aria-label][contains(@aria-label, 'star')]",
            ".//div[@role='img'][@aria-label]",
        ],
        "date": [
            ".//span[contains(@class, 'rsqaWe')]",
            ".//span[contains(text(), 'ago')]",
            ".//span[contains(text(), 'week')]",
            ".//span[contains(text(), 'month')]",
            ".//span[contains(text(), 'day')]",
            ".//span[contains(text(), 'year')]",
        ],
        "review_text": [
            ".//span[contains(@class, 'wiI7pd')]",
            ".//span[@jsname='fbQN7e']",
            ".//span[@jsname='bN97Pc']",
            ".//div[contains(@class, 'MyEned')]//span",
        ],
        "more_button": [
            ".//button[contains(@class, 'w8nwRe')]",
            ".//button[contains(@class, 'kyuUzc')]",
            ".//button[@aria-expanded='false']",
            ".//button[contains(@aria-label, 'More')]",
            ".//button[contains(@aria-label, 'more')]",
            ".//span[text()='More']/parent::button",
            ".//button[.//span[text()='More']]",
        ],
        "page_loaded": [
            "//div[contains(@class, 'fontHeadlineSmall')]",
            "//button[contains(@aria-label, 'Reviews')]",
            "//div[@role='main']",
            "//h1",
        ],
    }

    def __init__(self, headless: bool = True, chromedriver_path: Optional[str] = None):
        super().__init__(headless=headless, chromedriver_path=chromedriver_path)

    # ------------------------------------------------------------------
    # Google Maps–specific helpers (extracted intact)
    # ------------------------------------------------------------------

    def _expand_review_text(self, review_element):
        """Click 'More' button to expand truncated review."""
        for selector in self.SELECTORS["more_button"]:
            try:
                more_btn = review_element.find_element(By.XPATH, selector)
                if more_btn and more_btn.is_displayed():
                    try:
                        more_btn.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", more_btn)
                    self._random_delay(0.3, 0.6)
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return False

    def _get_scrollable_element(self, progress_callback=None):
        """Find the scrollable reviews container."""
        for selector in self.SELECTORS["scrollable_div"]:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element:
                    self._log(f"✅ Found scrollable container", progress_callback)
                    return element
            except NoSuchElementException:
                continue
        return None

    def _scroll_reviews(self, scrollable_element, scroll_pause: float = 1.5):
        """Scroll the reviews panel to load more."""
        if not scrollable_element:
            return False
        try:
            last_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", scrollable_element
            )
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element
            )
            time.sleep(scroll_pause + random.uniform(0, 0.5))
            new_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", scrollable_element
            )
            return new_height > last_height
        except Exception:
            return False

    def _click_reviews_tab(self, progress_callback=None) -> bool:
        """Click on the Reviews tab."""
        time.sleep(3)
        for selector in self.SELECTORS["reviews_tab"]:
            try:
                tab = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                tab.click()
                self._log("✅ Clicked Reviews tab", progress_callback)
                time.sleep(3)
                return True
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                continue

        # Fallback: find any button with "Review" text
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                try:
                    btn_text = btn.text.lower()
                    btn_aria = (btn.get_attribute("aria-label") or "").lower()
                    if "review" in btn_text or "review" in btn_aria:
                        btn.click()
                        time.sleep(3)
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        return False

    def _handle_consent_dialog(self, progress_callback=None):
        """Handle Google consent/cookie dialog."""
        consent_selectors = [
            "//button[contains(., 'Accept all')]",
            "//button[contains(., 'Reject all')]",
            "//button[contains(., 'Accept')]",
            "//button[contains(., 'I agree')]",
        ]
        for selector in consent_selectors:
            try:
                btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if btn.is_displayed():
                    self._log("🍪 Handling consent dialog...", progress_callback)
                    btn.click()
                    time.sleep(2)
                    return True
            except Exception:
                continue
        return False

    def _extract_review_data(self, review_element, idx: int) -> Optional[Dict]:
        """Extract all data from a single review card."""
        try:
            self._expand_review_text(review_element)

            name = self._extract_text_with_fallback(review_element, self.SELECTORS["reviewer_name"])
            date = self._extract_text_with_fallback(review_element, self.SELECTORS["date"])
            rating = self._extract_rating_from_aria(review_element, self.SELECTORS["rating"])

            # Try expanded first, then truncated
            text = ""
            for selector in [".//span[@jsname='fbQN7e']", ".//span[contains(@class, 'wiI7pd')]"]:
                try:
                    elem = review_element.find_element(By.XPATH, selector)
                    t = elem.text.strip()
                    if t and len(t) > len(text):
                        text = t
                except Exception:
                    continue

            if not text:
                text = self._extract_text_with_fallback(review_element, self.SELECTORS["review_text"])

            if not text or len(text) < 10:
                return None

            return {"name": name, "date": date.strip() if date else "", "rating": rating, "text": text}

        except StaleElementReferenceException:
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Main scrape method
    # ------------------------------------------------------------------

    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Scrape reviews from Google Maps restaurant page."""
        url_lower = url.lower()
        valid = any(x in url_lower for x in ["google.com/maps", "goo.gl/maps", "maps.google", "maps.app.goo.gl"])
        if not valid:
            return self._build_error("Invalid Google Maps URL")

        try:
            self._init_driver()
        except Exception as e:
            return self._build_error(f"Browser init failed: {str(e)[:200]}")

        try:
            self._log("🚀 Starting Google Maps scraper...", progress_callback)
            self.driver.get(url)

            self._log("⏳ Waiting for page to load...", progress_callback)
            if not self._wait_for_element(self.SELECTORS["page_loaded"], timeout=10):
                time.sleep(3)

            self._handle_consent_dialog(progress_callback)

            # Click Reviews tab
            self._log("📋 Looking for Reviews tab...", progress_callback)
            if not self._click_reviews_tab(progress_callback):
                self._log("⚠️ Could not find Reviews tab, trying to scroll anyway...", progress_callback)
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(2)

            time.sleep(3)

            scrollable = self._get_scrollable_element(progress_callback)

            # Data containers
            names, dates, ratings, review_texts = [], [], [], []
            processed_ids = set()
            scroll_count = 0
            no_new_reviews_count = 0
            max_no_new = 5
            max_scrolls = (max_reviews // 3) + 20 if max_reviews else 100

            while scroll_count < max_scrolls and no_new_reviews_count < max_no_new:
                scroll_count += 1
                review_elements = self._find_elements_with_fallback(self.SELECTORS["review_cards"])

                self._log(
                    f"📄 Scroll {scroll_count}: {len(review_elements)} cards, {len(review_texts)} collected",
                    progress_callback,
                )

                new_this_scroll = 0
                for idx, review_elem in enumerate(review_elements):
                    if max_reviews and len(review_texts) >= max_reviews:
                        break

                    try:
                        review_id = review_elem.get_attribute("data-review-id")
                        if not review_id:
                            review_id = f"pos_{idx}_{review_elem.location['y']}"
                    except Exception:
                        review_id = f"idx_{idx}_{scroll_count}"

                    if review_id in processed_ids:
                        continue

                    review_data = self._extract_review_data(review_elem, idx)
                    if review_data and review_data["text"] not in review_texts:
                        names.append(review_data["name"])
                        dates.append(review_data["date"])
                        ratings.append(review_data["rating"])
                        review_texts.append(review_data["text"])
                        new_this_scroll += 1

                    processed_ids.add(review_id)
                    if idx % 5 == 0:
                        self._random_delay(0.1, 0.3)

                if new_this_scroll == 0:
                    no_new_reviews_count += 1
                else:
                    no_new_reviews_count = 0

                if max_reviews and len(review_texts) >= max_reviews:
                    self._log(f"🎯 Reached target: {max_reviews} reviews", progress_callback)
                    break

                if scrollable:
                    self._scroll_reviews(scrollable)
                else:
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(1.5)

            self._log(f"✅ Scraped {len(review_texts)} reviews from Google Maps", progress_callback)

            return self._build_result(
                success=True,
                names=names,
                dates=dates,
                overall_ratings=ratings,
                review_texts=review_texts,
                url=url,
                pages_or_scrolls=scroll_count,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._build_error(str(e))
        finally:
            self._cleanup()


def scrape_google_maps(
    url: str,
    max_reviews: Optional[int] = None,
    headless: bool = True,
    chromedriver_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function matching original API."""
    scraper = GoogleMapsScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)
