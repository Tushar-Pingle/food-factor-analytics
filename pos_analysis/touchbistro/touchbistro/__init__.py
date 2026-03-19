"""
pos_analysis.touchbistro
=========================
TouchBistro POS analysis pipeline for Food Factor.

Handles CSV exports from TouchBistro iPad POS:
    - TouchBistro_01_detailed_sales.csv   (master sales, one row per line item)
    - TouchBistro_02_sales_item_totals.csv (aggregated per-item summary)
    - TouchBistro_03_detailed_shift_report.csv (labor/shift data)
    - TouchBistro_04_delivery_orders.csv   (third-party delivery financials)
    - TouchBistro_05_reservations.csv      (reservation data)
    - TouchBistro_06_payments_refund_totals.csv (payment method summary)

Usage:
    from pos_analysis.touchbistro import ingest, analysis, visualizations
    from pos_analysis.touchbistro.config import RESTAURANT_NAME

    data = ingest.load_all(Path("./data"))
    sales = analysis.run_sales_analysis(data["detailed_sales"])
"""

from .ingest import load_all
from .analysis import run_sales_analysis, run_payment_analysis, run_operational_flags

__all__ = [
    "load_all",
    "run_sales_analysis",
    "run_payment_analysis",
    "run_operational_flags",
]
