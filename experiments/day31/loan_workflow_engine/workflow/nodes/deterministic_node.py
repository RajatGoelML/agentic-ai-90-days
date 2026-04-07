
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Deterministic Scoring Node
# ------------------------------------------------

def deterministic_scoring_node(state):

    # --- Deterministic logic: read application data
    app = state["data"]["application"]

    income = app["income"]
    debt = app["debt"]
    emi = app["emi"]
    credit_score = app["credit_score"]

    # --- Derived financial ratios
    debt_to_income = debt / income
    emi_to_income = (emi * 12) / income

    # --- Basic scoring model
    score = 0

    if credit_score > 750:
        score += 40
    elif credit_score > 700:
        score += 30
    else:
        score += 10

    if debt_to_income < 0.2:
        score += 30
    elif debt_to_income < 0.4:
        score += 20
    else:
        score += 5

    if emi_to_income < 0.25:
        score += 30
    elif emi_to_income < 0.4:
        score += 20
    else:
        score += 5

    # --- Determine risk bucket
    if score >= 80:
        risk_bucket = "LOW"
    elif score >= 60:
        risk_bucket = "MEDIUM"
    else:
        risk_bucket = "HIGH"

    return NodeResult(

        data_updates={
            "financial_score": score,
            "risk_bucket": risk_bucket
        }
    )
