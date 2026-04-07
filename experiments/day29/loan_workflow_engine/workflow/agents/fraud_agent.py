
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Fraud Detection Agent
# ------------------------------------------------

def fraud_agent_node(state):

    app = state["data"]["application"]

    loan_amount = app["loan_amount"]
    income = app["income"]
    years_operating = app["years_operating"]

    loan_to_income = loan_amount / income

    # --- Simple fraud heuristics
    if loan_to_income > 1.5 or years_operating < 1:
        fraud_risk = "HIGH"

    elif loan_to_income > 0.8:
        fraud_risk = "MEDIUM"

    else:
        fraud_risk = "LOW"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "fraud_risk": fraud_risk
            }
        }
    )
