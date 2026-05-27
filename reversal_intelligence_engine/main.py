import sys
import io

# Ensure Unicode output (news headlines, special chars) prints cleanly on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from engine.scheduler import get_next_nodes
from engine.utils.state_updater import apply_node_result

from reversal_strategy.registry.node_registry import NODE_REGISTRY
from reversal_strategy.graph.graph_config import GRAPH
from engine.executor import execute_nodes_in_parallel
from engine.state.state_model import initialize_state
from reversal_strategy.agents.llm_client import token_tracker

def run_workflow():

    # Reset tracker for fresh run
    token_tracker.reset()

    state = initialize_state()

    while True:

        next_nodes = get_next_nodes(GRAPH, state["completed_nodes"])

        if not next_nodes:
            break

        print(f"\nRunning nodes: {next_nodes}")

        results = execute_nodes_in_parallel(next_nodes, NODE_REGISTRY, state)

        # Apply results sequentially (safe merge)
        for item in results:
            node_name = item["node"]
            if item["success"]:
                result = item["result"]
                apply_node_result(state, result)
            state["completed_nodes"].add(node_name)

    # Store token usage in state for watchlist persistence
    state["token_usage"] = token_tracker.get_summary()

    # Print cost summary to console
    token_tracker.print_summary()

    return state


if __name__ == "__main__":
    output = run_workflow()
