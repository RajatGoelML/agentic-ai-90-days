
from core.nodes.node_base import NodeResult
# ------------------------------------------------
# Policy Decision Node
# ------------------------------------------------

def policy_node(state):

    financial_score = state["data"]["financial_score"]
    aggregated_risk = state["data"]["aggregated_risk"]
    critic_verdict = state["data"]["critic_verdict"]

    if critic_verdict == "REVIEW_REQUIRED":
        decision = "REVIEW"

    elif aggregated_risk == "HIGH":
        decision = "REJECT"

    elif financial_score >= 80 and aggregated_risk == "LOW":
        decision = "APPROVE"

    else:
        decision = "REVIEW"

    return NodeResult(
        data_updates={
            "final_decision": decision
        }
    )
