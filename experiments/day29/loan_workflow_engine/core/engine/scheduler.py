
from  core.engine.executor import execute_node


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


def run_workflow(state,graph_config, node_registry, dependency_map):

    while state["status"] == "RUNNING":

        # safety guard
        if state["step_count"] >= state["max_steps"]:
            print("Max steps exceeded")
            break

        runnable_nodes = get_runnable_nodes(state, graph_config, dependency_map)

        if not runnable_nodes:
            break

        for node in runnable_nodes:

            if node == "START":
                state["completed_nodes"].add("START")
                continue

            execute_node(state, node,node_registry, graph_config)

    print("Workflow finished")