
from core.nodes.node_base import NodeResult
from core.llm.llm_client import asl_llm

# ------------------------------------------------
# Credit Risk Agent
# ------------------------------------------------

def credit_agent_node(state):

    app = state["data"]["application"]

    system_prompt = "You are a senior credit risk analyst."

    user_prompt = f"""

    Evaluate credit risk for this loan applicant.

    Income: {app["income"]}
    Debt: {app["debt"]}
    Credit Score: {app["credit_score"]}

    # Rules:
    # if financial_score >= 80 and credit_score >= 750 and debt_to_income < 0.3:
    #     risk = "LOW"

    # elif financial_score >= 60 and credit_score >= 700:
    #     risk = "MEDIUM"

    # else:
    #     risk = "HIGH"


    Respond ONLY with one of these values:
    LOW
    MEDIUM
    HIGH

    """
    llm_result = asl_llm(system_prompt,user_prompt)

    risk = llm_result["response"].upper()

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "credit_risk": risk
            }
            },
            trace={
                "user_prompt": user_prompt,
                "system_prompt": system_prompt,
                "response": llm_result["response"]
        }
    )