
# ------------------------------------------------
# Graph Validation
# ------------------------------------------------

def validate_graph(graph_config, node_registry):

    # --- check START node
    if "START" not in graph_config:
        raise ValueError("Graph must contain START node")

    # --- check node handlers exist
    for node in graph_config:

        if node == "START":
            continue

        if node not in node_registry:
            raise ValueError(f"Node '{node}' missing in NODE_REGISTRY")

    # --- check transitions are valid
    for node, config in graph_config.items():

        for next_node in config["next"]:

            if next_node not in graph_config:
                raise ValueError(
                    f"Invalid transition: {node} → {next_node}"
                )

    # --- check terminal node exists
    terminal_nodes = [
        node for node, config in graph_config.items()
        if len(config["next"]) == 0
    ]

    if not terminal_nodes:
        raise ValueError("Graph must contain at least one terminal node")

    print("Graph validation successful")
