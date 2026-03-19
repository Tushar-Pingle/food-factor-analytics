"""
pos_analysis/square/ingest.py — Square POS Data Ingestion
==========================================================
Reads Square for Restaurants CSV exports and normalizes them
into clean, analysis-ready pandas DataFrames.  Handles encoding
quirks, type coercion, missing data, and derived-column creation.

Usage::

    from pos_analysis.square.ingest import SquareDataLoader

    loader = SquareDataLoader(data_dir="/path/to/csvs")
    data   = loader.load_all()
    # data.transactions, data.items, data.timecards, …
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger("food_factor.square.ingest")

# ─────────────────────────────────────────────
# Square-specific CSV file name mapping
# ─────────────────────────────────────────────
SQUARE_FILE_MAP: Dict[str, str] = {
    "transactions":       "square_01_transactions.csv",
    "item_details":       "square_02_item_details.csv",
    "timecards":          "square_03_timecards.csv",
    "delivery_orders":    "square_04_delivery_orders.csv",
    "reservations":       "square_05_reservations.csv",
    "customer_directory": "square_06_customer_directory.csv",
}


# ─────────────────────────────────────────────
# Dataset container
# ─────────────────────────────────────────────
@dataclass
class SquareDataset:
    """Container for all normalized Square data tables."""

    transactions: pd.DataFrame
    items: pd.DataFrame
    timecards: pd.DataFrame
    delivery: pd.DataFrame
    reservations: pd.DataFrame
    customers: pd.DataFrame
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    restaurant_name: str

    def summary(self) -> Dict[str, int]:
        """Quick row-count summary for validation."""
        return {
            "transactions": len(self.transactions),
            "items":        len(self.items),
            "timecards":    len(self.timecards),
            "delivery":     len(self.delivery),
            "reservations": len(self.reservations),
            "customers":    len(self.customers),
        }


# ─────────────────────────────────────────────
# Main loader
# ─────────────────────────────────────────────
class SquareDataLoader:
    """
    Load and normalize Square POS CSV exports.

    Handles:
    - CSV encoding detection (UTF-8 with BOM, Windows line endings)
    - Decimal / currency column coercion
    - Datetime parsing with timezone awareness
    - Derived columns (daypart, day_of_week, week_number, hour)
    - Data validation and missing-value handling

    Parameters
    ----------
    data_dir : str | Path | None
        Directory containing the Square CSV files.
        Falls back to the current working directory.
    file_map : dict | None
        Override the default file-name mapping.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        file_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(".")
        self.file_map = file_map or SQUARE_FILE_MAP
        self._validate_files()

    # ─── helpers ──────────────────────────────

    def _validate_files(self) -> None:
        """Check that all expected CSV files exist."""
        missing = [
            f"{key}: {self.data_dir / fname}"
            for key, fname in self.file_map.items()
            if not (self.data_dir / fname).exists()
        ]
        if missing:
            raise FileNotFoundError(
                "Missing Square CSV exports:\n" + "\n".join(missing)
            )
        logger.info(
            "All %d Square CSV files found in %s",
            len(self.file_map), self.data_dir,
        )

    def _read_csv(self, key: str) -> pd.DataFrame:
        """Read a CSV with encoding fallback and Windows line-ending handling."""
        fpath = self.data_dir / self.file_map[key]
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                df = pd.read_csv(fpath, encoding=enc)
                logger.info("Loaded %s: %d rows (%s)", key, len(df), enc)
                return df
            except UnicodeDecodeError:
                continue
        raise ValueError(
            f"Could not decode {fpath} with any supported encoding"
        )

    @staticmethod
    def _classify_daypart(hour: int) -> str:
        """Classify an hour into a daypart per config definitions."""
        for daypart, (start, end) in settings.DAYPARTS.items():
            if start <= hour < end:
                return daypart
        return "Late Night"

    # ─── table loaders ────────────────────────

    def load_transactions(self) -> pd.DataFrame:
        """
        Load and normalize payment-level transaction data.

        Derived columns added:
            hour, daypart, day_of_week, week_number, date_only, is_refund
        """
        df = self._read_csv("transactions")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        money_cols = [
            "gross_sales", "discounts", "net_sales", "tax", "tip",
            "total_collected", "fees", "net_total", "cash_rounding",
        ]
        for col in money_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(r"[\$,]", "", regex=True),
                    errors="coerce",
                ).fillna(0.0)

        df["hour"]        = df["date"].dt.hour
        df["daypart"]     = df["hour"].apply(self._classify_daypart)
        df["day_of_week"] = df["date"].dt.day_name()
        df["week_number"] = df["date"].dt.isocalendar().week.astype(int)
        df["date_only"]   = df["date"].dt.date
        df["is_refund"]   = df["event_type"].str.lower() == "refund"

        for col in ("customer_name", "customer_id", "payment_method", "order_type"):
            if col in df.columns:
                df[col] = df[col].fillna("").str.strip()

        return df

    def load_items(self) -> pd.DataFrame:
        """
        Load and normalize line-item sales data.

        Derived columns added:
            contribution_margin, margin_pct, food_cost_pct,
            hour, daypart, day_of_week, date_only
        """
        df = self._read_csv("item_details")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        money_cols = [
            "unit_price", "gross_sales", "discounts", "net_sales",
            "tax", "modifier_amount", "cost",
        ]
        for col in money_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(r"[\$,]", "", regex=True),
                    errors="coerce",
                ).fillna(0.0)

        df["quantity"] = (
            pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
        )

        df["contribution_margin"] = df["net_sales"] - df["cost"]
        df["margin_pct"] = np.where(
            df["net_sales"] > 0,
            df["contribution_margin"] / df["net_sales"],
            0.0,
        )
        df["food_cost_pct"] = np.where(
            df["net_sales"] > 0, df["cost"] / df["net_sales"], 0.0,
        )

        df["hour"]        = df["date"].dt.hour
        df["daypart"]     = df["hour"].apply(self._classify_daypart)
        df["day_of_week"] = df["date"].dt.day_name()
        df["date_only"]   = df["date"].dt.date

        for col in ("item_name", "category", "reporting_category", "modifiers"):
            if col in df.columns:
                df[col] = df[col].fillna("").str.strip()

        return df

    def load_timecards(self) -> pd.DataFrame:
        """
        Load and normalize labor / timecard data.

        Derived columns added:
            day_of_week, week_number, date_only, is_foh
        """
        df = self._read_csv("timecards")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ("clock_in", "clock_out", "break_start", "break_end"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        numeric_cols = [
            "total_hours", "paid_hours", "regular_hours", "overtime_hours",
            "hourly_rate", "labor_cost", "declared_cash_tips",
            "pooled_tips_by_transaction",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        if "pooled_tips_by_transaction" in df.columns:
            df.rename(
                columns={"pooled_tips_by_transaction": "pooled_tips"},
                inplace=True,
            )

        df["day_of_week"] = df["date"].dt.day_name()
        df["week_number"] = df["date"].dt.isocalendar().week.astype(int)
        df["date_only"]   = df["date"].dt.date

        foh_titles = {"Server", "Host", "Bartender", "Busser"}
        df["is_foh"] = df["job_title"].isin(foh_titles)

        return df

    def load_delivery(self) -> pd.DataFrame:
        """
        Load and normalize delivery-platform order data.

        Derived columns added:
            day_of_week, hour, date_only, is_canceled,
            effective_margin_pct, total_platform_fees
        """
        df = self._read_csv("delivery_orders")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        df["order_date"]  = pd.to_datetime(df["order_date"], errors="coerce")
        df["payout_date"] = pd.to_datetime(df["payout_date"], errors="coerce")

        money_cols = [
            "gross_sales", "tax", "gst", "pst", "tip", "commission_amount",
            "marketing_fee", "promo_cost_restaurant", "promo_cost_platform",
            "service_fee", "adjustments", "net_payout",
        ]
        for col in money_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        for col in (
            "commission_rate", "item_count",
            "prep_time_minutes", "delivery_time_minutes", "customer_rating",
        ):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["day_of_week"]        = df["order_date"].dt.day_name()
        df["hour"]               = df["order_date"].dt.hour
        df["date_only"]          = df["order_date"].dt.date
        df["is_canceled"]        = df["order_status"].str.lower() == "canceled"
        df["effective_margin_pct"] = np.where(
            df["gross_sales"] > 0, df["net_payout"] / df["gross_sales"], 0.0,
        )
        df["total_platform_fees"] = (
            df["commission_amount"].abs()
            + df["marketing_fee"].abs()
            + df["service_fee"].abs()
            + df["promo_cost_restaurant"].abs()
        )

        return df

    def load_reservations(self) -> pd.DataFrame:
        """
        Load and normalize reservation data.

        Derived columns added:
            day_of_week, date_only, hour, is_noshow,
            is_completed, is_canceled, total_covers
        """
        df = self._read_csv("reservations")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ("reservation_time", "booked_at", "seated_time", "departed_time"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in ("party_size", "lead_time_days", "turn_time_minutes", "wait_time_minutes"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["day_of_week"]  = df["date"].dt.day_name()
        df["date_only"]    = df["date"].dt.date
        df["hour"]         = df["reservation_time"].dt.hour
        df["is_noshow"]    = df["status"].str.lower() == "no-show"
        df["is_completed"] = df["status"].str.lower() == "completed"
        df["is_canceled"]  = df["status"].str.lower().isin(["canceled", "late cancel"])
        df["total_covers"] = np.where(df["is_completed"], df["party_size"], 0)

        return df

    def load_customers(self) -> pd.DataFrame:
        """
        Load and normalize customer directory data.

        Derived columns added:
            avg_spend_per_visit, full_name
        """
        df = self._read_csv("customer_directory")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
        df["last_visit"]   = pd.to_datetime(df["last_visit"], errors="coerce")

        for col in ("total_visits", "loyalty_points"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        df["total_spend"] = pd.to_numeric(df["total_spend"], errors="coerce").fillna(0.0)

        df["avg_spend_per_visit"] = np.where(
            df["total_visits"] > 0,
            df["total_spend"] / df["total_visits"],
            0.0,
        )
        df["full_name"] = (
            df["first_name"].fillna("") + " " + df["last_name"].fillna("")
        ).str.strip()

        return df

    # ─── orchestrator ─────────────────────────

    def load_all(self) -> SquareDataset:
        """
        Load and normalize every Square CSV export.

        Returns
        -------
        SquareDataset
            Container with all six normalized DataFrames plus metadata.
        """
        logger.info("Loading all Square data from %s", self.data_dir)

        dataset = SquareDataset(
            transactions=self.load_transactions(),
            items=self.load_items(),
            timecards=self.load_timecards(),
            delivery=self.load_delivery(),
            reservations=self.load_reservations(),
            customers=self.load_customers(),
            period_start=pd.Timestamp(settings.REPORT_PERIOD_START),
            period_end=pd.Timestamp(settings.REPORT_PERIOD_END),
            restaurant_name=settings.RESTAURANT_NAME,
        )

        logger.info("Dataset loaded: %s", dataset.summary())
        return dataset
