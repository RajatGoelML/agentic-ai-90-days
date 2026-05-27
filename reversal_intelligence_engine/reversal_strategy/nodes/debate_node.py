from concurrent.futures import ThreadPoolExecutor

from engine.nodes.node_base import (
    Node,
    NodeResult
)

from reversal_strategy.agents.bull_agent import BullAgent
from reversal_strategy.agents.bear_agent import BearAgent
from reversal_strategy.agents.judge_agent import JudgeAgent


class DebateNode(Node):

    """
    Orchestrates the adversarial multi-agent reasoning pipeline.

    Bull and Bear agents run in PARALLEL (ThreadPoolExecutor) for each stock.
    The Judge runs only after both theses are ready — preserving correctness
    while cutting per-stock latency from 3 sequential LLM calls to 2 slots.
    """

    def __init__(self):

        self.bull_agent  = BullAgent()
        self.bear_agent  = BearAgent()
        self.judge_agent = JudgeAgent()

    # ------------------------------------------------------------------
    # Bull + Bear run concurrently — they are fully independent
    # ------------------------------------------------------------------

    def _run_bull_bear(self, payload):
        """Submits Bull and Bear to a thread pool, blocks until both return."""
        with ThreadPoolExecutor(max_workers=2) as executor:
            bull_future = executor.submit(self.bull_agent.run, payload)
            bear_future = executor.submit(self.bear_agent.run, payload)
            return bull_future.result(), bear_future.result()

    def run(self, context):

        signal_payloads = context.state.get("signal_payloads", [])

        final_recommendations = []

        for payload in signal_payloads:

            print(f"\nRunning debate for: {payload.symbol}")

            # ── Bull + Bear in parallel, then Judge ──
            bull_result, bear_result = self._run_bull_bear(payload)

            judge_result = self.judge_agent.run(
                signal_payload=payload,
                bull_thesis=bull_result,
                bear_thesis=bear_result
            )

            judge_result["symbol"]       = payload.symbol
            judge_result["sector"]       = payload.sector
            judge_result["company_name"] = payload.company_name

            judge_result["chartink_sector"]  = payload.chartink_sector
            judge_result["screening_price"]  = payload.screening_price
            judge_result["screening_volume"] = payload.screening_volume

            judge_result["data_warnings"] = payload.data_warnings or []

            judge_result["latest_news"] = payload.latest_news or []

            judge_result["news_sentiment"] = payload.news_sentiment or {}

            # Deterministic signals included for audit trail
            judge_result["signals"] = {
                "valuation":     payload.valuation_signal,
                "profitability": payload.profitability_signal,
                "growth":        payload.growth_signal,
            }

            judge_result["relative_valuation"] = payload.relative_valuation or {}

            judge_result["technical_context"] = payload.technical_context or {}

            judge_result["metrics"] = {
                "pe_ratio":       payload.pe_ratio,
                "forward_pe":     payload.forward_pe,
                "roe":            payload.roe,
                "eps":            payload.eps,
                "revenue_growth": payload.revenue_growth,
                "market_cap":     payload.market_cap,
            }

            # Deterministic risk/reward view — overrides LLM inconsistency
            # Higher confidence = better decision quality, not necessarily favourable trade
            # Tie risk_reward_view to the decision classification instead
            _decision_to_rr = {
                "STRONG_BUY":                "FAVORABLE",
                "EARLY_REVERSAL_CANDIDATE":  "FAVORABLE",
                "GOOD_COMPANY_BAD_PRICE":    "NEUTRAL",
                "HIGH_RISK_REVERSAL":        "NEUTRAL",
                "AVOID_STRUCTURALLY_WEAK":   "UNFAVORABLE",
            }
            if "risk_reward" in judge_result:
                judge_result["risk_reward"]["risk_reward_view"] = _decision_to_rr.get(
                    judge_result.get("decision", ""), "NEUTRAL"
                )

            final_recommendations.append(judge_result)

        return NodeResult(
            success=True,
            data={"final_recommendations": final_recommendations}
        )