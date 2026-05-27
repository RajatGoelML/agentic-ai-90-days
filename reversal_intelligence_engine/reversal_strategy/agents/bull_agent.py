from reversal_strategy.agents.base_agents import BaseAgent


class BullAgent(BaseAgent):

    """
    Generates the bullish investment thesis for a given stock.

    Focuses on upside potential, valuation opportunity created
    by the correction, reversal confirmation signals, and
    recovery catalysts. Operates independently from BearAgent
    to maintain epistemic separation.
    """

    AGENT_NAME = "BULL_AGENT"

    SYSTEM_PROMPT = (
        "You are a reversal-specialist equity analyst arguing the bullish case. "
        "Focus on recovery opportunity, valuation, and technical stabilization signals. "
        "Be concise, evidence-based, and structured. "
        "Only cite data that is explicitly provided — do not invent sector insights or external events."
    )

    MAX_TOKENS = 600

    def build_prompt(self, signal_payload):

        rv = signal_payload.relative_valuation or {}
        tc = signal_payload.technical_context or {}
        ns = signal_payload.news_sentiment or {}

        return f"""You are a senior reversal-specialist equity analyst arguing the BULLISH case.

CRITICAL CONTEXT: This stock comes from a REVERSAL SCREENER. It was pre-filtered for potential recovery.
Being near 52-week lows, in downtrend, or recently corrected is EXPECTED and NOT inherently bearish.

Your job: Evaluate whether this correction creates a buying opportunity.

STOCK: {signal_payload.symbol} | Sector: {signal_payload.sector}

FUNDAMENTALS:
- Valuation: {signal_payload.valuation_signal} | PE vs Sector: {rv.get('peer_position','N/A')} ({rv.get('valuation_view','N/A')})
- Profitability: {signal_payload.profitability_signal} | ROE: {signal_payload.roe}
- Growth: {signal_payload.growth_signal} | Revenue Growth: {signal_payload.revenue_growth}%

REVERSAL TECHNICALS:
- Correction Depth: {tc.get('correction_depth_pct','N/A')}% from 52W high
- Reversal Phase: {tc.get('reversal_phase','N/A')} | Structure: {tc.get('price_structure','N/A')}
- Higher Lows: {tc.get('higher_lows_forming','N/A')} | Stabilizing: {tc.get('price_stabilizing','N/A')}
- RS Improving: {tc.get('rs_improving','N/A')} | Volume: {tc.get('volume_signal','N/A')}

Supporting: {signal_payload.supporting_signals}

NEWS: Bullish: {ns.get('bullish', [])} | Net: {ns.get('net_sentiment', 'N/A')}

TASK (4 points max, be concise):
1. Reversal thesis: Why might this stock be bottoming?
2. Valuation opportunity created by the correction
3. Reversal confirmation signals present
4. Catalyst for recovery — base ONLY on provided data (volume_signal={tc.get('volume_signal','N/A')}, rs_improving={tc.get('rs_improving','N/A')}, bullish news={ns.get('bullish',[])}). If no data supports a catalyst, state "No catalyst confirmed yet." """

    def parse_response(self, response):

        return {
            "agent": "BULL",
            "thesis": response
        }
