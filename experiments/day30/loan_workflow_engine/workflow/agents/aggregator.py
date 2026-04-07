
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

    overall_risk = risks["response"]

    # if "HIGH" in risks:
    #     overall_risk = "HIGH"

    # elif "MEDIUM" in risks:
    #     overall_risk = "MEDIUM"

    # else:
    #     overall_risk = "LOW"

    return NodeResult(

        data_updates={
            "aggregated_risk": overall_risk
        },
        trace={
            "user_prompt":user_prompt,
            "system_prompt":system_prompt,
            "response": risks["response"]
        }
    )