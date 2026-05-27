from engine.llm.parser import parse_json_response


def parse_recommendation_response(response: str) -> dict:
    """
    Domain-aware parser for JudgeAgent outputs.

    Validates the LLM response against the recommendation contract:
    - Required fields: decision, confidence, summary
    - Allowed decisions: STRONG_BUY, EARLY_REVERSAL_CANDIDATE,
      GOOD_COMPANY_BAD_PRICE, HIGH_RISK_REVERSAL, AVOID_STRUCTURALLY_WEAK

    On any parse or validation failure:
    - Returns a HIGH_RISK_REVERSAL fallback dict
    - Sets parse_failed=True with a fallback_reason describing the failure
    - Never raises — failures are surfaced in the output, not as exceptions
    """
    fallback = {
        "decision": "HIGH_RISK_REVERSAL",
        "confidence": 0.4,
        "summary": "Failed to parse recommendation.",
        "reversal_quality": "",
        "supporting_signals": [],
        "risk_signals": [],
        "bull_case_summary": "",
        "bear_case_summary": "",
        "risk_reward": {
            "base_case_upside_pct": 0,
            "bear_case_downside_pct": 0,
            "bull_case_upside_pct": 0,
            "risk_reward_view": "NEUTRAL"
        },
        "parse_failed": True,
        "fallback_reason": "LLM response could not be parsed",
    }

    parsed = parse_json_response(response=response, fallback=fallback)

    if parsed is fallback:
        return fallback

    required_keys = ["decision", "confidence", "summary"]
    for key in required_keys:
        if key not in parsed:
            failed = dict(fallback)
            failed["fallback_reason"] = f"Missing required field: '{key}' in LLM response"
            return failed

    allowed_decisions = [
        "STRONG_BUY",
        "EARLY_REVERSAL_CANDIDATE",
        "GOOD_COMPANY_BAD_PRICE",
        "HIGH_RISK_REVERSAL",
        "AVOID_STRUCTURALLY_WEAK",
    ]
    if parsed["decision"] not in allowed_decisions:
        failed = dict(fallback)
        failed["fallback_reason"] = f"Invalid decision value: '{parsed['decision']}'"
        return failed

    parsed["parse_failed"] = False
    parsed.pop("fallback_reason", None)
    return parsed
