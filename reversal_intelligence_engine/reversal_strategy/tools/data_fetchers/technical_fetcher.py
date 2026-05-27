"""
================================================================
tools/data_fetchers/technical_fetcher.py
================================================================
PURPOSE:
    Computes reversal-aware technical structure from 1-year
    price history fetched via yfinance.

DATA SOURCE: Yahoo Finance via yfinance + curl_cffi session
NO LLM CALLS — pure deterministic computation.

KEY PRINCIPLE:
    Stocks in this pipeline come from a reversal screener.
    Analysis evaluates REVERSAL QUALITY, not trend-following.
    A stock near 52W low is an opportunity signal, not a risk.

SIGNALS COMPUTED:
    - Trend (UPTREND / DOWNTREND / SIDEWAYS)
    - Price structure & reversal phase classification
    - Higher lows detection (30-day window)
    - Price stabilization (narrowing range near lows)
    - Volume accumulation vs average
    - Relative strength vs benchmark index
================================================================
"""

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from curl_cffi import requests as curl_requests
import yfinance as yf
import numpy as np

from reversal_strategy.tools.base_tool import BaseTool, ToolResult

_YF_SESSION = curl_requests.Session(impersonate="chrome", verify=False)

# Nifty 50 for NSE stocks, BSE Sensex for BSE, S&P 500 default
BENCHMARK_MAP = {
    ".NS": "^NSEI",
    ".BO": "^BSESN",
}
DEFAULT_BENCHMARK = "^GSPC"


def _resolve_benchmark(symbol: str) -> str:
    for suffix, bench in BENCHMARK_MAP.items():
        if symbol.upper().endswith(suffix):
            return bench
    return DEFAULT_BENCHMARK


# =========================================================
# Module-level function (called directly by financial_signal_node)
# =========================================================

def fetch_technical_context(symbol: str) -> dict:
    """
    Computes reversal-aware technical structure from price data.
    Returns a structured dict. On failure, returns _unknown_context().
    """
    try:
        ticker = yf.Ticker(symbol, session=_YF_SESSION)
        hist = ticker.history(period="1y", interval="1d")

        if hist is None or len(hist) < 50:
            return _unknown_context("Insufficient price history")

        close  = hist["Close"].values
        volume = hist["Volume"].values if "Volume" in hist.columns else None
        current_price = close[-1]

        # ── Moving Averages ──
        dma_200 = np.mean(close[-200:]) if len(close) >= 200 else np.mean(close)
        dma_50  = np.mean(close[-50:])
        dma_20  = np.mean(close[-20:])

        above_200 = bool(current_price > dma_200)
        above_50  = bool(current_price > dma_50)

        # ── Trend Detection ──
        if above_50 and above_200 and dma_50 > dma_200:
            trend = "UPTREND"
        elif not above_50 and not above_200 and dma_50 < dma_200:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"

        # ── Price Position ──
        high_52w  = np.max(close)
        low_52w   = np.min(close)
        range_52w = high_52w - low_52w if high_52w != low_52w else 1

        pct_from_high = (high_52w - current_price) / high_52w * 100
        pct_from_low  = (current_price - low_52w) / low_52w * 100 if low_52w > 0 else 0

        correction_depth = round(float(pct_from_high), 1)

        # ── REVERSAL-SPECIFIC SIGNALS ──

        higher_lows = _detect_higher_lows(close)

        recent_20       = close[-20:]
        recent_range_pct = (np.max(recent_20) - np.min(recent_20)) / range_52w
        # Require the 20-day range to be ≤ 8% of the 52W range (was 12%).
        # 12% was too permissive — almost any stock near its 52W low qualified.
        stabilizing     = bool(recent_range_pct < 0.08)

        reclaiming_20dma = bool(
            current_price > dma_20 and close[-5] < np.mean(close[-25:-5])
        )

        volume_signal = _detect_volume_accumulation(volume) if volume is not None else "UNKNOWN"
        rs_improving  = _detect_rs_improvement(close)

        # ── REVERSAL STRUCTURE CLASSIFICATION ──
        if pct_from_high <= 5:
            price_structure = "NEAR_HIGHS"
            reversal_phase  = "NOT_APPLICABLE"
        elif stabilizing and higher_lows:
            price_structure = "BOTTOMING_WITH_HIGHER_LOWS"
            reversal_phase  = "EARLY_REVERSAL"
        elif stabilizing and pct_from_high > 20:
            price_structure = "STABILIZING_AFTER_CORRECTION"
            reversal_phase  = "ACCUMULATION_ZONE"
        elif reclaiming_20dma and pct_from_high > 15:
            price_structure = "RECLAIMING_SHORT_TERM_MA"
            reversal_phase  = "EARLY_REVERSAL"
        elif recent_range_pct < 0.08 and pct_from_high > 20:
            price_structure = "TIGHT_CONSOLIDATION_NEAR_LOWS"
            reversal_phase  = "ACCUMULATION_ZONE"
        elif trend == "DOWNTREND" and not stabilizing:
            price_structure = "ACTIVE_DECLINE"
            reversal_phase  = "NO_REVERSAL_YET"
        elif trend == "UPTREND":
            price_structure = "RECOVERY_UNDERWAY"
            reversal_phase  = "CONFIRMED_REVERSAL"
        else:
            price_structure = "CONSOLIDATION"
            reversal_phase  = "TRANSITION"

        # ── Relative Strength vs Benchmark ──
        benchmark_symbol  = _resolve_benchmark(symbol)
        relative_strength = _compute_relative_strength(symbol, benchmark_symbol, close)

        return {
            "trend":                      trend,
            "above_200_dma":              above_200,
            "above_50_dma":               above_50,
            "relative_strength_vs_index": relative_strength,
            "rs_improving":               rs_improving,
            "price_structure":            price_structure,
            "reversal_phase":             reversal_phase,
            "correction_depth_pct":       correction_depth,
            "pct_from_52w_high":          round(float(pct_from_high), 1),
            "pct_from_52w_low":           round(float(pct_from_low), 1),
            "higher_lows_forming":        higher_lows,
            "price_stabilizing":          stabilizing,
            "reclaiming_short_ma":        reclaiming_20dma,
            "volume_signal":              volume_signal,
        }

    except Exception as e:
        print(f"⚠️ Technical context failed for {symbol}: {e}")
        return _unknown_context(str(e))


# =========================================================
# Reversal Detection Helpers
# =========================================================

def _detect_higher_lows(close: np.ndarray) -> bool:
    """
    Detects a meaningful higher-lows pattern over the last 30 trading days.

    Splits into three 10-day windows and requires each successive trough
    to be at least 0.75% higher than the previous one — filtering out
    trivial noise bounces that would otherwise qualify every stock near
    its 52-week low as forming higher lows.
    """
    if len(close) < 30:
        return False
    recent = close[-30:]
    w1_low = np.min(recent[:10])
    w2_low = np.min(recent[10:20])
    w3_low = np.min(recent[20:])
    # Each successive low must be meaningfully higher (>= 0.75% improvement)
    min_improvement = 0.0075
    return bool(
        w2_low > w1_low * (1 + min_improvement)
        and w3_low > w2_low * (1 + min_improvement)
    )


def _detect_volume_accumulation(volume: np.ndarray) -> str:
    if volume is None or len(volume) < 50:
        return "UNKNOWN"
    recent_vol = np.mean(volume[-10:])
    avg_vol    = np.mean(volume[-50:])
    if avg_vol == 0:
        return "UNKNOWN"
    ratio = recent_vol / avg_vol
    if ratio > 1.3:   return "INCREASING"
    elif ratio < 0.7: return "DECLINING"
    else:             return "NORMAL"


def _detect_rs_improvement(close: np.ndarray) -> bool:
    if len(close) < 63:
        return False
    ret_1m = (close[-1] / close[-21] - 1) * 100
    ret_3m = (close[-1] / close[-63] - 1) * 100
    return bool(ret_1m > ret_3m)


def _compute_relative_strength(
    symbol: str,
    benchmark_symbol: str,
    stock_close: np.ndarray
) -> str:
    try:
        bench      = yf.Ticker(benchmark_symbol, session=_YF_SESSION)
        bench_hist = bench.history(period="1y", interval="1d")

        if bench_hist is None or len(bench_hist) < 63:
            return "UNKNOWN"

        bench_close = bench_hist["Close"].values
        lookback    = min(63, len(stock_close) - 1, len(bench_close) - 1)
        if lookback < 20:
            return "UNKNOWN"

        stock_return = (stock_close[-1] / stock_close[-lookback] - 1) * 100
        bench_return = (bench_close[-1] / bench_close[-lookback] - 1) * 100
        excess       = stock_return - bench_return

        if excess > 5:    return "OUTPERFORMING"
        elif excess < -5: return "UNDERPERFORMING"
        else:             return "INLINE"

    except Exception:
        return "UNKNOWN"


def _unknown_context(reason: str) -> dict:
    return {
        "trend":                      "UNKNOWN",
        "above_200_dma":              None,
        "above_50_dma":               None,
        "relative_strength_vs_index": "UNKNOWN",
        "rs_improving":               None,
        "price_structure":            "UNKNOWN",
        "reversal_phase":             "UNKNOWN",
        "correction_depth_pct":       None,
        "pct_from_52w_high":          None,
        "pct_from_52w_low":           None,
        "higher_lows_forming":        None,
        "price_stabilizing":          None,
        "reclaiming_short_ma":        None,
        "volume_signal":              "UNKNOWN",
        "error":                      reason,
    }


# =========================================================
# BaseTool wrapper — for registry + structured ToolResult
# =========================================================

class TechnicalFetcherTool(BaseTool):
    """
    Computes reversal-aware technical signals from 1-year price history.

    input_data keys:
        symbol (str) — stock ticker, e.g. "KOTAKBANK.NS"

    Returns ToolResult.data = technical context dict.
    """

    name = "technical_fetcher"
    description = (
        "Fetches 1-year price history from yfinance and computes reversal-specific "
        "technical signals: trend, reversal phase, higher lows, volume, RS vs index. "
        "No LLM calls. Pure deterministic computation."
    )

    def run(self, input_data: dict) -> ToolResult:
        symbol = input_data.get("symbol")
        if not symbol:
            return ToolResult(
                success=False,
                data=_unknown_context("symbol is required"),
                error="symbol is required",
                source=self.name,
            )
        context = fetch_technical_context(symbol)
        success = context.get("trend") != "UNKNOWN" or "error" not in context
        return ToolResult(
            success=success,
            data=context,
            error=context.get("error"),
            source=self.name,
        )

