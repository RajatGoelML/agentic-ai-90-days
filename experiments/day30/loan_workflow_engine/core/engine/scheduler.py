
from  core.engine.executor import execute_node
from concurrent.futures import ThreadPoolExecutor


def get_runnable_nodes(state,graph_config, dependency_map):

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

    print(state["trace"])            

    print("Workflow finished")