"""
pos_analysis.touchbistro.ingest
================================
Data ingestion and normalization for TouchBistro CSV exports.

Reads raw CSVs, cleans data types, adds derived columns (daypart, hour,
weekday), and returns standardized pandas DataFrames ready for analysis.

Loaders:
    - load_detailed_sales()  → TouchBistro_01 (master sales, one row per line item)
    - load_item_totals()     → TouchBistro_02 (aggregated per-item summary)
    - load_shifts()          → TouchBistro_03 (labor/shift data)
    - load_delivery()        → TouchBistro_04 (third-party delivery financials)
    - load_reservations()    → TouchBistro_05 (reservation data)
    - load_payments()        → TouchBistro_06 (payment method summary)
    - load_all()             → Master loader returning dict of all DataFrames

Each loader returns a clean DataFrame. The master load_all() function
returns a dict of all DataFrames for downstream modules.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from .config import (
    FILE_MAP,
    DATA_DIR,
    DAYPARTS,
    DATE_START,
    DATE_END,
    GST_RATE,
    PST_RATE_ALCOHOL,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _assign_daypart(hour: int) -> str:
    """Map hour (0–23) to daypart label from config.DAYPARTS."""
    for label, start, end in DAYPARTS:
        if end > 24:
            # handles late-night wrap (e.g. 22–26 means 22–23 + 0–1)
            if hour >= start or hour < (end - 24):
                return label
        elif start <= hour < end:
            return label
    return "Other"


def _parse_hours_worked(val) -> float:
    """Convert 'H:MM' or 'HH:MM' string to decimal hours."""
    if pd.isna(val) or val == "":
        return 0.0
    try:
        parts = str(val).split(":")
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return hours + minutes / 60.0
    except (ValueError, IndexError):
        logger.warning(f"Could not parse hours_worked value: {val}")
        return 0.0


# ──────────────────────────────────────────────
# 1. DETAILED SALES (TouchBistro_01)
# ──────────────────────────────────────────────

def load_detailed_sales(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Load TouchBistro_01_detailed_sales.csv — the master sales export.
    One row per line item per bill.

    Derived columns added:
        datetime, hour, weekday, weekday_name, daypart, is_void, is_return

    Args:
        data_dir: Directory containing the CSV file.

    Returns:
        Cleaned DataFrame with derived columns, filtered to analysis window.
    """
    filepath = data_dir / FILE_MAP["detailed_sales"]
    logger.info(f"Loading detailed sales from {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    # ---- Type coercion ----
    df["Date"] = pd.to_datetime(df["Date"], format="mixed")
    df["Time"] = df["Time"].astype(str)
    df["datetime"] = pd.to_datetime(
        df["Date"].dt.strftime("%Y-%m-%d") + " " + df["Time"],
        format="mixed",
        errors="coerce",
    )

    numeric_cols = [
        "Quantity", "Price", "Gross_Sales", "Discount_Amount", "Net_Sales",
        "Modifier_Amount", "Tax_1_Amount", "Tax_2_Amount", "Total_Tax",
        "Tip", "Auto_Gratuity",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # ---- Boolean flags ----
    df["is_void"] = df["Is_Void"].str.strip().str.lower() == "yes"
    df["is_return"] = df["Is_Return"].str.strip().str.lower() == "yes"

    # ---- Derived time features ----
    df["hour"] = df["datetime"].dt.hour
    df["weekday"] = df["datetime"].dt.weekday  # 0=Mon … 6=Sun
    df["weekday_name"] = df["datetime"].dt.day_name()
    df["daypart"] = df["hour"].apply(_assign_daypart)

    # ---- Fill blanks ----
    df["Section"] = df["Section"].fillna("Unknown")
    df["Table"] = df["Table"].fillna("")
    df["Discount_Name"] = df["Discount_Name"].fillna("")
    df["Modifiers"] = df["Modifiers"].fillna("")
    df["Notes"] = df["Notes"].fillna("")
    df["Payment_Method"] = df["Payment_Method"].fillna("Unknown")

    # ---- Filter to analysis window ----
    mask = (df["Date"] >= DATE_START) & (df["Date"] <= DATE_END)
    df = df.loc[mask].copy()

    logger.info(
        f"Loaded {len(df):,} line items across "
        f"{df['Bill_Number'].nunique():,} bills"
    )
    return df


# ──────────────────────────────────────────────
# 2. SALES ITEM TOTALS (TouchBistro_02)
# ──────────────────────────────────────────────

def load_item_totals(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Load TouchBistro_02_sales_item_totals.csv — aggregated per-item summary.
    Used for menu engineering (stars/plowhorses/puzzles/dogs).

    Derived columns added:
        food_cost_pct (float), contribution_margin, total_contribution_margin

    Args:
        data_dir: Directory containing the CSV file.

    Returns:
        Cleaned DataFrame with margin calculations.
    """
    filepath = data_dir / FILE_MAP["item_totals"]
    logger.info(f"Loading item totals from {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    numeric_cols = [
        "Quantity_Sold", "Gross_Sales", "Returns", "Return_Amount",
        "Voids", "Net_Sales", "Item_Cost", "Total_Cost",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Parse Food_Cost_Pct from "30.1%" string → 0.301 float
    df["food_cost_pct"] = (
        df["Food_Cost_Pct"]
        .str.replace("%", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .div(100)
        .fillna(0.0)
    )

    # Contribution margin per unit = unit revenue – cost
    df["contribution_margin"] = (
        df["Net_Sales"] / df["Quantity_Sold"].replace(0, np.nan)
    ) - df["Item_Cost"]
    df["contribution_margin"] = df["contribution_margin"].fillna(0.0)

    # Total contribution margin
    df["total_contribution_margin"] = df["contribution_margin"] * df["Quantity_Sold"]

    logger.info(f"Loaded {len(df)} menu items")
    return df


# ──────────────────────────────────────────────
# 3. SHIFTS / LABOR (TouchBistro_03)
# ──────────────────────────────────────────────

def load_shifts(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Load TouchBistro_03_detailed_shift_report.csv — labor data.
    One row per clock-in event.

    Derived columns added:
        hours_decimal, total_tips, weekday, weekday_name, clock_in_hour

    Args:
        data_dir: Directory containing the CSV file.

    Returns:
        Cleaned DataFrame ready for labor analysis.
    """
    filepath = data_dir / FILE_MAP["shifts"]
    logger.info(f"Loading shift data from {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    # Parse datetimes
    for col in ["Clock_In", "Clock_Out", "Break_Start", "Break_End"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["Date"] = pd.to_datetime(df["Date"], format="mixed")

    # Parse hours
    df["hours_decimal"] = df["Hours_Worked"].apply(_parse_hours_worked)

    # Numeric cols
    for col in ["Hourly_Rate", "Pay", "Cash_Tips", "Credit_Card_Tips"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Derived
    df["total_tips"] = df["Cash_Tips"] + df["Credit_Card_Tips"]
    df["weekday"] = df["Date"].dt.weekday
    df["weekday_name"] = df["Date"].dt.day_name()
    df["clock_in_hour"] = df["Clock_In"].dt.hour

    # Filter to analysis window
    mask = (df["Date"] >= DATE_START) & (df["Date"] <= DATE_END)
    df = df.loc[mask].copy()

    logger.info(
        f"Loaded {len(df)} shift records for "
        f"{df['Staff_Member'].nunique()} staff members"
    )
    return df


# ──────────────────────────────────────────────
# 4. DELIVERY ORDERS (TouchBistro_04)
# ──────────────────────────────────────────────

def load_delivery(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Load TouchBistro_04_delivery_orders.csv — third-party delivery data.
    One row per delivery order (Uber Eats / DoorDash).

    Derived columns added:
        is_canceled, date, hour, weekday, weekday_name, effective_commission_pct

    Args:
        data_dir: Directory containing the CSV file.

    Returns:
        Cleaned DataFrame with delivery financials.
    """
    filepath = data_dir / FILE_MAP["delivery"]
    logger.info(f"Loading delivery orders from {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Payout_Date"] = pd.to_datetime(df["Payout_Date"], errors="coerce")

    numeric_cols = [
        "Gross_Sales", "Tax", "GST", "PST", "Tip",
        "Commission_Amount", "Commission_Rate",
        "Marketing_Fee", "Promo_Cost_Restaurant", "Promo_Cost_Platform",
        "Service_Fee", "Adjustments", "Net_Payout",
        "Item_Count", "Prep_Time_Minutes", "Delivery_Time_Minutes",
        "Customer_Rating",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["is_canceled"] = df["Order_Status"].str.strip().str.lower() == "canceled"
    df["date"] = df["Order_Date"].dt.date
    df["hour"] = df["Order_Date"].dt.hour
    df["weekday"] = df["Order_Date"].dt.weekday
    df["weekday_name"] = df["Order_Date"].dt.day_name()

    # Effective commission: all fees as pct of gross
    completed = df[~df["is_canceled"]].copy()
    total_fees = (
        completed["Commission_Amount"].abs()
        + completed["Marketing_Fee"].abs()
        + completed["Service_Fee"].abs()
    )
    df.loc[~df["is_canceled"], "effective_commission_pct"] = (
        total_fees / completed["Gross_Sales"].replace(0, np.nan) * 100
    )

    logger.info(
        f"Loaded {len(df)} delivery orders "
        f"({df['is_canceled'].sum()} canceled)"
    )
    return df


# ──────────────────────────────────────────────
# 5. RESERVATIONS (TouchBistro_05)
# ──────────────────────────────────────────────

def load_reservations(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Load TouchBistro_05_reservations.csv — reservation data.
    One row per reservation.

    Derived columns added:
        is_noshow, is_completed, is_canceled, is_late_cancel,
        weekday, weekday_name, reservation_hour

    Args:
        data_dir: Directory containing the CSV file.

    Returns:
        Cleaned DataFrame for reservation/capacity analysis.
    """
    filepath = data_dir / FILE_MAP["reservations"]
    logger.info(f"Loading reservations from {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    df["Date"] = pd.to_datetime(df["Date"], format="mixed")
    for col in ["Reservation_Time", "Booked_At", "Seated_Time", "Departed_Time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        "Party_Size", "Lead_Time_Days", "Turn_Time_Minutes", "Wait_Time_Minutes",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Status flags
    status_lower = df["Status"].str.strip().str.lower()
    df["is_completed"] = status_lower == "completed"
    df["is_noshow"] = status_lower == "no-show"
    df["is_canceled"] = status_lower == "canceled"
    df["is_late_cancel"] = status_lower == "late cancel"

    df["weekday"] = df["Date"].dt.weekday
    df["weekday_name"] = df["Date"].dt.day_name()
    df["reservation_hour"] = df["Reservation_Time"].dt.hour

    # Filter to window
    mask = (df["Date"] >= DATE_START) & (df["Date"] <= DATE_END)
    df = df.loc[mask].copy()

    logger.info(
        f"Loaded {len(df)} reservations "
        f"(no-show: {df['is_noshow'].sum()}, "
        f"canceled: {df['is_canceled'].sum()})"
    )
    return df


# ──────────────────────────────────────────────
# 6. PAYMENT SUMMARY (TouchBistro_06)
# ──────────────────────────────────────────────

def load_payments(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Load TouchBistro_06_payments_refund_totals.csv — payment method summary.
    One row per payment method (aggregated over full period).

    Derived columns added:
        pct_of_total, avg_transaction

    Args:
        data_dir: Directory containing the CSV file.

    Returns:
        Cleaned DataFrame with payment method breakdowns.
    """
    filepath = data_dir / FILE_MAP["payments"]
    logger.info(f"Loading payment summary from {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")

    for col in ["Total_Amount", "Tips", "Refunds", "Transaction_Count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    total = df["Total_Amount"].sum()
    df["pct_of_total"] = (
        (df["Total_Amount"] / total * 100).round(1) if total > 0 else 0
    )
    df["avg_transaction"] = (
        df["Total_Amount"] / df["Transaction_Count"].replace(0, np.nan)
    ).round(2)

    logger.info(f"Loaded {len(df)} payment methods — total: ${total:,.2f}")
    return df


# ──────────────────────────────────────────────
# MASTER LOADER
# ──────────────────────────────────────────────

def load_all(data_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all TouchBistro data files into a single dict of DataFrames.

    Args:
        data_dir: Path to directory containing CSV files.
                  Defaults to config.DATA_DIR.

    Returns:
        Dict with keys: detailed_sales, item_totals, shifts,
        delivery, reservations, payments
    """
    if data_dir is None:
        data_dir = DATA_DIR

    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    data: Dict[str, pd.DataFrame] = {}

    loaders = {
        "detailed_sales": load_detailed_sales,
        "item_totals":    load_item_totals,
        "shifts":         load_shifts,
        "delivery":       load_delivery,
        "reservations":   load_reservations,
        "payments":       load_payments,
    }

    for key, loader_fn in loaders.items():
        try:
            data[key] = loader_fn(data_dir)
        except FileNotFoundError:
            logger.warning(
                f"File not found for '{key}' — skipping. "
                f"Expected: {FILE_MAP[key]}"
            )
            data[key] = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading '{key}': {e}")
            data[key] = pd.DataFrame()

    return data
