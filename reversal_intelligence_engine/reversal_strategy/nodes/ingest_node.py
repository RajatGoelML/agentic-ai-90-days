# ================================
# Node Layer — Ingestion
# ================================

from engine.nodes.node_base import Node, NodeResult
from infrastructure.adapters.ingestion.screener_input import (
    fetch_weekly_candidates
)


class IngestNode(Node):

    """
    Loads stock candidates from the screener and initializes
    the workflow state with a minimal, structured payload.

    All Chartink-sourced fields are preserved exactly as received
    — screening price, sector taxonomy, and category — to prevent
    data loss before downstream enrichment.
    """

    def run(self, context):

        raw_stocks = fetch_weekly_candidates()

        ingested_stocks = []

        for stock in raw_stocks:

            ingested_stocks.append({
                "symbol":            stock.symbol,
                "screening_price":   stock.price or None,
                "screening_volume":  stock.volume or None,
                "chartink_sector":   stock.sector or None,
                "chartink_industry": stock.industry or None,
                "chartink_category": stock.category or None,
                "source_table":      stock.source_table or None,
            })

        return NodeResult(
            success=True,
            data={"ingested_stocks": ingested_stocks}
        )