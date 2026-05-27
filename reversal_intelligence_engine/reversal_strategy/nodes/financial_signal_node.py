from datetime import datetime, timezone

from engine.nodes.node_base import (
    Node,
    NodeResult
)

from domain.models.signal_payload import SignalPayload

from reversal_strategy.processors import (
    ValuationProcessor,
    ProfitabilityProcessor,
    TechnicalProcessor,
    NewsProcessor,
)


class FinancialSignalNode(Node):

    """
    Converts raw financial metrics into deterministic semantic
    signals before they reach the LLM reasoning layer.

    Runs a sequential pipeline of focused SignalProcessor instances,
    each responsible for exactly one concern. Failures are isolated
    per step — a processor error skips that step but does not halt
    the pipeline.

    Pipeline:
        1. ValuationProcessor     — relative valuation signal
        2. ProfitabilityProcessor — profitability and growth signals
        3. TechnicalProcessor     — reversal-aware technical signals
        4. NewsProcessor          — news fetch and sentiment classification
    """

    _PIPELINE = [
        ValuationProcessor(),
        ProfitabilityProcessor(),
        TechnicalProcessor(),
        NewsProcessor(),
    ]

    def run(self, context):

        enriched_stocks = context.state.get("enriched_stocks", [])

        signal_payloads = []

        for stock in enriched_stocks:

            payload = SignalPayload(
                symbol=stock.get("symbol"),
                company_name=stock.get("company_name"),
                sector=stock.get("sector"),
                chartink_sector=stock.get("chartink_sector"),
                screening_price=stock.get("screening_price"),
                screening_volume=stock.get("screening_volume"),
                data_warnings=stock.get("data_warnings", []),
                pe_ratio=stock.get("pe_ratio"),
                forward_pe=stock.get("forward_pe"),
                roe=stock.get("roe"),
                roa=stock.get("roa"),
                eps=stock.get("eps"),
                market_cap=stock.get("market_cap"),
                revenue_growth=stock.get("revenue_growth"),
                signal_generation_timestamp=datetime.now(timezone.utc).isoformat(),
            )

            payload = self._run_pipeline(payload)

            signal_payloads.append(payload)

        return NodeResult(
            success=True,
            data={"signal_payloads": signal_payloads},
        )

    def _run_pipeline(self, payload: SignalPayload) -> SignalPayload:
        """
        Runs each processor in sequence. A failure in one step is
        logged and skipped; the payload continues with signals
        already set by earlier steps.
        """
        for processor in self._PIPELINE:
            try:
                payload = processor.process(payload)
            except Exception as e:
                print(f"[FinancialSignalNode] {processor.name} failed for {payload.symbol}: {e}")
        return payload
