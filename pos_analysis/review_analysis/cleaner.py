"""
Review Text Cleaner — EXTRACTED from src/data_processing/review_cleaner.py

All logic preserved intact: emoji removal, whitespace normalization, truncation,
duplicate detection (Jaccard similarity with 85% threshold).

This is proven code — do NOT rewrite.
"""

import re
import unicodedata
from typing import List, Set


class ReviewCleaner:
    """
    Cleans review text while preserving as much content as possible.
    Includes duplicate detection via Jaccard similarity.
    """

    MIN_REVIEW_LENGTH = 10
    DUPLICATE_SIMILARITY_THRESHOLD = 0.85

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {
            "total": 0,
            "kept": 0,
            "removed_empty": 0,
            "removed_short": 0,
            "removed_duplicates": 0,
            "chars_original": 0,
            "chars_cleaned": 0,
        }

    def clean_review(self, text: str) -> str:
        """Clean a single review text. Less aggressive — preserves more content."""
        if not text or not isinstance(text, str):
            return ""

        original_len = len(text)

        # 1. Basic whitespace normalization
        text = " ".join(text.split())

        # 2. Remove only truly problematic emojis
        text = self._remove_emojis(text)

        # 3. Normalize quotes
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")

        # 4. Remove control characters
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        text = "".join(
            char
            for char in text
            if unicodedata.category(char)[0] != "C" or char == " "
        )

        # 5. Normalize multiple spaces
        text = re.sub(r"\s+", " ", text)

        # 6. Truncate very long reviews (>1500 chars)
        if len(text) > 1500:
            text = text[:1497] + "..."

        text = text.strip()

        self.stats["chars_original"] += original_len
        self.stats["chars_cleaned"] += len(text)

        return text

    def _remove_emojis(self, text: str) -> str:
        """Remove emojis but keep most unicode characters."""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002702-\U000027B0"
            "]+",
            flags=re.UNICODE,
        )
        return emoji_pattern.sub("", text)

    # ------------------------------------------------------------------
    # Duplicate detection (PROC-02)
    # ------------------------------------------------------------------

    def _get_word_set(self, text: str) -> Set[str]:
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "is", "was", "are", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "this", "that", "these", "those",
            "i", "we", "you", "they", "it", "my", "our", "your", "their", "its",
            "very", "really", "so", "just", "also", "as", "if", "when", "where",
        }
        words = re.findall(r"\b[a-z]+\b", text.lower())
        return {w for w in words if len(w) > 2 and w not in stop_words}

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        words1 = self._get_word_set(text1)
        words2 = self._get_word_set(text2)
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _is_duplicate(self, text: str, existing_reviews: List[str]) -> bool:
        if text in existing_reviews:
            return True
        for existing in existing_reviews:
            if self._calculate_similarity(text, existing) >= self.DUPLICATE_SIMILARITY_THRESHOLD:
                return True
        return False

    # ------------------------------------------------------------------
    # Main clean method
    # ------------------------------------------------------------------

    def clean_reviews(self, reviews: List[str]) -> List[str]:
        """Clean a list of reviews. Removes empty, short, and duplicate entries."""
        self.stats = {
            "total": len(reviews), "kept": 0, "removed_empty": 0,
            "removed_short": 0, "removed_duplicates": 0,
            "chars_original": 0, "chars_cleaned": 0,
        }

        cleaned = []
        for review in reviews:
            cleaned_text = self.clean_review(review)

            if not cleaned_text:
                self.stats["removed_empty"] += 1
                continue
            if len(cleaned_text) < self.MIN_REVIEW_LENGTH:
                self.stats["removed_short"] += 1
                continue
            if self._is_duplicate(cleaned_text, cleaned):
                self.stats["removed_duplicates"] += 1
                continue

            cleaned.append(cleaned_text)
            self.stats["kept"] += 1

        return cleaned

    def get_cleaning_stats(self) -> dict:
        return {
            "original_count": self.stats["total"],
            "cleaned_count": self.stats["kept"],
            "removed_empty": self.stats["removed_empty"],
            "removed_short": self.stats["removed_short"],
            "removed_duplicates": self.stats["removed_duplicates"],
            "original_chars": self.stats["chars_original"],
            "cleaned_chars": self.stats["chars_cleaned"],
            "retention_rate": round(
                self.stats["kept"] / max(self.stats["total"], 1) * 100, 1
            ),
        }


def clean_reviews_for_ai(reviews: List[str], verbose: bool = True) -> List[str]:
    """Convenience function matching original API."""
    cleaner = ReviewCleaner(verbose=False)
    cleaned = cleaner.clean_reviews(reviews)

    if verbose:
        stats = cleaner.get_cleaning_stats()
        print(f"🧹 Cleaned {stats['original_count']} reviews:")
        print(f"   ✅ Kept: {stats['cleaned_count']} ({stats['retention_rate']}%)")
        if stats["removed_empty"] > 0:
            print(f"   ❌ Empty: {stats['removed_empty']}")
        if stats["removed_short"] > 0:
            print(f"   ❌ Too short: {stats['removed_short']}")
        if stats["removed_duplicates"] > 0:
            print(f"   🔄 Duplicates: {stats['removed_duplicates']}")
        if stats["retention_rate"] < 50:
            print(f"   ⚠️  WARNING: Only {stats['retention_rate']}% retention!")

    return cleaned
