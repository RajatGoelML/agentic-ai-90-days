
GRAPH_CONFIG = {

    "START": {
        "next": ["DETERMINISTIC_SCORING"]
    },

    "DETERMINISTIC_SCORING": {
        "next": ["CREDIT_AGENT", "FRAUD_AGENT", "SECTOR_AGENT"]
    },

    "CREDIT_AGENT": {
        "next": ["AGGREGATOR"]
    },

    "FRAUD_AGENT": {
        "next": ["AGGREGATOR"]
    },

    "SECTOR_AGENT": {
        "next": ["AGGREGATOR"]
    },

    "AGGREGATOR": {
        "next": ["CRITIC"]
    },

    "CRITIC": {
        "next": ["POLICY"]
    },

    "POLICY": {
        "next": ["FINAL_DECISION"]
    },

    "FINAL_DECISION": {
        "next": []
    }
}        