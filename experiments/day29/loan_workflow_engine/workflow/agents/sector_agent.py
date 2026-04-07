
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Sector Risk Agent
# ------------------------------------------------

def sector_agent_node(state):

    sector = state["data"]["application"]["sector"]

    high_risk_sectors = ["Crypto", "Gambling"]
    medium_risk_sectors = ["Manufacturing", "Construction"]

    if sector in high_risk_sectors:
        sector_risk = "HIGH"

    elif sector in medium_risk_sectors:
        sector_risk = "MEDIUM"

    else:
        sector_risk = "LOW"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "sector_risk": sector_risk
            }
        }
    )