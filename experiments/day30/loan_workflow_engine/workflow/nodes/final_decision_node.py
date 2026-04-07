
from core.nodes.node_base import NodeResult

# ------------------------------------------------
# Final Decision Node
# ------------------------------------------------

def final_decision_node(state):

    application_id = state["data"]["application"]["loan_id"]
    decision = state["data"]["final_decision"]

    print(f"Loan Application {application_id} → {decision}")

    # mark workflow finished
    state["status"] = "COMPLETED"

    return NodeResult(
        data_updates={}
    )
