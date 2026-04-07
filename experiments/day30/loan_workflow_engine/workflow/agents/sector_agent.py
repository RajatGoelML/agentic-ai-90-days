
from core.nodes.node_base import NodeResult
from core.llm.llm_client import asl_llm


# ------------------------------------------------
# Sector Risk Agent
# ------------------------------------------------

def sector_agent_node(state):

    sector = state["data"]["application"]["sector"]

    system_prompt = "You are a macroeconomic sector analyst."

    user_prompt = f"""
        Evaluate financial risk of the following business sector:

        Sector: {sector}

        Respond ONLY with:
        LOW
        MEDIUM
        HIGH
        """
    
    llm_result = asl_llm(system_prompt, user_prompt)

    sector_risk = llm_result["response"].upper()

    # if sector in high_risk_sectors:
    #     sector_risk = "HIGH"

    # elif sector in medium_risk_sectors:
    #     sector_risk = "MEDIUM"

    # else:
    #     sector_risk = "LOW"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "sector_risk": sector_risk
            }
        },
            trace={
                "user_prompt": user_prompt,
                "system_prompt": system_prompt,
                "response": llm_result["response"]
            }
    )