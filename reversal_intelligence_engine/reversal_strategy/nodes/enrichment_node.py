from engine.nodes.node_base import (
    Node,
    NodeResult
)

from reversal_strategy.tools.analyzers import FundamentalIntelligenceTool


class EnrichmentNode(Node):

    """
    Fetches live financial fundamentals for each ingested stock
    and merges the enriched data into the workflow state.

    Uses yfinance via FundamentalIntelligenceTool. Indian NSE
    symbols are automatically suffixed with .NS before the fetch.
    Stocks that fail enrichment are skipped with a logged warning
    — the remaining candidates continue through the pipeline.
    """

    def __init__(self):
        self.tool = FundamentalIntelligenceTool()

    def run(self, context):

        ingested_stocks = context.state.get("ingested_stocks", [])

        enriched_stocks = []

        for stock in ingested_stocks:

            symbol = stock.get("symbol")

            try:

                yf_symbol = symbol
                if yf_symbol and "." not in yf_symbol:
                    yf_symbol = f"{symbol}.NS"

                result = self.tool.run({"symbol": yf_symbol})

                if hasattr(result, "success"):
                    if not result.success:
                        print(f"\n[EnrichmentNode] Skipping {symbol}: {result.error}")
                        continue
                    payload = result.data or {}
                else:
                    if result.get("fetch_status") != "OK":
                        print(f"\n[EnrichmentNode] Skipping {symbol}: fetch_status not OK")
                        continue
                    payload = result.get("data", {})

                enriched_stock = {**stock, **payload}
                enriched_stocks.append(enriched_stock)

            except Exception as e:
                print(f"\n[EnrichmentNode] Failed for {symbol}: {e}")

        return NodeResult(
            success=True,
            data={"enriched_stocks": enriched_stocks}
        )