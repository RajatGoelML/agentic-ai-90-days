

def build_dependency_map(graph_config):

    dependency_map = {}

    for node, config in graph_config.items():

        for next_node in config["next"]:

            if next_node not in dependency_map:
                dependency_map[next_node] = []

            dependency_map[next_node].append(node)

    print(dependency_map)

    return dependency_map
