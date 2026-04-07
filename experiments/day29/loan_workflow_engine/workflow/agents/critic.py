
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Critic Node
# ------------------------------------------------

def critic_node(state):

    agent_summary = state["data"]["agent_summary"]

    credit = agent_summary["credit_risk"]
    fraud = agent_summary["fraud_risk"]
    sector = agent_summary["sector_risk"]

    # --- basic consistency checks
    if fraud == "HIGH":
        verdict = "REVIEW_REQUIRED"

    elif credit == "LOW" and sector == "HIGH":
        verdict = "REVIEW_REQUIRED"

    else:
        verdict = "CONSISTENT"

    return NodeResult(
        data_updates={
            "critic_verdict": verdict
        }
    )