import time

# ------------------------------------------------
# Engine State Mutation Helper
# ------------------------------------------------

def apply_node_result(state, result, node_name):

    # --- Apply state updates
    for key, value in result.data_updates.items():
        state["data"][key] = value

    ROUTING_ALLOWED_NODES = ["AGGREGATOR"]    

    if result.next_nodes and node_name in ROUTING_ALLOWED_NODES:

        state["routing"] = {
            "next_nodes": result.next_nodes,
            "source": node_name,
            "step": state.get("step_count", 0),
            "timestamp": time.time()    
        }


# ------------------------------------------------
# Execution Event Recorder
# ------------------------------------------------

def record_execution_event(state, node_name,next_nodes, result):

    routing_applied = False

    if state.get("routing") and state["routing"]["source"] == node_name:
        routing_applied = True

    state["execution_log"].append({

        "node": node_name,

        "data_updates": result.data_updates,

        "next_nodes": next_nodes,

        "routing_applied": routing_applied,   

        "step": state["step_count"],
        
        "trace": result.trace,
        
        "timestamp": time.time()
    })