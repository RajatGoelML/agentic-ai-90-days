# ================================
# Dependency-Aware Workflow Scheduler
# ================================


def get_next_nodes(graph, completed_nodes):
    """
    Returns nodes whose dependencies have all been completed.

    Iterates the workflow graph and identifies any node whose
    upstream dependencies are fully present in completed_nodes.
    Called each iteration of the main workflow loop to determine
    which nodes are safe to execute next.
    """

    runnable_nodes = []

    for node_name, dependencies in graph.items():

        if node_name in completed_nodes:
            continue

        if all(dep in completed_nodes for dep in dependencies):
            runnable_nodes.append(node_name)

    return runnable_nodes