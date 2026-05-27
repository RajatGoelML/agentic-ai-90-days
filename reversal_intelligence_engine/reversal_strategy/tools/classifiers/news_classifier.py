"""
================================================================
tools/classifiers/news_classifier.py
================================================================
PURPOSE:
    Converts raw news headlines into directional intelligence
    (bullish / bearish / neutral) using a single compact LLM call.

DATA SOURCE: Headlines from NewsFetcherTool
LLM CALL: Yes — 1 call per stock, ~200 input + ~150 output tokens.

DESIGN DECISIONS:
    - net_sentiment is computed ALGORITHMICALLY (not by LLM)
      to eliminate LLM inconsistency in direction labelling.
    - temperature=0.1 → near-deterministic classification.
    - max_tokens=400  → enforced budget.
================================================================
"""

from reversal_strategy.agents.llm_client import call_llm
from engine.llm.parser import parse_json_response
from reversal_strategy.tools.base_tool import BaseTool, ToolResult


# =========================================================
# Algorithmic net_sentiment — deterministic, not LLM-guessed
# =========================================================

def _compute_net_sentiment(bullish: list, bearish: list) -> str:
    b  = len(bullish)
    be = len(bearish)
    if b == 0 and be == 0: return "NEUTRAL"
    if b > be:             return "BULLISH"
    if be > b:             return "BEARISH"
    return "MIXED"   # equal and both > 0


# =========================================================
# System prompt — role-specific for classifier task
# =========================================================

_SYSTEM_PROMPT = (
    "You are a financial news classifier. "
    "Classify stock headlines strictly into bullish, bearish, or neutral categories. "
    "Return only valid JSON. Be concise. Do not add commentary outside the JSON."
)


# =========================================================
# Module-level function (used directly by financial_signal_node)
# =========================================================

def classify_news_headlines(
    symbol: str,
    sector: str,
    headlines: list
) -> dict:
    """
    Classifies news headlines into bullish/bearish/neutral.

    Returns:
    {
        "bullish":       ["impact summary 1", ...],
        "bearish":       ["impact summary 1", ...],
        "neutral_count": N,
        "net_sentiment": "BULLISH" | "BEARISH" | "MIXED" | "NEUTRAL"
    }
    """
    if not headlines:
        return {
            "bullish":       [],
            "bearish":       [],
            "neutral_count": 0,
            "net_sentiment": "NO_NEWS",
        }

    headline_block = "\n".join(
        f"{i+1}. {h}" for i, h in enumerate(headlines)
    )

    prompt = f"""Classify stock news. Return JSON only.

Stock: {symbol} | Sector: {sector}

Headlines:
{headline_block}

For each headline: classify as bullish/bearish/neutral.
For bullish and bearish only: write ONE short impact sentence (max 15 words).
Skip neutral headlines (only count them).

Return ONLY this JSON (no net_sentiment — it is computed separately):
{{"bullish":["impact1","impact2"],"bearish":["impact1"],"neutral_count":N}}"""

    try:
        response = call_llm(
            prompt=prompt,
            max_tokens=400,
            temperature=0.1,
            caller="NEWS_CLASSIFIER",
            system_prompt=_SYSTEM_PROMPT,
        )

        fallback = {
            "bullish":       [],
            "bearish":       [],
            "neutral_count": len(headlines),
        }

        parsed = parse_json_response(response, fallback=fallback)

        parsed.setdefault("bullish", [])
        parsed.setdefault("bearish", [])
        parsed.setdefault("neutral_count", 0)

        # Algorithmic direction — deterministic
        parsed["net_sentiment"] = _compute_net_sentiment(
            parsed["bullish"], parsed["bearish"]
        )

        return parsed

    except Exception as e:
        print(f"⚠️ News classification failed for {symbol}: {e}")
        return {
            "bullish":       [],
            "bearish":       [],
            "neutral_count": len(headlines),
            "net_sentiment": "CLASSIFICATION_FAILED",
        }


# =========================================================
# BaseTool wrapper — for registry + structured ToolResult
# =========================================================

class NewsClassifierTool(BaseTool):
    """
    Classifies stock news headlines into bullish/bearish/neutral
    with impact summaries using a single LLM call per stock.

    input_data keys:
        symbol    (str)       — stock ticker
        sector    (str)       — sector name for context
        headlines (list[str]) — raw headline strings

    Returns ToolResult.data = classification dict.
    """

    name = "news_classifier"
    description = (
        "Uses a single LLM call to classify stock news headlines into bullish, bearish, "
        "or neutral with one-sentence impact summaries. "
        "net_sentiment is computed algorithmically (not by the LLM)."
    )

    def run(self, input_data: dict) -> ToolResult:
        symbol    = input_data.get("symbol", "")
        sector    = input_data.get("sector", "")
        headlines = input_data.get("headlines", [])

        result = classify_news_headlines(symbol, sector, headlines)

        success = result.get("net_sentiment") != "CLASSIFICATION_FAILED"
        return ToolResult(
            success=success,
            data=result,
            error=None if success else "LLM classification failed",
            source=self.name,
        )

