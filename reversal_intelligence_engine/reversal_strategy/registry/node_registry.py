from reversal_strategy.nodes.ingest_node import IngestNode
from reversal_strategy.nodes.enrichment_node import EnrichmentNode
from reversal_strategy.nodes.financial_signal_node import FinancialSignalNode
from reversal_strategy.nodes.debate_node import DebateNode
from reversal_strategy.nodes.watchlist_node import WatchlistNode


NODE_REGISTRY = {

    # ---------------------------------------------------
    # Step 1
    # CSV → stock list
    # ---------------------------------------------------
    "INGEST": IngestNode(),

    # ---------------------------------------------------
    # Step 2
    # Fetch raw financial metrics
    # ---------------------------------------------------
    "ENRICHMENT": EnrichmentNode(),

    # ---------------------------------------------------
    # Step 3
    # Deterministic signal extraction
    # ---------------------------------------------------
    "SIGNAL": FinancialSignalNode(),

    # ---------------------------------------------------
    # Step 4
    # Bull vs Bear vs Judge reasoning
    # ---------------------------------------------------
    "DEBATE": DebateNode(),

    # ---------------------------------------------------
    # Step 5
    # Final recommendations storage
    # ---------------------------------------------------
    "WATCHLIST": WatchlistNode()
}