# ================================
# Signal Processor — Technical Context
# ================================

from reversal_strategy.tools.data_fetchers import fetch_technical_context
from reversal_strategy.processors.base_processor import SignalProcessor


class TechnicalProcessor(SignalProcessor):
    """
    Fetches price structure data and integrates reversal-aware
    technical signals into the payload.

    These stocks originate from a reversal screener, so downtrend
    and proximity to 52-week lows are expected inputs. The processor
    evaluates reversal quality — stabilization, higher lows, RS
    improvement — rather than treating correction depth as a risk.
    """

    name = "technical"

    def process(self, payload):

        payload.technical_context = fetch_technical_context(
            symbol=payload.symbol
        )

        self._integrate_technical_signals(payload)

        return payload

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _integrate_technical_signals(self, payload):

        tc = payload.technical_context or {}
        reversal_phase = tc.get("reversal_phase", "UNKNOWN")
        structure      = tc.get("price_structure", "UNKNOWN")
        rs_improving   = tc.get("rs_improving", False)
        higher_lows    = tc.get("higher_lows_forming", False)
        stabilizing    = tc.get("price_stabilizing", False)
        reclaiming     = tc.get("reclaiming_short_ma", False)
        volume         = tc.get("volume_signal", "UNKNOWN")

        # ── Reversal quality signals ──

        if reversal_phase == "CONFIRMED_REVERSAL":
            payload.supporting_signals.append("RECOVERY_UNDERWAY")

        elif reversal_phase == "EARLY_REVERSAL":
            payload.supporting_signals.append("EARLY_REVERSAL_FORMING")

        elif reversal_phase == "ACCUMULATION_ZONE":
            payload.supporting_signals.append("ACCUMULATION_ZONE")

        elif reversal_phase == "NO_REVERSAL_YET":
            payload.risk_signals.append("NO_REVERSAL_CONFIRMATION")

        # ── Micro-structure confirmation ──

        if higher_lows:
            payload.supporting_signals.append("HIGHER_LOWS")

        if stabilizing and reversal_phase != "NOT_APPLICABLE":
            payload.supporting_signals.append("PRICE_STABILIZING")

        if reclaiming:
            payload.supporting_signals.append("RECLAIMING_SHORT_MA")

        if (volume == "INCREASING"
                and reversal_phase in ("EARLY_REVERSAL", "ACCUMULATION_ZONE")):
            payload.supporting_signals.append("VOLUME_ACCUMULATION")

        if rs_improving:
            payload.supporting_signals.append("RS_IMPROVING")

        # ── Only flag structural decline as risk ──
        # (active decline with no stabilization signs)
        if (structure == "ACTIVE_DECLINE"
                and not higher_lows
                and not stabilizing
                and not rs_improving):
            payload.risk_signals.append("CONTINUED_DECLINE")

