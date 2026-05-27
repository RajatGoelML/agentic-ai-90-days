GRAPH = {

    # ---------------------------------------------------
    # STEP 1
    # CSV ingestion
    # ---------------------------------------------------
    "INGEST": [],

    # ---------------------------------------------------
    # STEP 2
    # Fetch raw financial intelligence
    # Example:
    # PE, ROE, EPS, Market Cap
    # ---------------------------------------------------
    "ENRICHMENT": ["INGEST"],

    # ---------------------------------------------------
    # STEP 3
    # Deterministic financial interpretation layer
    # Converts raw metrics into semantic signals
    # ---------------------------------------------------
    "SIGNAL": ["ENRICHMENT"],

    # ---------------------------------------------------
    # STEP 4
    # Multi-agent reasoning layer
    # Bull vs Bear vs Judge
    # ---------------------------------------------------
    "DEBATE": ["SIGNAL"],

    # ---------------------------------------------------
    # STEP 5
    # Final recommendations/watchlist
    # ---------------------------------------------------
    "WATCHLIST": ["DEBATE"]
}