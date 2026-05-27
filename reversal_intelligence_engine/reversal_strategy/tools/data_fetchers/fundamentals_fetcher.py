"""
================================================================
tools/data_fetchers/fundamentals_fetcher.py
================================================================
PURPOSE:
    Fetches, validates, and interprets raw company fundamentals
    from yfinance for a given stock symbol.

DATA SOURCE: Yahoo Finance via yfinance + curl_cffi session
NO LLM CALLS — pure deterministic data acquisition.

EXPORTS:
    FundamentalsSnapshot  — typed dataclass of all fetched fields
    fetch_fundamentals()  — main entry point
    print_snapshot()      — pretty-print for debugging
    quality_report()      — multi-symbol data quality summary

NAMING:
    *_pct   → percentage stored as 0–100 float  (12.5 means 12.5%)
    *_raw   → absolute monetary value in local currency
    *_ratio → pure ratio / multiplier (PE, P/B, D/E, current ratio)
    *_trend → derived categorical: INCREASING / STABLE / DECREASING
    *_label → human-readable bucketed string
================================================================
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from curl_cffi import requests as curl_requests
import yfinance as yf

_YF_SESSION = curl_requests.Session(impersonate="chrome", verify=False)


# ═════════════════════════════════════════════════════
# 1.  DATA MODEL
# ═════════════════════════════════════════════════════

@dataclass
class FundamentalsSnapshot:

    symbol: str

    # Identity / Name
    company_name: Optional[str] = None   # longName from yfinance (e.g. "Kotak Mahindra Bank Limited")

    # Meta
    currency:   Optional[str] = None    # "INR", "USD", etc.
    fetched_at: Optional[str] = None    # ISO-8601 UTC

    # Valuation ratios
    pe_ratio:             Optional[float] = None   # trailing P/E
    pe_forward_ratio:     Optional[float] = None   # analyst forward P/E
    price_to_book_ratio:  Optional[float] = None

    # Earnings
    eps_trailing: Optional[float] = None   # local currency
    eps_forward:  Optional[float] = None
    eps_trend:    Optional[str]   = None   # INCREASING / STABLE / DECREASING / UNKNOWN

    # Profitability  (all *_pct = already multiplied × 100)
    ebitda_raw:        Optional[float] = None
    profit_margin_pct: Optional[float] = None   # e.g. 18.4
    roe_pct:           Optional[float] = None
    roa_pct:           Optional[float] = None

    # Size & Debt
    market_cap_raw:       Optional[float] = None
    market_cap_readable:  Optional[str]   = None   # e.g. "₹18.55T"
    market_cap_label:     Optional[str]   = None   # Large / Mid / Small Cap
    debt_to_equity_ratio: Optional[float] = None
    current_ratio:        Optional[float] = None

    # Growth  (*_pct = already × 100)
    revenue_growth_pct:  Optional[float] = None
    earnings_growth_pct: Optional[float] = None
    revenue_trend:       Optional[str]   = None   # GROWING / FLAT / DECLINING
    revenue_consistency: Optional[str]   = None   # CONSISTENT / VOLATILE / INCONSISTENT

    # Sector
    sector:   Optional[str] = None
    industry: Optional[str] = None

    # Post-fetch layers
    signals:  dict = field(default_factory=dict)   # field → emoji signal string
    warnings: list = field(default_factory=list)

    # Fetch metadata
    fetch_status: str = "OK"
    fetch_notes:  str = ""


# ═════════════════════════════════════════════════════
# 2.  DERIVED-FIELD HELPERS
# ═════════════════════════════════════════════════════

def _derive_eps_trend(t: Optional[float], f: Optional[float]) -> str:
    if t is None or f is None:
        return "UNKNOWN"
    if f > t * 1.05:  return "INCREASING"
    if f < t * 0.95:  return "DECREASING"
    return "STABLE"


def _derive_revenue_trend(growth_pct: Optional[float]) -> str:
    if growth_pct is None: return "UNKNOWN"
    if growth_pct >= 3.0:  return "GROWING"
    if growth_pct < -5.0:  return "DECLINING"
    return "FLAT"


def _derive_revenue_consistency(growth_pct: Optional[float]) -> str:
    if growth_pct is None:   return "UNKNOWN"
    if growth_pct >= 3.0:    return "CONSISTENT"
    if growth_pct < -5.0:    return "INCONSISTENT"
    return "VOLATILE"


def _market_cap_label(raw: Optional[float], currency: Optional[str]) -> str:
    if raw is None: return "UNKNOWN"
    if currency == "USD":
        if raw >= 10_000_000_000: return "Large Cap"
        if raw >=  2_000_000_000: return "Mid Cap"
        return "Small Cap"
    else:   # INR / default
        if raw >= 200_000_000_000: return "Large Cap"
        if raw >=  10_000_000_000: return "Mid Cap"
        return "Small Cap"


def _human_readable(value: Optional[float], currency: Optional[str]) -> Optional[str]:
    if value is None: return None
    sym = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency or "", f"{currency} " if currency else "")
    av = abs(value)
    if av >= 1e12: return f"{sym}{value/1e12:.2f}T"
    if av >= 1e9:  return f"{sym}{value/1e9:.2f}B"
    if av >= 1e6:  return f"{sym}{value/1e6:.2f}M"
    if av >= 1e3:  return f"{sym}{value/1e3:.2f}K"
    return f"{sym}{value:.2f}"


# ═══════════════════════════════════════════��═════════
# 3.  INTERPRETATION LAYER
# ═════════════════════════════════════════════════════

def _interpret(snap: FundamentalsSnapshot) -> dict:
    sig = {}

    if snap.pe_ratio is not None:
        if snap.pe_ratio < 15:    sig["pe_ratio"] = "🟢 CHEAP"
        elif snap.pe_ratio < 30:  sig["pe_ratio"] = "🟡 FAIR"
        else:                     sig["pe_ratio"] = "🔴 EXPENSIVE"

    if snap.pe_ratio and snap.pe_forward_ratio:
        if snap.pe_forward_ratio < snap.pe_ratio * 0.95:   sig["pe_direction"] = "🟢 EARNINGS IMPROVING"
        elif snap.pe_forward_ratio > snap.pe_ratio * 1.05: sig["pe_direction"] = "🔴 EARNINGS DETERIORATING"
        else:                                               sig["pe_direction"] = "🟡 FLAT OUTLOOK"

    trend_map = {"INCREASING": "🟢 INCREASING", "STABLE": "🟡 STABLE",
                 "DECREASING": "🔴 DECREASING", "UNKNOWN": "⚪ UNKNOWN"}
    if snap.eps_trend:
        sig["eps_trend"] = trend_map.get(snap.eps_trend, snap.eps_trend)

    if snap.profit_margin_pct is not None:
        if snap.profit_margin_pct >= 20:   sig["profit_margin"] = "🟢 HIGH"
        elif snap.profit_margin_pct >= 8:  sig["profit_margin"] = "🟡 MODERATE"
        else:                              sig["profit_margin"] = "🔴 THIN"

    if snap.roe_pct is not None:
        if snap.roe_pct >= 15:   sig["roe"] = "🟢 STRONG"
        elif snap.roe_pct >= 8:  sig["roe"] = "🟡 ACCEPTABLE"
        else:                    sig["roe"] = "🔴 WEAK"

    if snap.debt_to_equity_ratio is not None:
        if snap.debt_to_equity_ratio < 30:    sig["debt_to_equity"] = "🟢 LOW DEBT"
        elif snap.debt_to_equity_ratio < 80:  sig["debt_to_equity"] = "🟡 MODERATE DEBT"
        else:                                 sig["debt_to_equity"] = "🔴 HIGH DEBT"

    if snap.revenue_growth_pct is not None:
        if snap.revenue_growth_pct >= 10:   sig["revenue_growth"] = "🟢 STRONG GROWTH"
        elif snap.revenue_growth_pct >= 0:  sig["revenue_growth"] = "🟡 MODEST GROWTH"
        else:                               sig["revenue_growth"] = "🔴 DECLINING"

    if snap.current_ratio is not None:
        if snap.current_ratio >= 1.5:    sig["current_ratio"] = "🟢 HEALTHY"
        elif snap.current_ratio >= 1.0:  sig["current_ratio"] = "🟡 ADEQUATE"
        else:                            sig["current_ratio"] = "🔴 LIQUIDITY RISK"

    return sig


# ═════════════════════════════════════════════════════
# 4.  VALIDATION LAYER
# ═════════════════════════════════════════════════════

def _validate(snap: FundamentalsSnapshot) -> list:
    w = []
    if snap.pe_ratio is not None and snap.pe_ratio > 100:
        w.append(f"⚠️  PE {snap.pe_ratio:.1f} > 100 — verify or extreme-growth stock")
    if snap.pe_ratio is not None and snap.pe_ratio < 0:
        w.append(f"⚠️  Negative PE ({snap.pe_ratio:.1f}) — loss-making trailing 12m")
    if snap.debt_to_equity_ratio is not None and snap.debt_to_equity_ratio > 150:
        w.append(f"⚠️  D/E {snap.debt_to_equity_ratio:.1f} > 150 — significant leverage risk")
    if snap.roe_pct is not None and snap.roe_pct > 100:
        w.append(f"⚠️  ROE {snap.roe_pct:.1f}% > 100% — may indicate negative equity")
    if snap.profit_margin_pct is not None and snap.profit_margin_pct < 0:
        w.append(f"⚠️  Negative profit margin ({snap.profit_margin_pct:.1f}%) — unprofitable")
    if snap.eps_trailing is not None and snap.eps_trailing < 0:
        w.append(f"⚠️  Negative trailing EPS ({snap.eps_trailing:.2f})")
    if snap.current_ratio is not None and snap.current_ratio < 0.8:
        w.append(f"⚠️  Current ratio {snap.current_ratio:.2f} < 0.8 — liquidity concern")
    if snap.revenue_growth_pct is not None and snap.revenue_growth_pct < -20:
        w.append(f"⚠️  Revenue decline {snap.revenue_growth_pct:.1f}% — severe contraction")
    if snap.ebitda_raw is not None and snap.ebitda_raw < 0:
        w.append(f"⚠️  Negative EBITDA — poor operating cash generation")
    return w


# ═════════════════════════════════════════════════════
# 5.  CORE FETCH FUNCTION
# ═════════════════════════════════════════════════════

def fetch_fundamentals(symbol: str) -> FundamentalsSnapshot:
    snap = FundamentalsSnapshot(
        symbol=symbol,
        fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    try:
        ticker = yf.Ticker(symbol, session=_YF_SESSION)
        info   = ticker.info

        if not info or (info.get("regularMarketPrice") is None
                        and info.get("currentPrice") is None):
            snap.fetch_status = "NO_DATA"
            snap.fetch_notes  = "Symbol not found or delisted"
            return snap

        snap.currency = info.get("currency", "UNKNOWN")

        # Valuation
        snap.pe_ratio            = info.get("trailingPE")
        snap.pe_forward_ratio    = info.get("forwardPE")
        snap.price_to_book_ratio = info.get("priceToBook")

        # Earnings
        snap.eps_trailing = info.get("trailingEps")
        snap.eps_forward  = info.get("forwardEps")
        snap.eps_trend    = _derive_eps_trend(snap.eps_trailing, snap.eps_forward)

        # Profitability — yfinance returns 0.18 for 18%, we store 18.0
        rm = info.get("profitMargins")
        rr = info.get("returnOnEquity")
        ra = info.get("returnOnAssets")

        snap.ebitda_raw        = info.get("ebitda")
        snap.profit_margin_pct = round(rm * 100, 2) if rm is not None else None
        snap.roe_pct           = round(rr * 100, 2) if rr is not None else None
        snap.roa_pct           = round(ra * 100, 2) if ra is not None else None

        # Size & Debt
        snap.market_cap_raw       = info.get("marketCap")
        snap.market_cap_readable  = _human_readable(snap.market_cap_raw, snap.currency)
        snap.market_cap_label     = _market_cap_label(snap.market_cap_raw, snap.currency)
        snap.debt_to_equity_ratio = info.get("debtToEquity")
        snap.current_ratio        = info.get("currentRatio")

        # Growth — yfinance returns 0.12 for 12%, we store 12.0
        rg  = info.get("revenueGrowth")
        eg  = info.get("earningsGrowth")
        snap.revenue_growth_pct  = round(rg * 100, 2) if rg is not None else None
        snap.earnings_growth_pct = round(eg * 100, 2) if eg is not None else None
        snap.revenue_trend       = _derive_revenue_trend(snap.revenue_growth_pct)
        snap.revenue_consistency = _derive_revenue_consistency(snap.revenue_growth_pct)

        snap.sector   = info.get("sector")
        snap.industry = info.get("industry")

        # Company name — longName is the full legal name (e.g. "Kotak Mahindra Bank Limited")
        snap.company_name = (
            info.get("longName")
            or info.get("shortName")
            or symbol
        )

    except Exception as e:
        snap.fetch_status = "ERROR"
        snap.fetch_notes  = str(e)
        return snap

    snap.signals  = _interpret(snap)
    snap.warnings = _validate(snap)
    return snap


# ═════════════════════════════════════════════════════
# 6.  PRETTY-PRINT
# ═════════════════════════════════════════════════════

def _f(v, suffix="", decimals=2):
    if v is None: return "N/A"
    if isinstance(v, float): return f"{v:,.{decimals}f}{suffix}"
    return f"{v}{suffix}"

def _s(signals, key): return signals.get(key, "")

def print_snapshot(snap: FundamentalsSnapshot):
    cur = snap.currency or "?"
    w   = ("\n    ".join(snap.warnings)) if snap.warnings else "✅ No anomalies detected"
    ebitda_hr = _human_readable(snap.ebitda_raw, snap.currency) or "N/A"

    print(f"""
╔════════════════════════════════════════════════════════════════╗
  📊  {snap.symbol}   [{snap.fetch_status}]   Currency: {cur}   As of: {snap.fetched_at}
  {snap.fetch_notes}
╠════════════════════════════════════════════════════════════════╣
  VALUATION
    PE Ratio (trailing)    : {_f(snap.pe_ratio)}x          {_s(snap.signals,'pe_ratio')}
    PE Ratio (forward)     : {_f(snap.pe_forward_ratio)}x          {_s(snap.signals,'pe_direction')}
    Price-to-Book          : {_f(snap.price_to_book_ratio)}x

  EARNINGS
    EPS Trailing (12m)     : {_f(snap.eps_trailing)}  {cur}
    EPS Forward (est.)     : {_f(snap.eps_forward)}  {cur}
    EPS Trend              : {snap.eps_trend or 'N/A'}     {_s(snap.signals,'eps_trend')}

  PROFITABILITY
    EBITDA                 : {ebitda_hr}
    Profit Margin          : {_f(snap.profit_margin_pct, suffix='%')}     {_s(snap.signals,'profit_margin')}
    ROE                    : {_f(snap.roe_pct, suffix='%')}     {_s(snap.signals,'roe')}
    ROA                    : {_f(snap.roa_pct, suffix='%')}

  SIZE & DEBT
    Market Cap             : {snap.market_cap_readable or 'N/A'}   [{snap.market_cap_label}]
    Debt-to-Equity         : {_f(snap.debt_to_equity_ratio)}       {_s(snap.signals,'debt_to_equity')}
    Current Ratio          : {_f(snap.current_ratio)}       {_s(snap.signals,'current_ratio')}

  GROWTH
    Revenue Growth (YoY)   : {_f(snap.revenue_growth_pct, suffix='%')}     {_s(snap.signals,'revenue_growth')}
    Earnings Growth (YoY)  : {_f(snap.earnings_growth_pct, suffix='%')}
    Revenue Trend          : {snap.revenue_trend or 'N/A'}
    Revenue Consistency    : {snap.revenue_consistency or 'N/A'}

  SECTOR
    Sector                 : {snap.sector or 'N/A'}
    Industry               : {snap.industry or 'N/A'}

  ⚡ VALIDATION
    {w}
╚════════════════════════════════════════════════════════════════╝""")


# ═════════════════════════════════════════════════════
# 7.  DATA-QUALITY REPORT
# ═════════════════════════════════════════════════════

CORE_FIELDS = [
    "pe_ratio", "eps_trailing", "eps_trend",
    "ebitda_raw", "revenue_trend",
    "market_cap_raw", "market_cap_label",
    "debt_to_equity_ratio", "roe_pct",
    "revenue_growth_pct", "revenue_consistency",
]

def quality_report(snapshots: list):
    print("\n" + "="*74)
    print("  DATA QUALITY REPORT")
    print("="*74)
    print(f"  {'Symbol':<22} {'Status':<10} {'Cur':<6} {'Fields OK':<12} {'Notes'}")
    print("  " + "-"*70)
    for snap in snapshots:
        d       = asdict(snap)
        ok      = [f for f in CORE_FIELDS if d.get(f) not in (None, "UNKNOWN")]
        missing = [f for f in CORE_FIELDS if d.get(f) in (None, "UNKNOWN")]
        wc      = len(snap.warnings)
        note    = (f"⚠️ {wc} warning(s)" if wc else "✅ clean") if snap.fetch_status == "OK" else snap.fetch_notes[:30]
        miss_s  = (", ".join(missing)) if missing else "all present"
        print(f"  {snap.symbol:<22} {snap.fetch_status:<10} {(snap.currency or '?'):<6} "
              f"{len(ok)}/{len(CORE_FIELDS):<8}  {note}  |  missing: {miss_s}")
    print("="*74)


# ═════════════════════════════════════════════════════
# 8.  STANDALONE TEST (run with: python -m tools.data_fetchers.fundamentals_fetcher)
# ═════════════════════════════════════════════════════

TEST_SYMBOLS = [
    "RELIANCE.NS", "INFY.NS", "HDFCBANK.NS", "TCS.NS",
    "AAPL", "MSFT",
]

if __name__ == "__main__":
    print("\n🔍 Fundamentals Fetcher — standalone test")
    print(f"   Testing {len(TEST_SYMBOLS)} symbols ...\n")
    snapshots = []
    for sym in TEST_SYMBOLS:
        print(f"  ⏳ Fetching {sym} ...")
        snap = fetch_fundamentals(sym)
        snapshots.append(snap)
        print_snapshot(snap)
    quality_report(snapshots)

