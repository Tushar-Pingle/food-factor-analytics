"""
pos_analysis/square — Square for Restaurants POS Module
========================================================
Handles CSV export ingestion, sales/payment/delivery/reservation
analysis, labor optimization, and branded chart generation for
restaurants running Square for Restaurants.

Key classes:
    SquareDataLoader  — Read and normalize Square CSV exports
    SquareDataset     — Container for all normalized DataFrames
    SalesAnalyzer     — Revenue, daypart, category, order-type analysis
    PaymentAnalyzer   — Payment methods, tips, gift card usage
    DeliveryAnalyzer  — Platform comparison, margins, ratings
    ReservationAnalyzer — No-shows, turn times, RevPASH
    OperationalFlagAnalyzer — Refund/discount/void anomaly detection
    LaborAnalyzer     — Labor %, SPLH, FOH/BOH, overtime
"""

from pos_analysis.square.ingest import SquareDataLoader, SquareDataset
from pos_analysis.square.analysis import (
    SalesAnalyzer,
    PaymentAnalyzer,
    DeliveryAnalyzer,
    ReservationAnalyzer,
    OperationalFlagAnalyzer,
)
from pos_analysis.square.labor import LaborAnalyzer

__all__ = [
    "SquareDataLoader",
    "SquareDataset",
    "SalesAnalyzer",
    "PaymentAnalyzer",
    "DeliveryAnalyzer",
    "ReservationAnalyzer",
    "OperationalFlagAnalyzer",
    "LaborAnalyzer",
]
