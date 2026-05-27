from reversal_strategy.agents.base_agents import BaseAgent

from domain.contracts.recommendation_parser import (
    parse_recommendation_response
)


class JudgeAgent(BaseAgent):

    """
    Synthesizes the bull and bear theses into a final structured
    investment recommendation.

    Receives both arguments, weighs them against the provided
    financial signals and technical context, and produces a
    decision from the five defined reversal classification
    categories along with a confidence score and risk/reward view.
    """

    AGENT_NAME = "JUDGE_AGENT"

    SYSTEM_PROMPT = (
        "You are a senior investment committee judge synthesizing adversarial bull and bear research. "
        "Your role is to weigh both arguments objectively and produce a final, structured classification. "
        "CRITICAL: You must differentiate between stocks — every stock should be evaluated on its OWN merits. "
        "Use the FULL range of decisions — STRONG_BUY, EARLY_REVERSAL_CANDIDATE, GOOD_COMPANY_BAD_PRICE, HIGH_RISK_REVERSAL, AVOID_STRUCTURALLY_WEAK. "
        "CONFIDENCE RULE: Confidence must be unique and signal-driven. "
        "Count the total supporting signals vs risk signals — more supporting signals = higher confidence within the chosen category. "
        "Two stocks in the same category with different signal counts MUST have different confidence values. "
        "Never assign the same confidence to two different stocks. Range: 0.30 to 0.90. "
        "You MUST return only valid JSON matching the requested schema exactly — no prose, no markdown fences. "
        "Do not hallucinate data not present in the input."
    )

    MAX_TOKENS = 1200

    # Higher temperature encourages meaningful differentiation across stocks
    TEMPERATURE = 0.4

    # =====================================================
    # Prompt Construction
    # =====================================================

    def build_prompt(

        self,

        signal_payload,

        bull_thesis,

        bear_thesis
    ):

        rv = signal_payload.relative_valuation or {}
        tc = signal_payload.technical_context or {}
        ns = signal_payload.news_sentiment or {}

        # ── Derived context injected into prompt ──
        prof_signal   = signal_payload.profitability_signal or "UNKNOWN"
        growth_signal = signal_payload.growth_signal        or "UNKNOWN"
        val_signal    = signal_payload.valuation_signal     or "UNKNOWN"
        tc_phase      = tc.get("reversal_phase", "UNKNOWN")
        tc_higher     = tc.get("higher_lows_forming", False)
        tc_stable     = tc.get("price_stabilizing", False)
        supporting_count = len(signal_payload.supporting_signals or [])
        risk_count       = len(signal_payload.risk_signals or [])

        # Fundamental quality tier (used as a label in the prompt)
        all_unknown = (
            prof_signal == "UNKNOWN"
            and growth_signal == "UNKNOWN"
            and val_signal == "UNKNOWN"
        )
        strong_fundamentals = (
            prof_signal == "STRONG"
            and growth_signal in ("HIGH_GROWTH",)
        )
        fundamentals_tier = (
            "UNKNOWN" if all_unknown
            else "STRONG" if strong_fundamentals
            else "DECENT"
        )

        # Technical reversal tier
        tech_tier = (
            "CONFIRMED"  if tc_phase == "CONFIRMED_REVERSAL"
            else "EARLY"    if tc_phase == "EARLY_REVERSAL"
            else "FORMING"  if tc_phase == "ACCUMULATION_ZONE"
            else "NONE"     if tc_phase == "NO_REVERSAL_YET"
            else "UNCERTAIN"
        )

        return f"""You are a senior reversal-focused investment committee judge.

CONTEXT: These stocks come from a REVERSAL SCREENER — pre-filtered for recovery potential.
Correction, downtrend, and 52W low proximity are EXPECTED. Evaluate REVERSAL PROBABILITY.

===== THIS STOCK'S DATA SNAPSHOT =====
Fundamentals tier : {fundamentals_tier}  (profitability={prof_signal}, growth={growth_signal}, valuation={val_signal})
Technical tier    : {tech_tier}  (reversal_phase={tc_phase}, higher_lows={tc_higher}, stabilizing={tc_stable})
Signal balance    : {supporting_count} supporting signals vs {risk_count} risk signals

===== TWO-DIMENSION DECISION MATRIX =====

Evaluate FUNDAMENTALS QUALITY and TECHNICAL REVERSAL STATUS independently, then combine:

FUNDAMENTALS QUALITY:
  STRONG  → ROE >= 15 AND positive revenue growth AND known valuation
  DECENT  → Some metrics known (even if mixed) — at least one of ROE/growth/PE is not UNKNOWN
  UNKNOWN → ALL of profitability, growth, valuation are UNKNOWN/N/A
  WEAK    → Known ROE < 15 + negative/slow growth, or clearly deteriorating metrics

TECHNICAL REVERSAL STATUS:
  CONFIRMED → reversal_phase = CONFIRMED_REVERSAL (uptrend underway, price recovering)
  EARLY     → reversal_phase = EARLY_REVERSAL (higher lows forming, reclaiming MA, or tight stabilization)
  FORMING   → reversal_phase = ACCUMULATION_ZONE (stabilizing near lows, directional signs beginning)
  NONE      → reversal_phase = NO_REVERSAL_YET (active decline, no floor visible)
  UNCERTAIN → reversal_phase = TRANSITION or UNKNOWN

DECISION MAPPING (combine both dimensions):
  STRONG_BUY             → STRONG fundamentals + CONFIRMED or EARLY tech
  EARLY_REVERSAL_CANDIDATE → STRONG or DECENT fundamentals + EARLY or FORMING tech
  GOOD_COMPANY_BAD_PRICE → STRONG or DECENT fundamentals + NONE or UNCERTAIN tech (decline ongoing, no bottom yet)
  HIGH_RISK_REVERSAL     → UNKNOWN fundamentals (any tech tier) OR WEAK fundamentals (any tech)
  AVOID_STRUCTURALLY_WEAK → Any fundamentals + NONE tech + evidence of structural business deterioration (negative EPS, collapsing revenue)

EDGE CASES:
  - UNKNOWN fundamentals + EARLY tech with multiple supporting signals → borderline HIGH_RISK_REVERSAL or EARLY_REVERSAL_CANDIDATE; use bull/bear thesis to decide
  - DECENT fundamentals + NONE tech → GOOD_COMPANY_BAD_PRICE (wait for entry)
  - WEAK fundamentals + FORMING tech → HIGH_RISK_REVERSAL (speculative, not investable yet)

===== CONFIDENCE (signal-driven, NOT a fixed range) =====
Confidence = f(signal count, data quality, bull/bear thesis alignment)
  High (0.75-0.90) : Strong fundamentals + multiple confirmed signals + clear bull thesis
  Mid  (0.55-0.74) : Decent fundamentals + some confirmed signals + mixed thesis
  Low  (0.35-0.54) : Unknown/weak fundamentals, or conflicting signals, or incomplete picture
  Very low (0.30-0.34) : Almost no verifiable data, highly speculative

RULE: You MUST vary confidence based on this stock's specific signal count ({supporting_count} supporting, {risk_count} risk).
Do NOT use a round number (0.65, 0.45) — reflect the actual signal balance.

===== STOCK DATA =====
STOCK: {signal_payload.symbol} | Sector: {signal_payload.sector}

RELATIVE VALUATION:
Company PE: {rv.get('company_pe','N/A')} | Sector Median: {rv.get('sector_median_pe','N/A')} | Band: {rv.get('sector_pe_band','N/A')}
Position: {rv.get('peer_position','N/A')} | View: {rv.get('valuation_view','N/A')}

SIGNALS:
- Valuation: {signal_payload.valuation_signal}
- Profitability: {signal_payload.profitability_signal}
- Growth: {signal_payload.growth_signal}

REVERSAL TECHNICALS:
Reversal Phase: {tc.get('reversal_phase','N/A')} | Structure: {tc.get('price_structure','N/A')}
Correction Depth: {tc.get('correction_depth_pct','N/A')}% | Trend: {tc.get('trend','N/A')}
Higher Lows: {tc.get('higher_lows_forming','N/A')} | Stabilizing: {tc.get('price_stabilizing','N/A')}
RS Improving: {tc.get('rs_improving','N/A')} | Volume: {tc.get('volume_signal','N/A')}

Supporting ({supporting_count}): {signal_payload.supporting_signals}
Risk ({risk_count}): {signal_payload.risk_signals}

NEWS SENTIMENT:
Bullish: {ns.get('bullish', [])}
Bearish: {ns.get('bearish', [])}
Net: {ns.get('net_sentiment', 'N/A')}

BULL THESIS:
{bull_thesis["thesis"]}

BEAR THESIS:
{bear_thesis["thesis"]}

Return STRICT JSON ONLY:
{{
    "decision": "STRONG_BUY | EARLY_REVERSAL_CANDIDATE | GOOD_COMPANY_BAD_PRICE | HIGH_RISK_REVERSAL | AVOID_STRUCTURALLY_WEAK",
    "confidence": 0.0,
    "summary": "2-3 sentence reversal assessment",
    "reversal_quality": "Brief: is this a credible reversal or structural decline?",
    "supporting_signals": [],
    "risk_signals": [],
    "bull_case_summary": "1 sentence",
    "bear_case_summary": "1 sentence",
    "risk_reward": {{
        "base_case_upside_pct": 0,
        "bear_case_downside_pct": 0,
        "bull_case_upside_pct": 0,
        "risk_reward_view": "FAVORABLE | NEUTRAL | UNFAVORABLE"
    }}
}}

IMPORTANT: confidence 0-1, return ONLY valid JSON."""

    # =====================================================
    # Structured Parsing
    # =====================================================

    def parse_response(self, response):

        parsed = parse_recommendation_response(
            response
        )

        return parsed