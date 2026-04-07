
from  core.engine.executor import execute_node
from concurrent.futures import ThreadPoolExecutor


def get_runnable_nodes(state,graph_config, dependency_map):

    # ------------------------------------------------
    # 🔥 STEP 1 — STRONG ROUTING OVERRIDE
    # ------------------------------------------------

    routing = state.get("routing")

    if routing:
        next_nodes = routing["next_nodes"]
        
        # --- Safety validation
        for node in next_nodes:
            if node not in graph_config:
                raise Exception(f"Invalid routing target: {node}")
            
        state["routing_comsumed"] = True

        return next_nodes   # 🚀 BYPASS DAG COMPLETELY

    # ------------------------------------------------
    # 🔽 STEP 2 — NORMAL DAG EXECUTION (FALLBACK)
    # ------------------------------------------------

    runnable = []

    for node in graph_config:

        if node in state["completed_nodes"]:
            continue

        dependencies = dependency_map.get(node, [])

        # node is runnable if all dependencies completed
        if all(dep in state["completed_nodes"] for dep in dependencies):
            runnable.append(node)

    return runnable


def run_workflow(state, graph_config, node_registry, dependency_map):

    while state["status"] == "RUNNING":

        # ------------------------------------------------
        # 🔥 CLEAR ROUTING AFTER IT WAS USED
        # ------------------------------------------------
        if state.get("routing_consumed"):
            state.pop("routing", None)
            state.pop("routing_consumed", None)

        if state["step_count"] >= state["max_steps"]:
            print("Max steps exceeded")
            break

        runnable_nodes = get_runnable_nodes(state, graph_config, dependency_map)

        if not runnable_nodes:
            break

        # --- handle START node
        if "START" in runnable_nodes:
            state["completed_nodes"].add("START")

        nodes_to_run = [n for n in runnable_nodes if n != "START"]

        if not nodes_to_run:
            continue

        # --- parallel execution
        with ThreadPoolExecutor(max_workers=len(nodes_to_run)) as executor:

            futures = [
                executor.submit(
                    execute_node,
                    state,
                    node,
                    node_registry,
                    graph_config
                )
                for node in nodes_to_run
            ]

            # wait for all nodes to finish
            for future in futures:
                future.result()

            if state.get("routing"):
                state.pop("routing")

    print("ROUTING:", state.get("routing"))            

    print(state["execution_log"])            

    print("Workflow finished")