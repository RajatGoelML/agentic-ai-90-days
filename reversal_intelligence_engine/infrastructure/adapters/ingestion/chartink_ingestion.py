# -----------------------------------------------------------------------------
# Chartink Ingestion - reads manually placed (or scraped) CSVs from
#   data/inputs/chartink/<YYYY-MM-DD>/*.csv  ->  List[StockDTO]
# -----------------------------------------------------------------------------

import csv
import os
from datetime import date
from pathlib import Path
from typing import List

from domain.models.stock_dto import StockDTO

# -- known column-name variants ------------------------------------------------
SYMBOL_KEYS = {"symbol", "nsecode", "nse code", "ticker", "stock", "scrip code"}
PRICE_KEYS  = {"ltp", "close", "price", "last price", "current price", "close price"}
VOLUME_KEYS = {"volume", "vol"}
SECTOR_KEYS = {"sector"}
INDUSTRY_KEYS = {"industry"}
CATEGORY_KEYS = {"category", "cap type", "market cap category"}


def _normalise(row: dict) -> dict:
    return {k.strip().lower(): v.strip() if isinstance(v, str) else v
            for k, v in row.items()}


def _pick(row: dict, keys: set, default: str = "") -> str:
    for k in keys:
        if k in row:
            return row[k]
    return default


def _to_float(val: str) -> float:
    try:
        return float(val.replace(",", "").split()[0])
    except Exception:
        return 0.0


def _parse_csv(filepath: str, source_table: str) -> List[StockDTO]:
    stocks = []
    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            for raw in csv.DictReader(f):
                row = _normalise(raw)
                symbol = _pick(row, SYMBOL_KEYS)
                if not symbol:
                    continue
                stocks.append(StockDTO(
                    symbol=symbol.upper(),
                    price=_to_float(_pick(row, PRICE_KEYS)),
                    volume=_to_float(_pick(row, VOLUME_KEYS)),
                    sector=_pick(row, SECTOR_KEYS),
                    industry=_pick(row, INDUSTRY_KEYS),
                    category=_pick(row, CATEGORY_KEYS),
                    source_table=source_table,
                    metadata={"raw_row": dict(raw), "source_file": os.path.basename(filepath)},
                ))
    except Exception as e:
        print(f"[chartink_ingestion] [!] Could not parse {filepath}: {e}")
    return stocks


def load_from_chartink(run_date: str = None) -> List[StockDTO]:
    if run_date is None:
        run_date = date.today().isoformat()   # e.g. "2026-05-12"

    data_dir = (
        Path(__file__).resolve().parent        # infrastructure/adapters/ingestion/
        .parent.parent.parent                  # reversal_intelligence_engine/
        / "data" / "inputs" / "chartink" / run_date
    )

    if not data_dir.is_dir():
        print(f"[chartink_ingestion] [!] Folder not found: {data_dir}")
        return []

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        print(f"[chartink_ingestion] [!] No CSV files in {data_dir}")
        return []

    all_stocks: List[StockDTO] = []
    for fp in csv_files:
        source = fp.stem          # filename without .csv  ->  used as source_table
        batch  = _parse_csv(str(fp), source)
        print(f"[chartink_ingestion] [ok] {fp.name}  ->  {len(batch)} stocks")
        all_stocks.extend(batch)

    print(f"[chartink_ingestion] Total: {len(all_stocks)} stocks from {len(csv_files)} file(s)")
    return all_stocks
