
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Credit Risk Agent
# ------------------------------------------------

def credit_agent_node(state):

    app = state["data"]["application"]

    financial_score = state["data"]["financial_score"]

    credit_score = app["credit_score"]
    debt = app["debt"]
    income = app["income"]

    debt_to_income = debt / income

    # --- Simple risk reasoning
    if financial_score >= 80 and credit_score >= 750 and debt_to_income < 0.3:
        risk = "LOW"

    elif financial_score >= 60 and credit_score >= 700:
        risk = "MEDIUM"

    else:
        risk = "HIGH"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "credit_risk": risk
            }
        }
    )