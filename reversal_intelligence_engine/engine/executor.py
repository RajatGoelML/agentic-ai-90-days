# ================================
# Parallel Workflow Executor
# ================================

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)


def execute_nodes_in_parallel(node_names, registry, state):

    """
    Executes a list of nodes concurrently using a thread pool.

    Each node is looked up in the registry and submitted as an
    independent task. Results and errors are collected and returned
    as a list — failures are captured per node without blocking others.
    """

    results = []

    with ThreadPoolExecutor(max_workers=4) as executor:

        futures = {
            executor.submit(registry[node_name].execute, state): node_name
            for node_name in node_names
        }

        for future in as_completed(futures):

            node_name = futures[future]

            try:
                result = future.result()
                results.append({
                    "node":    node_name,
                    "success": True,
                    "result":  result,
                })

            except Exception as e:
                print(f"\n[Executor] Node {node_name} failed: {e}")
                results.append({
                    "node":    node_name,
                    "success": False,
                    "error":   str(e),
                })

    return results