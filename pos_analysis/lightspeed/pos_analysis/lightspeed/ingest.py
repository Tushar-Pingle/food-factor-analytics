"""
pos_analysis.lightspeed.ingest — Lightspeed Data Ingestion & Normalization

Reads all 9 Lightspeed CSV exports, validates schemas, handles missing
data, and returns standardized pandas DataFrames ready for analysis.

Also provides analytical join builders:
    build_item_sales_view() — enriched item-level sales with receipt context + COGS
    build_daily_summary()   — daily revenue + labor KPIs
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import logging

from pos_analysis.lightspeed import FILE_PATHS
from pos_analysis.shared import DAYPARTS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# SCHEMA DEFINITIONS — expected columns per file
# ─────────────────────────────────────────────

SCHEMAS: Dict[str, list] = {
    "receipts": [
        "Receipt_ID", "Sequence_Number", "Creation_Date", "Finalized_Date",
        "Status", "Type", "Void_Status", "Table_ID", "Table_Name",
        "Floor_ID", "Floor_Name", "User_ID", "Username", "Customer_ID",
        "Number_of_Seats", "Net_Total", "Total", "Tip",
    ],
    "receipt_items": [
        "Receipt_ID", "Creation_Date", "Created_By", "Product_ID",
        "Item_Name", "Tax_Exclusive_Price", "Tax_Inclusive_Price", "Amount",
        "Tax_Percentage", "Tax_Amount", "Total_Price", "Total_Tax_Excl_Price",
        "Category", "Category_Type", "Seat_Number", "Course_Number",
    ],
    "modifiers": [
        "receipt_id", "item_name", "product_id", "mod_id", "mod_name",
        "mod_price_incl", "mod_price_excl",
    ],
    "payments": [
        "Receipt_ID", "Payment_ID", "Created_Date", "Payment_Name",
        "Payment_Type", "Amount", "Tip", "Customer_ID",
    ],
    "labor_shifts": [
        "Shift_ID", "User_ID", "Employee_Name", "Role", "User_Group",
        "Date", "Clock_In", "Clock_Out", "Total_Hours", "Paid_Hours",
        "Regular_Hours", "Overtime_Hours", "Hourly_Rate", "Labor_Cost",
    ],
    "products": [
        "Product_ID", "Name", "Price", "Category_Name", "Tax_Rate",
        "Delivery_Price", "Tax_Exclusive_Price", "Cost",
    ],
    "delivery": [
        "Platform", "Order_ID", "Order_Date", "Order_Status", "Gross_Sales",
        "Tax", "Commission_Amount", "Commission_Rate", "Net_Payout",
        "Item_Count", "Customer_Type", "Prep_Time_Minutes",
    ],
    "reservations": [
        "Reservation_ID", "Date", "Reservation_Time", "Party_Size",
        "Service", "Source", "Status", "Turn_Time_Minutes",
        "Wait_Time_Minutes", "Server_Assigned",
    ],
    "customers": [
        "Customer_ID", "First_Name", "Last_Name", "Email",
        "Total_Visits", "Total_Spend", "Last_Visit", "Groups",
    ],
}


def _validate_schema(df: pd.DataFrame, name: str) -> bool:
    """Check that required columns exist in the DataFrame."""
    required = SCHEMAS.get(name, [])
    missing = [col for col in required if col not in df.columns]
    if missing:
        logger.warning(f"[{name}] Missing expected columns: {missing}")
        return False
    return True


def _assign_daypart(row) -> str:
    """Assign daypart based on hour and day of week."""
    hour = row["hour"]
    dow = row["day_of_week"]

    if dow == "Sunday" and 10 <= hour < 14:
        return "Brunch"
    if 11 <= hour < 15:
        return "Lunch"
    if 15 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 22:
        return "Dinner"
    if hour >= 22 or hour < 6:
        return "Late Night"
    return "Other"


# ─────────────────────────────────────────────
# INDIVIDUAL FILE LOADERS
# ─────────────────────────────────────────────

def load_receipts(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load and normalize Lightspeed_01_receipts.csv.

    Returns DataFrame with parsed datetimes, numeric totals,
    and derived columns: date, hour, day_of_week, daypart, is_voided.
    """
    fp = filepath or FILE_PATHS["receipts"]
    df = pd.read_csv(fp)
    _validate_schema(df, "receipts")

    for col in ["Creation_Date", "Finalized_Date", "Delivery_Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["Net_Total", "Total", "Tip", "Number_of_Seats", "Sequence_Number"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["date"] = df["Creation_Date"].dt.date
    df["hour"] = df["Creation_Date"].dt.hour
    df["day_of_week"] = df["Creation_Date"].dt.day_name()
    df["week_number"] = df["Creation_Date"].dt.isocalendar().week.astype(int)
    df["is_voided"] = df["Void_Status"].fillna("").str.strip().str.lower() == "voided"
    df["daypart"] = df.apply(_assign_daypart, axis=1)

    mask = (~df["is_voided"]) & (df["Net_Total"] > 0)
    df["tip_pct"] = np.where(mask, df["Tip"] / df["Net_Total"], 0)

    logger.info(f"Loaded {len(df)} receipts ({df['is_voided'].sum()} voided)")
    return df


def load_receipt_items(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load and normalize Lightspeed_02_receipt_items.csv.

    Returns DataFrame with parsed datetimes, numeric prices,
    and clean category fields.
    """
    fp = filepath or FILE_PATHS["receipt_items"]
    df = pd.read_csv(fp)
    _validate_schema(df, "receipt_items")

    df["Creation_Date"] = pd.to_datetime(df["Creation_Date"], errors="coerce")

    numeric_cols = [
        "Tax_Exclusive_Price", "Tax_Inclusive_Price", "Amount",
        "Tax_Percentage", "Tax_Amount", "Total_Price",
        "Total_Tax_Excl_Price", "Seat_Number", "Course_Number",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Category"] = df["Category"].fillna("Unknown").str.strip()
    df["Category_Type"] = df["Category_Type"].fillna("Unknown").str.strip()

    logger.info(f"Loaded {len(df)} receipt items across {df['Category'].nunique()} categories")
    return df


def load_modifiers(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load and normalize Lightspeed_03_modifiers.csv."""
    fp = filepath or FILE_PATHS["modifiers"]
    df = pd.read_csv(fp)
    _validate_schema(df, "modifiers")

    for col in ["mod_price_incl", "mod_price_excl"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    logger.info(f"Loaded {len(df)} modifier applications across {df['mod_name'].nunique()} modifier types")
    return df


def load_payments(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load and normalize Lightspeed_04_payments.csv."""
    fp = filepath or FILE_PATHS["payments"]
    df = pd.read_csv(fp)
    _validate_schema(df, "payments")

    df["Created_Date"] = pd.to_datetime(df["Created_Date"], errors="coerce")

    for col in ["Amount", "Tip"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Payment_Name"] = df["Payment_Name"].fillna("Unknown").str.strip()
    df["Payment_Type"] = df["Payment_Type"].fillna("Unknown").str.strip()

    logger.info(f"Loaded {len(df)} payments — methods: {df['Payment_Name'].nunique()}")
    return df


def load_labor_shifts(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load and normalize Lightspeed_05_labor_shifts.csv.

    Returns DataFrame with parsed datetimes and numeric hour/cost columns.
    """
    fp = filepath or FILE_PATHS["labor_shifts"]
    df = pd.read_csv(fp)
    _validate_schema(df, "labor_shifts")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Clock_In", "Clock_Out", "Break_Start", "Break_End"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        "Total_Hours", "Paid_Hours", "Regular_Hours", "Overtime_Hours",
        "Hourly_Rate", "Labor_Cost", "Declared_Cash_Tips", "Pooled_Tips",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["day_of_week"] = df["Date"].dt.day_name()
    df["User_Group"] = df["User_Group"].fillna("Unknown").str.strip()
    df["Role"] = df["Role"].fillna("Unknown").str.strip()

    logger.info(
        f"Loaded {len(df)} shifts — "
        f"FOH: {(df['User_Group']=='FOH').sum()}, "
        f"BOH: {(df['User_Group']=='BOH').sum()}"
    )
    return df


def load_products(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load and normalize Lightspeed_06_products.csv (menu catalog with COGS).

    Computes food_cost_pct and contribution_margin per item.
    """
    fp = filepath or FILE_PATHS["products"]
    df = pd.read_csv(fp)
    _validate_schema(df, "products")

    numeric_cols = [
        "Price", "Tax_Rate", "Takeaway_Price", "Delivery_Price",
        "Tax_Exclusive_Price", "Cost",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["food_cost_pct"] = np.where(df["Price"] > 0, df["Cost"] / df["Price"], 0)
    df["contribution_margin"] = df["Price"] - df["Cost"]
    df["has_delivery"] = df["Delivery_Price"] > 0

    logger.info(f"Loaded {len(df)} products — avg food cost: {df['food_cost_pct'].mean():.1%}")
    return df


def load_delivery(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load and normalize Lightspeed_07_delivery_orders.csv."""
    fp = filepath or FILE_PATHS["delivery"]
    df = pd.read_csv(fp)
    _validate_schema(df, "delivery")

    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Payout_Date"] = pd.to_datetime(df.get("Payout_Date"), errors="coerce")

    numeric_cols = [
        "Gross_Sales", "Tax", "GST", "PST", "Tip", "Commission_Amount",
        "Commission_Rate", "Marketing_Fee", "Promo_Cost_Restaurant",
        "Service_Fee", "Adjustments", "Net_Payout", "Item_Count",
        "Prep_Time_Minutes", "Delivery_Time_Minutes", "Customer_Rating",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["date"] = df["Order_Date"].dt.date
    df["hour"] = df["Order_Date"].dt.hour
    df["day_of_week"] = df["Order_Date"].dt.day_name()
    df["is_completed"] = df["Order_Status"].str.lower() == "completed"
    df["effective_commission_pct"] = np.where(
        df["Gross_Sales"] > 0,
        df["Commission_Amount"].abs() / df["Gross_Sales"],
        0,
    )

    logger.info(
        f"Loaded {len(df)} delivery orders — "
        f"completed: {df['is_completed'].sum()}, "
        f"canceled: {(~df['is_completed']).sum()}"
    )
    return df


def load_reservations(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load and normalize Lightspeed_08_reservations.csv."""
    fp = filepath or FILE_PATHS["reservations"]
    df = pd.read_csv(fp)
    _validate_schema(df, "reservations")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Reservation_Time", "Booked_At", "Seated_Time", "Departed_Time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        "Party_Size", "Lead_Time_Days", "Turn_Time_Minutes", "Wait_Time_Minutes",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["day_of_week"] = df["Date"].dt.day_name()
    df["hour"] = df["Reservation_Time"].dt.hour
    df["Status"] = df["Status"].fillna("Unknown").str.strip()
    df["Source"] = df["Source"].fillna("Unknown").str.strip()

    logger.info(
        f"Loaded {len(df)} reservations — "
        f"no-shows: {(df['Status']=='No-Show').sum()}, "
        f"completed: {(df['Status']=='Completed').sum()}"
    )
    return df


def load_customers(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load and normalize Lightspeed_09_customer_directory.csv."""
    fp = filepath or FILE_PATHS["customers"]
    df = pd.read_csv(fp)
    _validate_schema(df, "customers")

    df["Last_Visit"] = pd.to_datetime(df["Last_Visit"], errors="coerce")
    df["Created_Date"] = pd.to_datetime(df["Created_Date"], errors="coerce")

    for col in ["Total_Visits", "Total_Spend", "Loyalty_Points"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["avg_spend_per_visit"] = np.where(
        df["Total_Visits"] > 0,
        df["Total_Spend"] / df["Total_Visits"],
        0,
    )

    logger.info(f"Loaded {len(df)} customers — VIP: {(df['Groups'].str.contains('VIP', na=False)).sum()}")
    return df


# ─────────────────────────────────────────────
# MASTER LOADER
# ─────────────────────────────────────────────

def load_all(data_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all 9 Lightspeed data files and return as a dictionary.

    Args:
        data_dir: Override directory for CSV files.

    Returns:
        Dict mapping file keys to normalized DataFrames.
        Keys: receipts, receipt_items, modifiers, payments,
              labor_shifts, products, delivery, reservations, customers.
    """
    if data_dir:
        paths = {k: data_dir / v.name for k, v in FILE_PATHS.items()}
    else:
        paths = FILE_PATHS

    datasets: Dict[str, pd.DataFrame] = {}
    loaders = {
        "receipts":       (load_receipts,       paths["receipts"]),
        "receipt_items":  (load_receipt_items,   paths["receipt_items"]),
        "modifiers":      (load_modifiers,       paths["modifiers"]),
        "payments":       (load_payments,        paths["payments"]),
        "labor_shifts":   (load_labor_shifts,    paths["labor_shifts"]),
        "products":       (load_products,        paths["products"]),
        "delivery":       (load_delivery,        paths["delivery"]),
        "reservations":   (load_reservations,    paths["reservations"]),
        "customers":      (load_customers,       paths["customers"]),
    }

    for key, (loader_fn, filepath) in loaders.items():
        try:
            datasets[key] = loader_fn(filepath)
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath} — skipping {key}")
            datasets[key] = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading {key} from {filepath}: {e}")
            datasets[key] = pd.DataFrame()

    logger.info(f"Loaded {sum(len(v) for v in datasets.values())} total rows across {len(datasets)} files")
    return datasets


# ─────────────────────────────────────────────
# JOINED VIEWS — Common analytical joins
# ─────────────────────────────────────────────

def build_item_sales_view(
    receipts: pd.DataFrame,
    items: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build enriched item-level sales view by joining receipt items
    with receipt metadata and product catalog (COGS).

    Returns one row per item sold with receipt context + cost data.
    """
    r = receipts[~receipts["is_voided"]][
        ["Receipt_ID", "date", "hour", "day_of_week", "daypart",
         "Type", "Floor_Name", "Username", "Number_of_Seats"]
    ].copy()

    merged = items.merge(r, on="Receipt_ID", how="inner")

    prod = products[["Product_ID", "Cost", "food_cost_pct", "contribution_margin"]].copy()
    merged = merged.merge(prod, on="Product_ID", how="left")

    merged["Cost"] = merged["Cost"].fillna(0)
    merged["food_cost_pct"] = merged["food_cost_pct"].fillna(0)
    merged["contribution_margin"] = merged["contribution_margin"].fillna(
        merged["Tax_Exclusive_Price"]
    )

    logger.info(f"Built item sales view: {len(merged)} rows")
    return merged


def build_daily_summary(
    receipts: pd.DataFrame,
    labor: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a daily summary joining POS revenue with labor cost.

    Returns one row per date with revenue, covers, labor, and derived KPIs.
    """
    valid = receipts[~receipts["is_voided"]].copy()

    daily_rev = valid.groupby("date").agg(
        net_revenue=("Net_Total", "sum"),
        total_with_tax=("Total", "sum"),
        total_tips=("Tip", "sum"),
        transaction_count=("Receipt_ID", "nunique"),
        total_covers=("Number_of_Seats", "sum"),
    ).reset_index()

    daily_rev["avg_check"] = daily_rev["net_revenue"] / daily_rev["transaction_count"].clip(lower=1)
    daily_rev["rev_per_cover"] = np.where(
        daily_rev["total_covers"] > 0,
        daily_rev["net_revenue"] / daily_rev["total_covers"],
        0,
    )

    daily_labor = labor.groupby(labor["Date"].dt.date).agg(
        total_labor_cost=("Labor_Cost", "sum"),
        total_labor_hours=("Paid_Hours", "sum"),
        foh_labor_cost=("Labor_Cost", lambda x: x[labor.loc[x.index, "User_Group"] == "FOH"].sum()),
        boh_labor_cost=("Labor_Cost", lambda x: x[labor.loc[x.index, "User_Group"] == "BOH"].sum()),
        foh_hours=("Paid_Hours", lambda x: x[labor.loc[x.index, "User_Group"] == "FOH"].sum()),
        boh_hours=("Paid_Hours", lambda x: x[labor.loc[x.index, "User_Group"] == "BOH"].sum()),
        overtime_hours=("Overtime_Hours", "sum"),
        shift_count=("Shift_ID", "nunique"),
    ).reset_index()
    daily_labor.rename(columns={"Date": "date"}, inplace=True)

    daily = daily_rev.merge(daily_labor, on="date", how="left")
    daily["total_labor_cost"] = daily["total_labor_cost"].fillna(0)
    daily["total_labor_hours"] = daily["total_labor_hours"].fillna(0)

    daily["labor_pct"] = np.where(
        daily["net_revenue"] > 0,
        daily["total_labor_cost"] / daily["net_revenue"],
        0,
    )
    daily["splh"] = np.where(
        daily["total_labor_hours"] > 0,
        daily["net_revenue"] / daily["total_labor_hours"],
        0,
    )
    daily["day_of_week"] = pd.to_datetime(daily["date"]).dt.day_name()

    logger.info(f"Built daily summary: {len(daily)} days")
    return daily
