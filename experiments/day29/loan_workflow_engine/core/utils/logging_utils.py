

# ------------------------------------------------
# Engine State Mutation Helper
# ------------------------------------------------

def apply_node_result(state, result):

    # --- Apply state updates
    for key, value in result.data_updates.items():
        state["data"][key] = value


# ------------------------------------------------
# Execution Event Recorder
# ------------------------------------------------

def record_execution_event(state, node_name,next_nodes, result):

    state["execution_log"].append({

        "node": node_name,

        "data_updates": result.data_updates,

        "next_nodes": next_nodes,

        "step": state["step_count"]
    })