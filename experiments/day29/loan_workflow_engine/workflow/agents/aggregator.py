
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Agent Aggregator
# ------------------------------------------------

def aggregator_node(state):

    agent_summary = state["data"]["agent_summary"]

    risks = list(agent_summary.values())

    if "HIGH" in risks:
        overall_risk = "HIGH"

    elif "MEDIUM" in risks:
        overall_risk = "MEDIUM"

    else:
        overall_risk = "LOW"

    return NodeResult(

        data_updates={
            "aggregated_risk": overall_risk
        }
    )