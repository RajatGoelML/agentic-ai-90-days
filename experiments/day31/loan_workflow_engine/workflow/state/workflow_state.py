
# ------------------------------------------------
# Workflow State
# ------------------------------------------------

state = {

    # --- Workflow execution pointer
    "current_node": "START",

    # --- Workflow lifecycle
    "status": "RUNNING",

    # --- Unified execution log (replaces history + trace)
    "execution_log": [],

    # completed nodes for DAG scheduler
    "completed_nodes": set(),

    # --- Infinite loop guard
    "step_count": 0,
    "max_steps": 20,

    # --- Retry tracking
    "retry_count": {},

    "routing": None,
    
    "routing_consumed": None,

    # --- Dynamic routing control
    "allowed_next_nodes": None,

    # --- Business data used by workflow
    "data": {

        # Input application
        "application": {
            "loan_id": "L001",
            "loan_amount": 800000,
            "income": 2400000,
            "debt": 300000,
            "emi": 15000,
            "credit_score": 785,
            "years_operating": 8,
            "sector": "IT Services"
        },

        # Deterministic scoring output
        "financial_score": None,
        "risk_bucket": None,

        # Agent summary signals
        "agent_summary": {
            "credit_risk": None,
            "fraud_risk": None,
            "sector_risk": None
        },
        "aggregated_risk": None,

        # External result references
        "agent_result_refs": {},

        # Critic evaluation
        "critic_verdict": None,

        # Final decision
        "final_decision": None
    }
}
