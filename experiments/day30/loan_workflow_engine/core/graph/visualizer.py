

from graphviz import Digraph


def visualize_graph(graph_config):

    dot = Digraph(comment="Workflow DAG")

    # create nodes
    for node in graph_config:
        dot.node(node)

    # create edges
    for node, config in graph_config.items():

        for next_node in config["next"]:
            dot.edge(node, next_node)

    return dot