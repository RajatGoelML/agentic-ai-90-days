
from core.nodes.node_base import NodeResult
from core.llm.llm_client import asl_llm

# ------------------------------------------------
# Agent Aggregator
# ------------------------------------------------

def aggregator_node(state):

    agent_summary = state["data"]["agent_summary"]
    app = state["data"]["application"]

    system_prompt = "You are a senior loan risk committee analyst."

    user_prompt = f"""
        The following risk assessments were produced by independent AI agents.

        Credit Risk: {agent_summary["credit_risk"]}
        Fraud Risk: {agent_summary["fraud_risk"]}
        Sector Risk: {agent_summary["sector_risk"]}

        Loan Information:
        Loan Amount: {app["loan_amount"]}
        Income: {app["income"]}
        Credit Score: {app["credit_score"]}

        Evaluate the overall loan risk.

        Respond ONLY with:
        LOW
        MEDIUM
        HIGH
        """

    risks = asl_llm(system_prompt,user_prompt)

    response  = risks["response"].upper()

    if "HIGH" in response:
        overall_risk = "HIGH"
        next_nodes = ["final_decision"]

    elif "MEDIUM" in response:
        overall_risk = "MEDIUM"
        next_nodes = ["critic"]

    elif "LOW" in response:
        overall_risk = "LOW"
        next_nodes = ["policy"]

    else:
        # ------------------------------------------------
        # 🔥 SAFETY FALLBACK (very important)
        # ------------------------------------------------
        overall_risk = "MEDIUM"
        next_nodes = ["critic"]    

    return NodeResult(

        data_updates={
            "aggregated_risk": overall_risk
        },
        next_nodes=next_nodes,
        trace={
            "user_prompt":user_prompt,
            "system_prompt":system_prompt,
            "response": risks["response"],
            "parsed_risk": overall_risk
        }   
    )