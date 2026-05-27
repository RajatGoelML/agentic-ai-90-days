# ================================
# Signal Processor — Valuation
# ================================

from reversal_strategy.tools.analyzers import compute_relative_valuation
from reversal_strategy.processors.base_processor import SignalProcessor


class ValuationProcessor(SignalProcessor):
    """
    Computes the relative valuation signal for a stock.

    Uses sector-aware PE comparison (Chartink taxonomy preferred,
    yfinance as fallback) to avoid false overvaluation signals in
    structurally high-PE sectors such as Technology or FMCG.
    """

    name = "valuation"

    def process(self, payload):

        sector_for_pe = payload.chartink_sector or payload.sector

        payload.relative_valuation = compute_relative_valuation(
            pe_ratio=payload.pe_ratio,
            forward_pe=payload.forward_pe,
            sector=sector_for_pe
        )

        self._generate_valuation_signal(payload)

        return payload

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_valuation_signal(self, payload):

        rv = payload.relative_valuation or {}
        view = rv.get("valuation_view", "INSUFFICIENT_DATA")
        position = rv.get("peer_position", "UNKNOWN")

        if view == "INSUFFICIENT_DATA" or position == "UNKNOWN":
            payload.valuation_signal = "UNKNOWN"
            return

        if view in ("UNDERVALUED", "ATTRACTIVE"):
            payload.valuation_signal = "UNDERVALUED_VS_SECTOR"
            payload.supporting_signals.append("SECTOR_DISCOUNT")

        elif view == "FAIR_TO_SLIGHTLY_EXPENSIVE":
            payload.valuation_signal = "FAIRLY_VALUED"
            if position in ("FAIR_VALUE", "DISCOUNT", "DEEP_DISCOUNT"):
                payload.supporting_signals.append("REASONABLE_PE")

        elif view == "EXPENSIVE_VS_SECTOR":
            payload.valuation_signal = "OVERVALUED_VS_SECTOR"
            payload.risk_signals.append("PREMIUM_TO_SECTOR")

        # Forward PE compression = positive signal
        if rv.get("forward_pe_compression"):
            payload.supporting_signals.append("EARNINGS_GROWTH_NORMALIZING")

