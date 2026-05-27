from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SignalPayload:
    """
    Carries interpreted financial signals alongside raw metrics
    for a single stock candidate through the workflow.

    Deterministic signal fields are populated by the processor
    pipeline in FinancialSignalNode before any LLM reasoning occurs.
    """

    # Core Identity
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None

    # Chartink-sourced context (preserved from IngestNode)
    chartink_sector: Optional[str] = None
    screening_price: Optional[float] = None
    screening_volume: Optional[float] = None

    # Data quality warnings from yfinance validation
    data_warnings: List[str] = field(default_factory=list)

    # Raw financial metrics
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    eps: Optional[float] = None
    market_cap: Optional[float] = None
    revenue_growth: Optional[float] = None

    # Deterministic signals
    valuation_signal: Optional[str] = None
    profitability_signal: Optional[str] = None
    growth_signal: Optional[str] = None
    momentum_signal: Optional[str] = None
    debt_signal: Optional[str] = None

    # Risk and strength indicators
    supporting_signals: List[str] = field(default_factory=list)
    risk_signals: List[str] = field(default_factory=list)

    # Raw news headlines
    latest_news: List[str] = field(default_factory=list)

    # Sector-aware PE comparison
    relative_valuation: Optional[Dict] = None

    # Classified news sentiment (bullish / bearish / net)
    news_sentiment: Optional[Dict] = None

    # Price structure and reversal phase context
    technical_context: Optional[Dict] = None

    # Metadata
    signal_generation_timestamp: Optional[str] = None