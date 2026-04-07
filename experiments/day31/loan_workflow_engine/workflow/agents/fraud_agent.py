
from core.nodes.node_base import NodeResult
from core.llm.llm_client import asl_llm


# ------------------------------------------------
# Fraud Detection Agent
# ------------------------------------------------

def fraud_agent_node(state):

    app = state["data"]["application"]

    system_prompt = "You are a financial fraud detection expert."

    user_prompt = f"""
        Evaluate fraud risk.

        Loan amount: {app["loan_amount"]}
        Income: {app["income"]}
        Years operating: {app["years_operating"]}

        Respond ONLY with:
        LOW
        MEDIUM
        HIGH
        """

    llm_result = asl_llm(system_prompt, user_prompt)

    fraud_risk = llm_result["response"].upper()

    # --- Simple fraud heuristics
    # if loan_to_income > 1.5 or years_operating < 1:
    #     fraud_risk = "HIGH"

    # elif loan_to_income > 0.8:
    #     fraud_risk = "MEDIUM"

    # else:
    #     fraud_risk = "LOW"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "fraud_risk": fraud_risk
            }
            
        },
        trace={
                "response": llm_result["response"],
                "user_prompt":user_prompt,
                "system_prompt":system_prompt
            }
    )
