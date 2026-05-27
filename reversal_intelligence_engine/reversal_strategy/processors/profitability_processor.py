# ================================
# Signal Processor — Profitability & Growth
# ================================

from reversal_strategy.processors.base_processor import SignalProcessor


class ProfitabilityProcessor(SignalProcessor):
    """
    Generates profitability and growth signals from fundamental metrics.

    Both signals share the same data source (yfinance enrichment output)
    and are computed together with no external I/O.
    """

    name = "profitability"

    def process(self, payload):

        self._generate_profitability_signal(payload)
        self._generate_growth_signal(payload)

        return payload

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_profitability_signal(self, payload):

        if payload.roe is None:
            payload.profitability_signal = "UNKNOWN"
            return

        if payload.roe >= 15:
            payload.profitability_signal = "STRONG"
            payload.supporting_signals.append("STRONG_ROE")
        else:
            payload.profitability_signal = "WEAK"
            payload.risk_signals.append("LOW_ROE")

    def _generate_growth_signal(self, payload):

        if payload.revenue_growth is None:
            payload.growth_signal = "UNKNOWN"
            return

        if payload.revenue_growth >= 10:
            payload.growth_signal = "HIGH_GROWTH"
            payload.supporting_signals.append("POSITIVE_REVENUE_GROWTH")
        else:
            payload.growth_signal = "SLOW_GROWTH"
            payload.risk_signals.append("LOW_REVENUE_GROWTH")

