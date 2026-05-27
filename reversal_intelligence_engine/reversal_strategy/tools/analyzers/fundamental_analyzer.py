"""
================================================================
tools/analyzers/fundamental_analyzer.py
================================================================
PURPOSE:
    Converts raw yfinance fundamentals into structured,
    AI-agent-consumable signal payloads.

DEPENDS ON:
    tools/data_fetchers/fundamentals_fetcher.py  ← raw fetch layer

NO LLM CALLS — pure deterministic signal derivation.

PIPELINE POSITION:
    fundamentals_fetcher.py  →  FundamentalsSnapshot
                              ↓
    fundamental_analyzer.py  →  build_agent_payload()   → enriched dict
                              →  FundamentalAnalyzerTool → ToolResult
                              ↓
    EnrichmentNode           →  enriched_stocks[]
================================================================
"""

import sys
import os
from typing import Optional

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from reversal_strategy.tools.data_fetchers.fundamentals_fetcher import (
    fetch_fundamentals,
    FundamentalsSnapshot,
)
from reversal_strategy.tools.base_tool import BaseTool, ToolResult


# =========================================================
# Threshold Constants
# =========================================================

PE_CHEAP_THRESHOLD       = 15.0
PE_EXPENSIVE_THRESHOLD   = 30.0

ROE_STRONG_THRESHOLD     = 15.0
ROE_ACCEPTABLE_THRESHOLD = 8.0

MARGIN_HIGH_THRESHOLD     = 20.0
MARGIN_MODERATE_THRESHOLD = 8.0

DE_LOW_THRESHOLD  = 30.0
DE_HIGH_THRESHOLD = 80.0

CR_HEALTHY_THRESHOLD  = 1.5
CR_ADEQUATE_THRESHOLD = 1.0

REV_GROWTH_STRONG   = 10.0
REV_GROWTH_POSITIVE = 0.0
EARN_GROWTH_STRONG  = 10.0


# =========================================================
# Deterministic Signal Helpers
# =========================================================

def _pe_signal(pe: Optional[float]) -> str:
    if pe is None:                        return "UNKNOWN"
    if pe <= PE_CHEAP_THRESHOLD:          return "CHEAP"
    if pe >= PE_EXPENSIVE_THRESHOLD:      return "EXPENSIVE"
    return "FAIR"


def _roe_signal(roe: Optional[float]) -> str:
    if roe is None:                          return "UNKNOWN"
    if roe >= ROE_STRONG_THRESHOLD:          return "STRONG"
    if roe >= ROE_ACCEPTABLE_THRESHOLD:      return "AVERAGE"
    return "WEAK"


def _debt_signal(de_ratio: Optional[float]) -> str:
    if de_ratio is None:                  return "UNKNOWN"
    if de_ratio <= DE_LOW_THRESHOLD:      return "LOW_DEBT"
    if de_ratio >= DE_HIGH_THRESHOLD:     return "HIGH_DEBT"
    return "MODERATE_DEBT"


def _growth_signal(revenue_growth: Optional[float]) -> str:
    if revenue_growth is None:                    return "UNKNOWN"
    if revenue_growth >= REV_GROWTH_STRONG:       return "HIGH_GROWTH"
    if revenue_growth > REV_GROWTH_POSITIVE:      return "POSITIVE_GROWTH"
    return "NEGATIVE_GROWTH"


# =========================================================
# Payload Builder — converts snapshot → agent-ready dict
# =========================================================

def build_agent_payload(snap: FundamentalsSnapshot) -> dict:
    """
    Converts raw FundamentalsSnapshot into structured AI-ready dict.

    Responsibilities:
    - field normalization
    - semantic signal generation from raw numbers
    - stable key contract for downstream workflow nodes
    """
    return {
        # Identity
        "symbol":       snap.symbol,
        "company_name": getattr(snap, "company_name", None) or snap.symbol,
        "sector":       snap.sector,

        # Raw Financial Metrics
        "market_cap":     snap.market_cap_raw,
        "pe_ratio":       snap.pe_ratio,
        "forward_pe":     snap.pe_forward_ratio,
        "roe":            snap.roe_pct,
        "roa":            snap.roa_pct,
        "eps":            snap.eps_trailing,
        "debt_to_equity": snap.debt_to_equity_ratio,
        "current_ratio":  snap.current_ratio,
        "profit_margin":  snap.profit_margin_pct,
        "revenue_growth": snap.revenue_growth_pct,
        "earnings_growth":snap.earnings_growth_pct,

        # Deterministic Signals
        "valuation_signal":    _pe_signal(snap.pe_ratio),
        "profitability_signal": _roe_signal(snap.roe_pct),
        "debt_signal":         _debt_signal(snap.debt_to_equity_ratio),
        "growth_signal":       _growth_signal(snap.revenue_growth_pct),

        # Metadata
        "fetch_status":  snap.fetch_status,
        "fetch_notes":   snap.fetch_notes,

        # Data quality warnings — forwarded to SignalPayload → final output
        # Allows agents and users to see data anomalies (e.g. negative PE, missing EPS)
        "data_warnings": snap.warnings or [],
    }


# =========================================================
# FundamentalAnalyzerTool — class interface (used by EnrichmentNode + registry)
# =========================================================

class FundamentalAnalyzerTool(BaseTool):
    """
    Fetches yfinance fundamentals and converts them into a
    structured AI-ready enrichment payload.

    input_data keys:
        symbol (str) — stock ticker, e.g. "KOTAKBANK.NS"

    Returns ToolResult.data = enriched dict (see build_agent_payload).
    """

    name = "fundamental_analyzer"
    description = (
        "Fetches company fundamentals from yfinance (PE, ROE, EPS, market cap, "
        "revenue growth) and produces deterministic valuation/profitability/growth signals. "
        "No LLM calls."
    )

    def run(self, input_data: dict) -> ToolResult:
        symbol = input_data.get("symbol")

        if not symbol:
            return ToolResult(
                success=False,
                data=None,
                error="symbol is required",
                source=self.name,
            )

        snap = fetch_fundamentals(symbol)

        if snap.fetch_status != "OK":
            return ToolResult(
                success=False,
                data=None,
                error=snap.fetch_notes or snap.fetch_status,
                source=self.name,
            )

        payload = build_agent_payload(snap)
        return ToolResult(
            success=True,
            data=payload,
            source=self.name,
        )


# =========================================================
# Backward-compat alias — EnrichmentNode used FundamentalIntelligenceTool
# =========================================================

FundamentalIntelligenceTool = FundamentalAnalyzerTool

