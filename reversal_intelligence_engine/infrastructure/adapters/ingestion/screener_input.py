# ================================
# Screener Input
# ================================
#
# Primary entry point for fetching stock candidates.
# Delegates to Chartink CSV ingestion and falls back to mock data
# if no CSV files are available.

from typing import List
from domain.models.stock_dto import StockDTO
from infrastructure.adapters.ingestion.chartink_ingestion import load_from_chartink


def fetch_weekly_candidates(run_date: str = None) -> List[StockDTO]:
    """
    Primary entry point for fetching stock candidates.

    1. Tries to load real data from Chartink CSVs (run chartink_scraper.py first).
    2. Falls back to mock data if no CSVs are available (safe for dev/testing).

    Args:
        run_date: 'YYYY-MM-DD' to load a specific date's data. Defaults to today.
    """
    stocks = load_from_chartink(run_date=run_date)

    if stocks:
        return stocks

    print("[screener_input] No Chartink data found using mock fallback")
    return [
        StockDTO(symbol="ABC", price=100, volume=100000,
                 sector="Technology", industry="Software", category="Mid Cap",
                 source_table="mock"),
        StockDTO(symbol="XYZ", price=250, volume=50000,
                 sector="Finance", industry="Banking", category="Large Cap",
                 source_table="mock"),
    ]
