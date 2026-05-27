from reversal_strategy.agents.base_agents import BaseAgent


class BearAgent(BaseAgent):

    """
    Generates the bearish investment thesis for a given stock.

    Focuses on structural business risks, downside scenarios,
    and conditions that would invalidate the reversal hypothesis.
    Operates independently from BullAgent to maintain epistemic
    separation before the Judge synthesizes both arguments.
    """

    AGENT_NAME = "BEAR_AGENT"

    SYSTEM_PROMPT = (
        "You are a senior risk analyst specializing in identifying structural business deterioration. "
        "Focus only on genuine fundamental risks — not price-action or technical weakness. "
        "Be concise, evidence-based, and structured. "
        "IMPORTANT: If any data field is null, unknown, or missing, do NOT infer a risk from its absence. "
        "Only cite risks that are explicitly supported by the provided data."
    )

    MAX_TOKENS = 600

    def build_prompt(self, signal_payload):

        rv = signal_payload.relative_valuation or {}
        tc = signal_payload.technical_context or {}
        ns = signal_payload.news_sentiment or {}

        return f"""You are a senior risk analyst evaluating a REVERSAL CANDIDATE.

CRITICAL CONTEXT: This stock comes from a REVERSAL SCREENER. It was pre-filtered for recovery potential.
DO NOT treat correction, downtrend, or proximity to 52W low as standalone bearish signals.
DATA RULE: If EPS, ROE, or revenue growth is null/UNKNOWN, do NOT invent structural concerns — state "data unavailable" and skip that point.

Your job: Determine if the decline reflects STRUCTURAL BUSINESS DETERIORATION or just TEMPORARY PRICE WEAKNESS.

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

Risk Signals: {signal_payload.risk_signals}

NEWS: Bearish: {ns.get('bearish', [])} | Net: {ns.get('net_sentiment', 'N/A')}

TASK (4 points max, concise):
1. Is this structural decline or temporary correction? Why?
2. What fundamental risks could prevent recovery?
3. Is the downtrend likely to continue? Evidence.
4. What would invalidate the reversal thesis?"""

    def parse_response(self, response):

        return {
            "agent": "BEAR",
            "thesis": response
        }

