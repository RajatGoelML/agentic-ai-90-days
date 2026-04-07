
from core.utils.logging_utils import apply_node_result
from core.utils.logging_utils import record_execution_event



def execute_node(state, node_name,node_registry, graph_config):

    # --- Fetch node object from registry
    node = node_registry[node_name]

    print(f"Executing node: {node_name}")

    # --- Update execution pointer
    state["current_node"] = node_name

    try:

        # --- Execute node logic
        result = node.node_function(state)

    except Exception as e:

        # --- Retry handling
        retry_count = state["retry_count"].get(node_name, 0)

        if retry_count < node.max_retry:

            state["retry_count"][node_name] = retry_count + 1

            print(f"Retrying node {node_name} ({retry_count+1}/{node.max_retry})")

            return [node_name]

        else:

            state["status"] = "FAILED"

            raise RuntimeError(f"Node {node_name} failed after retries") from e

    # --- Apply result to state
    apply_node_result(state, result,node_name)

    if result.next_nodes:
        next_nodes = result.next_nodes
    else:
        next_nodes = graph_config[node_name]["next"]
    # --- Record execution event
    record_execution_event(state, node_name,next_nodes, result)

    # --- Mark node as completed
    state["completed_nodes"].add(node_name)

    state["step_count"] += 1

    print(f"[EXECUTED] {node_name}")